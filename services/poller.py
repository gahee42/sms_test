"""SMS 폴링 서비스 — 모뎀에서 안읽은 SMS를 주기적으로 처리"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))
LOG_PATH = Path(__file__).parent.parent / 'sms_log.jsonl'


def save_and_reply(imei: str, msisdn: str, messages: list) -> dict:
    """SMS 저장 + echo 답장 생성"""
    entry = {
        'imei': imei,
        'msisdn': msisdn,
        'messages': messages,
        'received_at': datetime.now().isoformat(),
    }
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    replies = []
    for msg in messages:
        replies.append({
            'phone': msg.get('phone'),
            'message': f'[echo] {msg.get("content", "")}',
        })

    return {'ok': True, 'replies': replies}


async def poll_loop(modem):
    """폴링 루프 — 서버 startup 시 백그라운드로 실행됨"""
    print(f'[폴러] {POLL_INTERVAL}초 간격 폴링 시작')

    while True:
        try:
            messages = await modem.get_unread_sms()

            if messages:
                print(f'[폴러] 안읽은 SMS {len(messages)}건 발견')

                # 저장 + 답장 생성
                result = save_and_reply(modem.imei, modem.msisdn, messages)

                if result.get('ok'):
                    # 읽음 처리
                    for msg in messages:
                        await modem.set_read(msg['index'])

                    # 답장 발송
                    for reply in result.get('replies', []):
                        try:
                            await modem.send_sms(reply['phone'], reply['message'])
                            print(f'[폴러] 답장 발송 → {reply["phone"]}')
                        except Exception as e:
                            print(f'[폴러] 답장 실패: {e}')

        except Exception as e:
            print(f'[폴러] 에러: {e}')

        await asyncio.sleep(POLL_INTERVAL)
