"""SMS 폴링 스크립트 - 모뎀에서 안읽은 SMS를 가져와 서버로 전송"""
import time
import requests
from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection

MODEM_URL = 'http://192.168.8.1/'
API_URL = 'http://localhost:3000/v1/sms'
POLL_INTERVAL = 5


def poll():
    with Connection(MODEM_URL) as conn:
        client = Client(conn)
        print(f'[시작] 모뎀 연결됨. {POLL_INTERVAL}초 간격 폴링')

        while True:
            try:
                sms_list = client.sms.get_sms_list(
                    1, BoxType=1, ReadCount=50, UnreadPreferred=1
                )
                messages = sms_list.get('Messages', {}).get('Message', [])
                if isinstance(messages, dict):
                    messages = [messages]

                for sms in messages:
                    if sms.get('Smstat') == '0':
                        try:
                            res = requests.post(API_URL, json={'raw': sms})
                            if res.status_code == 200:
                                client.sms.set_read(int(sms['Index']))
                                print(f'[저장완료] Index:{sms["Index"]} From:{sms["Phone"]}')
                            else:
                                print(f'[전송실패] {res.status_code}')
                        except requests.RequestException as e:
                            print(f'[서버에러] {e}')
            except Exception as e:
                print(f'[모뎀에러] {e}')

            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    poll()
