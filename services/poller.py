"""SMS 폴링 서비스 — 오케스트레이션만 담당

각 단계는 개별 서비스가 처리:
  1. modem.get_unread_sms()            → 수신
  2. POST /v1/sms (서버 API)           → 수신 저장 + 답장/스팸 응답
  3. modem.send_sms()                  → 답장 발송
  4. POST /v1/sms (서버 API)           → 발신 저장 (direction: seller)
  5. modem.set_read()                  → 읽음 처리
"""
import asyncio
import os
import time
from datetime import datetime

import aiohttp

from services.modem import MODEM_TIMEOUT, RECONNECT_INTERVAL, SMS_CLEANUP_THRESHOLD
from services import slack
from services.spam_filter import is_spam

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))
API_URL = os.getenv('API_URL', 'http://localhost:3000/v1/sms')


async def poll_loop(modem):
    """폴링 루프 — 서버 startup 시 백그라운드로 실행됨"""
    tag = modem.label
    print(f'[{tag}] {POLL_INTERVAL}초 간격 폴링 시작')
    asyncio.create_task(slack.polling_started(tag, POLL_INTERVAL))

    timeout = aiohttp.ClientTimeout(total=MODEM_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                # 모뎀 미연결 → 재연결 시도
                if not modem.connected:
                    if not await modem.reconnect():
                        asyncio.create_task(slack.modem_reconnect_failed(tag, '재연결 실패'))
                        await asyncio.sleep(RECONNECT_INTERVAL)
                        continue
                    asyncio.create_task(slack.modem_connected(tag, modem.msisdn))

                # 1. 수신
                messages = await modem.get_unread_sms()

                if not messages:
                    asyncio.create_task(slack.poll_ok(tag, modem.msisdn))

                if messages:
                    # 이미 읽은 MMS → 서버 전송 없이 바로 삭제
                    read_mms = [m for m in messages if m.get('_read_mms')]
                    for m in read_mms:
                        await modem.delete_sms(m['index'])
                        print(f'[{tag}] 읽은 MMS 삭제 [{m["index"]}]')
                    messages = [m for m in messages if not m.get('_read_mms')]

                if messages:
                    # MMS 중복 분리 (읽음 처리용 index만 보관)
                    duplicates = [m for m in messages if m.get('_duplicate')]
                    unique = [m for m in messages if not m.get('_duplicate')]

                    print(f'[{tag}] 안읽은 SMS {len(unique)}건 발견'
                          + (f' (MMS 중복 {len(duplicates)}건 제외)' if duplicates else ''))
                    asyncio.create_task(slack.sms_received(unique))

                    # 2. 수신 메시지 서버 전송
                    server_messages = [
                        {
                            'phone': m['phone'],
                            'content': m['content'],
                            'date': m['date'],
                            'mms': m['mms'],
                            'direction': 'customer',
                        }
                        for m in unique
                    ]

                    try:
                        start = time.time()
                        async with session.post(API_URL, json={
                            'msisdn': modem.msisdn,
                            'messages': server_messages,
                        }) as resp:
                            result = await resp.json()
                        elapsed = round(time.time() - start, 2)
                        print(f'[{tag}] 서버 응답 ({resp.status}) {elapsed}초')
                    except Exception as e:
                        print(f'[{tag}] 서버 API 에러: {e}')
                        asyncio.create_task(slack.server_error(tag, str(e)))
                        result = None

                    if result and result.get('ok'):
                        # 3. 답장 발송 — 스팸 필터링 (추후 서버 전환)
                        spam_phones = set(result.get('spam', []))
                        spam_phones |= {m['phone'] for m in unique if is_spam(m)}
                        sent = []
                        for r in result.get('replies', []):
                            if r['phone'] in spam_phones:
                                print(f'[{tag}] 스팸 답장 스킵 → {r["phone"]}')
                                asyncio.create_task(slack.sms_spam_skipped(r['phone']))
                                continue
                            try:
                                await modem.send_sms(r['phone'], r['message'])
                                print(f'[{tag}] 답장 발송 → {r["phone"]}')
                                asyncio.create_task(slack.sms_replied(r['phone'], r['message']))
                                sent.append({
                                    'phone': r['phone'],
                                    'content': r['message'],
                                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'mms': False,
                                    'direction': 'seller',
                                })
                                await asyncio.sleep(2)
                            except Exception as e:
                                print(f'[{tag}] 답장 실패: {e}')
                                asyncio.create_task(slack.sms_reply_failed(r['phone'], str(e)))

                        # 4. 발신 메시지 서버 전송
                        if sent:
                            try:
                                async with session.post(API_URL, json={
                                    'msisdn': modem.msisdn,
                                    'messages': sent,
                                }) as resp2:
                                    await resp2.json()
                            except Exception as e:
                                print(f'[{tag}] 발송 보고 실패: {e}')
                                asyncio.create_task(slack.server_error(tag, f'발송 보고: {e}'))

                    elif result:
                        print(f'[{tag}] 서버 응답 실패: {result}')
                        asyncio.create_task(slack.server_response_failed(tag, result))

                    # 5. 읽음 처리 + MMS 삭제
                    for msg in messages:
                        await modem.set_read(msg['index'])
                        if msg.get('mms') or msg.get('_duplicate'):
                            await modem.delete_sms(msg['index'])
                            print(f'[{tag}] MMS 삭제 [{msg["index"]}]')

                # 6. SMS 용량 체크 → 임계치 이하로 떨어질 때까지 반복 정리
                try:
                    total = await modem.get_sms_count()
                    if total >= SMS_CLEANUP_THRESHOLD:
                        print(f'[{tag}] SMS {total}건 → 정리 시작 (임계값: {SMS_CLEANUP_THRESHOLD})')
                        total_deleted = 0
                        while total >= SMS_CLEANUP_THRESHOLD:
                            deleted = await modem.cleanup_read_sms()
                            total_deleted += deleted
                            if deleted == 0:
                                break
                            total = await modem.get_sms_count()
                        asyncio.create_task(slack.cleanup_done(tag, total_deleted, total))
                except Exception as e:
                    print(f'[{tag}] SMS 정리 에러: {e}')

            except Exception as e:
                print(f'[{tag}] 에러: {e}')
                asyncio.create_task(slack.error(tag, e))
                asyncio.create_task(slack.modem_disconnected(tag, str(e)))
                # 모뎀 에러 → 재연결 시도
                if not await modem.reconnect():
                    asyncio.create_task(slack.modem_reconnect_failed(tag, str(e)))
                    await asyncio.sleep(RECONNECT_INTERVAL)
                    continue
                asyncio.create_task(slack.modem_connected(tag, modem.msisdn))

            await asyncio.sleep(POLL_INTERVAL)
