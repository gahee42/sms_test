"""모뎀 API 원본 XML 응답을 그대로 출력하는 디버그 스크립트

사용법:
  python raw_dump.py                # 전체 API 덤프
  python raw_dump.py sms-list       # SMS 목록만
  python raw_dump.py sms-count      # SMS 개수만
  python raw_dump.py device         # 기기 정보만
  python raw_dump.py signal         # 신호 세기만
  python raw_dump.py status         # 모니터링 상태만
  python raw_dump.py traffic        # 트래픽 통계만
  python raw_dump.py plmn           # 통신사 정보만
  python raw_dump.py net-mode       # 네트워크 모드만
  python raw_dump.py sms-config     # SMS 설정만
  python raw_dump.py check          # 기기정보 + SMS개수 + 신호세기 (modem.py check와 동일 범위)
  python raw_dump.py sms-send       # SMS 발송 (⚠️ 실제 발송됨!)
  python raw_dump.py sms-delete     # SMS 삭제 (⚠️ 실제 삭제됨!)
"""
import os
import sys
import xml.etree.ElementTree as ET

from huawei_lte_api.Connection import Connection

MODEM_URL = os.getenv('MODEM_URL', '')
MODEM_USER = os.getenv('MODEM_USER', '')
MODEM_PASS = os.getenv('MODEM_PASS', '')
MODEM_PHONE = os.getenv('MODEM_PHONE', '')

# POST 요청이 필요한 엔드포인트와 body
POST_ENDPOINTS = {
    'sms-list': (
        'api/sms/sms-list',
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<request>'
        '<PageIndex>1</PageIndex>'
        '<ReadCount>5</ReadCount>'
        '<BoxType>1</BoxType>'
        '<SortType>0</SortType>'
        '<Ascending>0</Ascending>'
        '<UnreadPreferred>1</UnreadPreferred>'
        '</request>'
    ),
    'sms-delete': (
        'api/sms/delete-sms',
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<request>'
        '<Index>40023</Index>'
        '</request>'
    ),
}


def get_sms_send_body(phone: str = '', content: str = 'raw_dump test') -> tuple:
    """sms-send body를 동적으로 생성 (전화번호가 env에서 옴)"""
    p = phone or MODEM_PHONE
    return (
        'api/sms/send-sms',
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<request>'
        f'<Index>-1</Index>'
        f'<Phones><Phone>{p}</Phone></Phones>'
        f'<Sca></Sca>'
        f'<Content>{content}</Content>'
        f'<Length>-1</Length>'
        f'<Reserved>1</Reserved>'
        f'<Date>-1</Date>'
        f'</request>'
    )

# 전체 덤프에서 제외할 커맨드 (실행 시 실제 발송/삭제됨)
DANGEROUS_KEYS = {'sms-send', 'sms-delete'}

# GET 요청 엔드포인트
GET_ENDPOINTS = {
    'device':    'api/device/information',
    'signal':    'api/device/signal',
    'basic':     'api/device/basic_information',
    'sms-count': 'api/sms/sms-count',
    'sms-config': 'api/sms/config',
    'status':    'api/monitoring/status',
    'traffic':   'api/monitoring/traffic-statistics',
    'plmn':      'api/net/current-plmn',
    'net-mode':  'api/net/net-mode',
}

ALL_KEYS = [k for k in list(GET_ENDPOINTS.keys()) + list(POST_ENDPOINTS.keys()) if k not in DANGEROUS_KEYS]


def get_token(session) -> str:
    """매 POST 요청마다 새 CSRF 토큰 발급"""
    resp = session.get(f'{MODEM_URL}api/webserver/SesTokInfo')
    root = ET.fromstring(resp.text)
    return root.findtext('TokInfo', '')


def raw_request(conn: Connection, method: str, endpoint: str, body: str = None) -> str:
    """로그인된 Connection의 내부 세션으로 raw 요청"""
    session = conn.requests_session
    url = f'{MODEM_URL}{endpoint}'

    if method == 'POST':
        token = get_token(session)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            '__RequestVerificationToken': token,
        }
        resp = session.post(url, data=body, headers=headers)
    else:
        resp = session.get(url)

    resp.encoding = 'utf-8'
    return resp.text


def dump(conn: Connection, targets: list[str]):
    for name in targets:
        print(f'\n{"=" * 60}')
        print(f'  {name}')
        print(f'{"=" * 60}')

        try:
            if name == 'sms-send':
                endpoint, body = get_sms_send_body()
                result = raw_request(conn, 'POST', endpoint, body)
            elif name in POST_ENDPOINTS:
                endpoint, body = POST_ENDPOINTS[name]
                result = raw_request(conn, 'POST', endpoint, body)
            elif name in GET_ENDPOINTS:
                result = raw_request(conn, 'GET', GET_ENDPOINTS[name])
            else:
                print(f'  알 수 없는 명령: {name}')
                continue

            print(result)
        except Exception as e:
            print(f'  ❌ {e}')


def main():
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = ALL_KEYS

    conn = Connection(MODEM_URL, username=MODEM_USER, password=MODEM_PASS)
    dump(conn, targets)
    try:
        conn.close()
    except Exception:
        pass  # raw 요청으로 토큰 소진 시 로그아웃 실패 무시


if __name__ == '__main__':
    main()
