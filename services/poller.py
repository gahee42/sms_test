"""SMS 폴링 서비스 — 오케스트레이션만 담당

각 단계는 개별 서비스가 처리:
  1. modem.get_unread_sms()            → 수신
  2. POST /v1/sms (서버 API)           → 저장 + 답장 생성
  3. modem.send_sms()                  → 답장 발송
  4. modem.set_read()                  → 읽음 처리
"""
import asyncio
import os
import time

import aiohttp

from services.modem import RECONNECT_INTERVAL

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))
API_URL = os.getenv('API_URL', 'http://localhost:3000/v1/sms')


async def poll_loop(modem):
    """폴링 루프 — 서버 startup 시 백그라운드로 실행됨"""
    print(f'[폴러] {POLL_INTERVAL}초 간격 폴링 시작')

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # 1. 수신
                messages = await modem.get_unread_sms()

                if messages:
                    print(f'[폴러] 안읽은 SMS {len(messages)}건 발견')

                    # 2. 서버 API로 전송 → 답장 받기
                    start = time.time()
                    async with session.post(API_URL, json={
                        'imei': modem.imei,
                        'msisdn': modem.msisdn,
                        'messages': messages,
                    }) as resp:
                        result = await resp.json()
                    elapsed = round(time.time() - start, 2)
                    print(f'[폴러] 서버 응답 ({resp.status}) {elapsed}초')

                    if result.get('ok'):
                        # 3. 답장 발송 (모뎀 처리 간격 2초)
                        for r in result.get('replies', []):
                            try:
                                await modem.send_sms(r['phone'], r['message'])
                                print(f'[폴러] 답장 발송 → {r["phone"]}')
                                await asyncio.sleep(2)
                            except Exception as e:
                                print(f'[폴러] 답장 실패: {e}')

                        # 4. 읽음 처리
                        for msg in messages:
                            await modem.set_read(msg['index'])
                    else:
                        print(f'[폴러] 서버 응답 실패: {result}')

            except Exception as e:
                print(f'[폴러] 에러: {e}')
                # 모뎀 에러 → 재연결 시도
                if not await modem.reconnect():
                    await asyncio.sleep(RECONNECT_INTERVAL)
                    continue

            await asyncio.sleep(POLL_INTERVAL)
