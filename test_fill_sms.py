"""SMS 저장 한도 테스트 — 자기 자신에게 대량 발송

사용법:
  python test_fill_sms.py          # 235건 발송
  python test_fill_sms.py 10       # 10건만 발송
"""
import os
import sys
import time

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection

MODEM_URL = os.getenv('MODEM_URL', '')
MODEM_USER = os.getenv('MODEM_USER', '')
MODEM_PASS = os.getenv('MODEM_PASS', '')

SELF_PHONE = os.getenv('MODEM_PHONE', '')
TOTAL = int(sys.argv[1]) if len(sys.argv) > 1 else 235
INTERVAL = 1  # 초


def main():
    conn = Connection(MODEM_URL, username=MODEM_USER, password=MODEM_PASS)
    client = Client(conn)

    with conn:
        # 현재 상태 확인
        count = client.sms.sms_count()
        inbox = int(count.get('LocalInbox', 0))
        outbox = int(count.get('LocalOutbox', 0))
        local_max = int(count.get('LocalMax', 500))
        current = inbox + outbox
        print(f'현재: {current}/{local_max} (수신:{inbox} 발신:{outbox})')
        print(f'발송 예정: {TOTAL}건 → 자기자신({SELF_PHONE})')
        print(f'예상 결과: {current} + {TOTAL}*2 = {current + TOTAL * 2}건')
        print()

        for i in range(1, TOTAL + 1):
            try:
                client.sms.send_sms([SELF_PHONE], f'fill test {i}/{TOTAL}')
                print(f'[{i}/{TOTAL}] OK')
            except Exception as e:
                print(f'[{i}/{TOTAL}] ERROR: {e}')
                # 에러 발생 시 현재 상태 확인
                try:
                    count = client.sms.sms_count()
                    inbox = int(count.get('LocalInbox', 0))
                    outbox = int(count.get('LocalOutbox', 0))
                    print(f'  현재: {inbox + outbox}/{local_max} (수신:{inbox} 발신:{outbox})')
                except Exception:
                    pass
                break

            if i < TOTAL:
                time.sleep(INTERVAL)

        # 최종 상태
        print()
        count = client.sms.sms_count()
        inbox = int(count.get('LocalInbox', 0))
        outbox = int(count.get('LocalOutbox', 0))
        print(f'최종: {inbox + outbox}/{local_max} (수신:{inbox} 발신:{outbox})')


if __name__ == '__main__':
    main()
