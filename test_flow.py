"""SMS 전체 흐름 테스트 스크립트

흐름:
  1. 모뎀에서 안읽은 SMS 폴링
  2. 서버에 전송 (mock)
  3. 서버 응답: ok + reply message
  4. 수신 번호에게 답장 발송 → 성공 시 원본 읽음 처리
  5. 답장 성공 확인
  6. 원본(읽은거) + 답장(발신함) 삭제

사용법:
  python test_flow.py
"""
import json
import os
import re
import time

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.sms import BoxTypeEnum

MODEM_URL = os.getenv('MODEM_URL', '')
MODEM_USER = os.getenv('MODEM_USER', '')
MODEM_PASS = os.getenv('MODEM_PASS', '')

# MMS 감지 패턴
MMS_PATTERN = '¾¯'


# ──────────────────────────────────────────────
# Mock 서버 (실제 서버 구현 전 테스트용)
# ──────────────────────────────────────────────
def mock_server_request(imei: str, msisdn: str, messages: list) -> dict:
    """서버 POST /v1/sms 를 흉내냄"""
    print(f'\n📡 [서버 전송] imei={imei}, msisdn={msisdn}')
    print(f'   메시지 {len(messages)}건:')
    for msg in messages:
        print(f'   - [{msg["index"]}] {msg["phone"]}: {msg["content"]}')

    # mock 응답: 모든 메시지에 답장
    replies = []
    for msg in messages:
        replies.append({
            'phone': msg['phone'],
            'message': '답장 보낼거',
        })

    response = {'ok': True, 'replies': replies}
    print(f'   ← 서버 응답: {json.dumps(response, ensure_ascii=False)}')
    return response


# ──────────────────────────────────────────────
# 1. SMS 폴링 (MMS fallback 포함)
# ──────────────────────────────────────────────
def poll_sms(client: Client, conn: Connection) -> list:
    """안읽은 SMS 목록 조회. MMS로 파싱 실패 시 raw fallback."""
    print('\n📥 [1] SMS 폴링...')

    try:
        # 라이브러리로 시도
        sms_list = client.sms.get_sms_list(
            1, box_type=BoxTypeEnum.LOCAL_INBOX,
            read_count=50, unread_preferred=True
        )
        messages_raw = sms_list.get('Messages', {}).get('Message', [])
        if isinstance(messages_raw, dict):
            messages_raw = [messages_raw]

        messages = []
        for sms in messages_raw:
            if sms.get('Smstat') != '0':
                continue

            content = sms.get('Content') or ''
            if MMS_PATTERN in content:
                print(f'   ⚠️ MMS 감지 [{sms.get("Index")}] → 삭제 예정')
                client.sms.delete_sms(int(sms.get('Index')))
                print(f'   🗑️ MMS 삭제 완료 [{sms.get("Index")}]')
                continue

            messages.append({
                'index': int(sms.get('Index')),
                'phone': sms.get('Phone'),
                'content': content,
                'date': sms.get('Date'),
                'smsType': int(sms.get('SmsType', 1)),
            })

        print(f'   안읽은 SMS: {len(messages)}건')
        return messages

    except Exception as e:
        print(f'   ❌ 라이브러리 파싱 실패: {e}')
        print(f'   🔄 raw fallback 시도...')
        return poll_sms_raw_fallback(conn)


def poll_sms_raw_fallback(conn: Connection) -> list:
    """라이브러리 실패 시 raw HTTP + 정규식으로 SMS 추출"""
    import xml.etree.ElementTree as ET

    session = conn.requests_session

    # CSRF 토큰 발급
    tok_resp = session.get(f'{MODEM_URL}api/webserver/SesTokInfo')
    root = ET.fromstring(tok_resp.text)
    token = root.findtext('TokInfo', '')

    # raw sms-list 요청
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<request>'
        '<PageIndex>1</PageIndex>'
        '<ReadCount>50</ReadCount>'
        '<BoxType>1</BoxType>'
        '<SortType>0</SortType>'
        '<Ascending>0</Ascending>'
        '<UnreadPreferred>1</UnreadPreferred>'
        '</request>'
    )
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        '__RequestVerificationToken': token,
    }
    resp = session.post(f'{MODEM_URL}api/sms/sms-list', data=body, headers=headers)
    raw_xml = resp.text

    # 정규식으로 Message 블록 추출
    msg_blocks = re.findall(r'<Message>(.*?)</Message>', raw_xml, re.DOTALL)

    messages = []
    for block in msg_blocks:
        smstat = re.search(r'<Smstat>(\d)</Smstat>', block)
        if not smstat or smstat.group(1) != '0':
            continue

        index_m = re.search(r'<Index>(\d+)</Index>', block)
        phone_m = re.search(r'<Phone>(.*?)</Phone>', block)
        date_m = re.search(r'<Date>(.*?)</Date>', block)
        smstype_m = re.search(r'<SmsType>(\d+)</SmsType>', block)

        try:
            content_m = re.search(r'<Content>(.*?)</Content>', block, re.DOTALL)
            content = content_m.group(1).strip() if content_m else ''
        except Exception:
            content = '[인코딩 오류]'

        index = int(index_m.group(1)) if index_m else 0

        # MMS 감지 → 즉시 삭제
        if MMS_PATTERN in content:
            print(f'   ⚠️ [raw] MMS 감지 [{index}] → 삭제')
            try:
                from huawei_lte_api.Client import Client as _C
                # delete는 raw로 직접 처리
                tok_resp2 = session.get(f'{MODEM_URL}api/webserver/SesTokInfo')
                root2 = ET.fromstring(tok_resp2.text)
                token2 = root2.findtext('TokInfo', '')
                del_body = f'<?xml version="1.0" encoding="UTF-8"?><request><Index>{index}</Index></request>'
                del_headers = {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    '__RequestVerificationToken': token2,
                }
                session.post(f'{MODEM_URL}api/sms/delete-sms', data=del_body, headers=del_headers)
                print(f'   🗑️ MMS 삭제 완료 [{index}]')
            except Exception as de:
                print(f'   ❌ MMS 삭제 실패: {de}')
            continue

        messages.append({
            'index': index,
            'phone': phone_m.group(1) if phone_m else '',
            'content': content,
            'date': date_m.group(1) if date_m else '',
            'smsType': int(smstype_m.group(1)) if smstype_m else 1,
        })

    print(f'   [raw] 안읽은 SMS: {len(messages)}건')
    return messages


# ──────────────────────────────────────────────
# 전체 흐름
# ──────────────────────────────────────────────
def main():
    conn = Connection(MODEM_URL, username=MODEM_USER, password=MODEM_PASS)
    client = Client(conn)

    with conn:
        # 기기 정보 획득
        info = client.device.information()
        imei = info.get('Imei', '')
        msisdn = info.get('Msisdn', '')
        print(f'🔌 모뎀 연결: {info.get("DeviceName")} (IMEI: {imei}, 번호: {msisdn})')

        # [1] SMS 폴링
        messages = poll_sms(client, conn)

        if not messages:
            print('\n📭 안읽은 SMS 없음. 종료.')
            return

        # [2-3] 서버에 전송 + 응답 받기
        server_resp = mock_server_request(imei, msisdn, messages)

        if not server_resp.get('ok'):
            print('\n❌ 서버 응답 실패. 종료.')
            return

        # [4] 서버 응답 성공 → 읽음 처리 + 답장 발송
        replies = server_resp.get('replies', [])
        sent_indices = []  # 발송 후 발신함에서 삭제할 용도

        for reply in replies:
            phone = reply['phone']
            message = reply['message']

            # 원본 메시지 읽음 처리
            original = next((m for m in messages if m['phone'] == phone), None)
            if original:
                print(f'\n📖 [4] 읽음 처리 [{original["index"]}]')
                try:
                    client.sms.set_read(original['index'])
                    print(f'   ✅ 읽음 처리 완료')
                except Exception as e:
                    print(f'   ❌ 읽음 처리 실패: {e}')

            # [4] 답장 발송
            print(f'\n📤 [4] 답장 발송 → {phone}: "{message}"')
            try:
                client.sms.send_sms([phone], message)
                print(f'   ✅ 답장 발송 성공')
            except Exception as e:
                print(f'   ❌ 답장 발송 실패: {e}')
                continue

        # [5] 발송 확인 — 잠시 대기 (모뎀 처리 시간)
        print(f'\n⏳ [5] 발송 확인 대기 (2초)...')
        time.sleep(2)

        # 발신함 조회 → 방금 보낸 답장의 Index 확보
        outbox = client.sms.get_sms_list(
            1, box_type=BoxTypeEnum.LOCAL_SENT,
            read_count=50
        )
        sent_messages = outbox.get('Messages', {}).get('Message', [])
        if isinstance(sent_messages, dict):
            sent_messages = [sent_messages]

        for sent in sent_messages:
            sent_indices.append(int(sent.get('Index')))

        print(f'   발신함: {len(sent_indices)}건')

        # [6] 삭제 — 원본(읽은거) + 답장(발신함)
        print(f'\n🗑️ [6] 삭제 시작...')

        # 원본 삭제
        for msg in messages:
            try:
                client.sms.delete_sms(msg['index'])
                print(f'   ✅ 수신 삭제 [{msg["index"]}] {msg["phone"]}')
            except Exception as e:
                print(f'   ❌ 수신 삭제 실패 [{msg["index"]}]: {e}')

        # 발신함 삭제
        for idx in sent_indices:
            try:
                client.sms.delete_sms(idx)
                print(f'   ✅ 발신 삭제 [{idx}]')
            except Exception as e:
                print(f'   ❌ 발신 삭제 실패 [{idx}]: {e}')

        # 최종 상태
        print(f'\n📊 최종 상태:')
        count = client.sms.sms_count()
        print(f'   수신함: {count.get("LocalInbox", 0)}건')
        print(f'   발신함: {count.get("LocalOutbox", 0)}건')
        print(f'   안읽음: {count.get("LocalUnread", 0)}건')
        print(f'\n✅ 전체 흐름 완료!')


if __name__ == '__main__':
    main()
