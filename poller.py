"""SMS 폴링 스크립트 - 모뎀에서 안읽은 SMS를 가져와 서버로 전송"""
import os
import time
import requests
from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.sms import BoxTypeEnum

MODEM_URL = os.getenv('MODEM_URL', '')
MODEM_USER = os.getenv('MODEM_USER', '')
MODEM_PASS = os.getenv('MODEM_PASS', '')
API_URL = os.getenv('API_URL', 'http://localhost:3000/v1/sms')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))


def poll():
    with Connection(MODEM_URL, username=MODEM_USER, password=MODEM_PASS) as conn:
        client = Client(conn)

        # 기기 정보 획득
        info = client.device.information()
        imei = info.get('Imei', '')
        msisdn = info.get('Msisdn', '')
        print(f'[시작] 모뎀 연결됨 (IMEI: {imei}). {POLL_INTERVAL}초 간격 폴링')

        while True:
            try:
                sms_list = client.sms.get_sms_list(
                    1, box_type=BoxTypeEnum.LOCAL_INBOX, read_count=50, unread_preferred=True
                )
                raw_messages = sms_list.get('Messages', {}).get('Message', [])
                if isinstance(raw_messages, dict):
                    raw_messages = [raw_messages]

                # 안읽은 SMS만 수집
                messages = []
                for sms in raw_messages:
                    if sms.get('Smstat') == '0':
                        messages.append({
                            'index': int(sms['Index']),
                            'phone': sms.get('Phone', ''),
                            'content': sms.get('Content', ''),
                            'date': sms.get('Date', ''),
                            'smsType': int(sms.get('SmsType', 1)),
                        })

                if not messages:
                    time.sleep(POLL_INTERVAL)
                    continue

                # 서버로 전송
                try:
                    res = requests.post(API_URL, json={
                        'imei': imei,
                        'msisdn': msisdn,
                        'messages': messages,
                    })
                    resp = res.json()

                    if res.status_code in (200, 201) and resp.get('ok'):
                        # 읽음 처리
                        for msg in messages:
                            client.sms.set_read(msg['index'])
                        print(f'[저장완료] {len(messages)}건')

                        # 답장 발송
                        for reply in resp.get('replies', []):
                            try:
                                client.sms.send_sms([reply['phone']], reply['message'])
                                print(f'[답장발송] → {reply["phone"]}')
                            except Exception as e:
                                print(f'[답장실패] {e}')
                    else:
                        print(f'[전송실패] {res.status_code}')
                except requests.RequestException as e:
                    print(f'[서버에러] {e}')
            except Exception as e:
                print(f'[모뎀에러] {e}')

            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    poll()
