"""SMS 폴링 서비스 — 오케스트레이션만 담당

각 단계는 개별 서비스가 처리:
  1. modem.get_unread_sms()   → 수신
  2. storage.save()           → 저장
  3. reply.generate()         → 답장 생성
  4. modem.send_sms()         → 답장 발송
  5. modem.set_read()         → 읽음 처리
"""
import asyncio
import os

from services import storage, reply

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))


async def poll_loop(modem):
    """폴링 루프 — 서버 startup 시 백그라운드로 실행됨"""
    print(f'[폴러] {POLL_INTERVAL}초 간격 폴링 시작')

    while True:
        try:
            # 1. 수신
            messages = await modem.get_unread_sms()

            if messages:
                print(f'[폴러] 안읽은 SMS {len(messages)}건 발견')

                # 2. 저장
                storage.save(modem.imei, modem.msisdn, messages)

                # 3. 답장 생성
                replies = reply.generate(messages)

                # 4. 답장 발송 (모뎀 처리 간격 2초)
                for r in replies:
                    try:
                        await modem.send_sms(r['phone'], r['message'])
                        print(f'[폴러] 답장 발송 → {r["phone"]}')
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f'[폴러] 답장 실패: {e}')

                # 5. 읽음 처리
                for msg in messages:
                    await modem.set_read(msg['index'])

        except Exception as e:
            print(f'[폴러] 에러: {e}')

        await asyncio.sleep(POLL_INTERVAL)
