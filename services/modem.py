"""모뎀 통신 서비스 — huawei-lte-api 래핑"""
import asyncio
import json
import os
import re

import xmltodict

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.sms import BoxTypeEnum

MMS_PATTERN = '¾¯'

RECONNECT_INTERVAL = 10  # 재연결 시도 간격 (초)
MODEM_TIMEOUT = int(os.getenv('MODEM_TIMEOUT', '30'))  # 모뎀 요청 타임아웃 (초)
SMS_MAX = 500
SMS_CLEANUP_THRESHOLD = int(SMS_MAX * 0.7)  # 350개
MODEMS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'modems.json')


def load_modem_configs() -> list:
    """modems.json → ModemService 리스트 생성"""
    with open(MODEMS_PATH) as f:
        configs = json.load(f)

    modems = []
    for i, cfg in enumerate(configs, 1):
        password = os.getenv(cfg.get('env_pass', ''), '')
        modem = ModemService(
            url=cfg['url'],
            user=cfg.get('user', 'admin'),
            password=password,
            label=f'모뎀{i}',
        )
        modems.append(modem)
    return modems


class ModemService:
    def __init__(self, url: str, user: str, password: str, label: str = '모뎀'):
        self.url = url
        self.user = user
        self.password = password
        self.label = label
        self.conn = None
        self.client = None
        self.imei = ''
        self.msisdn = ''
        self.connected = False

    async def connect(self):
        """모뎀 연결 + 기기 정보 획득"""
        def _connect():
            self.conn = Connection(self.url, username=self.user, password=self.password)
            self.client = Client(self.conn)
            info = self.client.device.information()
            self.imei = info.get('Imei', '')
            self.msisdn = info.get('Msisdn', '')
            return info

        info = await asyncio.wait_for(asyncio.to_thread(_connect), timeout=MODEM_TIMEOUT)
        self.connected = True

        if not self.msisdn:
            self.connected = False
            raise Exception(f'MSISDN 조회 불가 — SIM 카드 확인 필요')

        print(f'[{self.label}] 연결됨: {info.get("DeviceName")} (MSISDN: {self.msisdn})')

    async def reconnect(self):
        """모뎀 재연결 시도"""
        self.connected = False
        await self.disconnect()
        print(f'[{self.label}] 재연결 시도 중...')
        try:
            await self.connect()
            return True
        except Exception as e:
            print(f'[{self.label}] 재연결 실패: {e} ({RECONNECT_INTERVAL}초 후 재시도)')
            return False

    def _parse_sms_raw(self, raw: list) -> list:
        """SMS raw 데이터 → 메시지 리스트 파싱"""
        if isinstance(raw, dict):
            raw = [raw]

        messages = []
        seen = set()
        for sms in raw:
            content = sms.get('Content') or ''
            index = int(sms.get('Index', 0))
            phone = sms.get('Phone', '')
            date = sms.get('Date', '')
            is_read = sms.get('Smstat') != '0'

            sms_type = int(sms.get('SmsType', 1))
            is_mms = MMS_PATTERN in content or sms_type == 5

            # 읽은 메시지는 스킵 (단, 읽은 MMS는 삭제 대상으로 포함)
            if is_read and not is_mms:
                continue
            if is_read and is_mms:
                print(f'[{self.label}] 읽은 MMS 삭제 대상 [{index}]')
                messages.append({
                    'index': index,
                    'mms': True,
                    '_read_mms': True,
                })
                continue

            # MMS 중복 제거 (같은 번호 + 날짜 + 내용)
            dedup_key = (phone, date, content)
            if dedup_key in seen:
                print(f'[{self.label}] MMS 중복 스킵 [{index}] {phone}')
                messages.append({
                    'index': index,
                    '_duplicate': True,
                })
                continue
            seen.add(dedup_key)

            if is_mms:
                print(f'[{self.label}] MMS 감지 [{index}]')

            messages.append({
                'index': index,
                'phone': phone,
                'content': content,
                'date': date,
                'smsType': sms_type,
                'mms': is_mms,
            })
        return messages

    async def get_unread_sms(self) -> list:
        """안읽은 SMS 목록 조회 (XML 파싱 에러 시 개별 조회 fallback)"""
        def _get():
            sms_list = self.client.sms.get_sms_list(
                1, box_type=BoxTypeEnum.LOCAL_INBOX,
                read_count=50, sort_type=0, ascending=1,
                unread_preferred=True
            )
            raw = sms_list.get('Messages', {}).get('Message', [])
            return self._parse_sms_raw(raw)

        def _get_raw_xml():
            """XML 파싱 에러 시 raw XML 직접 요청 → invalid 문자 제거 후 파싱"""
            body = xmltodict.unparse({'request': {
                'PageIndex': 1,
                'ReadCount': 50,
                'BoxType': 1,
                'SortType': 0,
                'Ascending': 1,
                'UnreadPreferred': 1,
            }}).encode('utf-8')

            headers = {'Content-Type': 'application/xml'}
            if self.conn.request_verification_tokens:
                if len(self.conn.request_verification_tokens) > 1:
                    headers['__RequestVerificationToken'] = self.conn.request_verification_tokens.pop(0)
                else:
                    headers['__RequestVerificationToken'] = self.conn.request_verification_tokens[0]

            resp = self.conn.requests_session.post(
                f'{self.conn.url}api/sms/sms-list',
                data=body,
                headers=headers,
                timeout=MODEM_TIMEOUT,
            )

            # 응답 CSRF 토큰 갱신
            if '__RequestVerificationTokenone' in resp.headers:
                self.conn.request_verification_tokens.append(resp.headers['__RequestVerificationTokenone'])
                if '__RequestVerificationTokentwo' in resp.headers:
                    self.conn.request_verification_tokens.append(resp.headers['__RequestVerificationTokentwo'])
            elif '__RequestVerificationToken' in resp.headers:
                self.conn.request_verification_tokens.append(resp.headers['__RequestVerificationToken'])

            # XML invalid 문자 제거 (제어 문자 등)
            raw_xml = resp.content.decode('utf-8', errors='replace')
            clean_xml = re.sub(r'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]', '', raw_xml)

            data = xmltodict.parse(clean_xml, dict_constructor=dict)
            sms_list = data.get('response', {})
            raw = sms_list.get('Messages', {}).get('Message', [])
            return self._parse_sms_raw(raw)

        try:
            return await asyncio.wait_for(asyncio.to_thread(_get), timeout=MODEM_TIMEOUT)
        except Exception as e:
            if 'not well-formed' not in str(e) and 'invalid token' not in str(e):
                raise
            print(f'[{self.label}] XML 파싱 에러 — raw XML 직접 조회')
            return await asyncio.wait_for(asyncio.to_thread(_get_raw_xml), timeout=MODEM_TIMEOUT)

    async def set_read(self, index: int):
        """SMS 읽음 처리"""
        await asyncio.wait_for(asyncio.to_thread(self.client.sms.set_read, index), timeout=MODEM_TIMEOUT)

    async def send_sms(self, phone: str, message: str):
        """SMS 발송"""
        await asyncio.wait_for(asyncio.to_thread(self.client.sms.send_sms, [phone], message), timeout=MODEM_TIMEOUT)

    async def delete_sms(self, index: int):
        """SMS 삭제"""
        await asyncio.wait_for(asyncio.to_thread(self.client.sms.delete_sms, index), timeout=MODEM_TIMEOUT)

    async def get_sms_count(self) -> int:
        """SMS 총 개수 (수신+발신) 조회"""
        def _count():
            info = self.client.sms.sms_count()
            inbox = int(info.get('LocalInbox', 0))
            outbox = int(info.get('LocalOutbox', 0))
            draft = int(info.get('LocalDraft', 0))
            return inbox + outbox + draft
        return await asyncio.wait_for(asyncio.to_thread(_count), timeout=MODEM_TIMEOUT)

    async def cleanup_read_sms(self):
        """읽은 수신 SMS + 발신 SMS 삭제하여 용량 확보"""
        def _get_targets():
            indices = []

            # 수신함 — 읽은 것만 (Smstat == '1')
            inbox = self.client.sms.get_sms_list(
                1, box_type=BoxTypeEnum.LOCAL_INBOX,
                read_count=50, sort_type=0, ascending=1,
            )
            raw = inbox.get('Messages', {}).get('Message', [])
            if isinstance(raw, dict):
                raw = [raw]
            indices += [int(sms['Index']) for sms in raw if sms.get('Smstat') == '1']

            # 발신함 — 전체
            outbox = self.client.sms.get_sms_list(
                1, box_type=BoxTypeEnum.LOCAL_OUTBOX,
                read_count=50, sort_type=0, ascending=1,
            )
            raw = outbox.get('Messages', {}).get('Message', [])
            if isinstance(raw, dict):
                raw = [raw]
            indices += [int(sms['Index']) for sms in raw]

            return indices

        targets = await asyncio.wait_for(asyncio.to_thread(_get_targets), timeout=MODEM_TIMEOUT)
        if not targets:
            return 0

        deleted = 0
        for index in targets:
            try:
                await self.delete_sms(index)
                deleted += 1
            except Exception:
                pass
        print(f'[{self.label}] SMS {deleted}건 정리 완료 (수신 읽음 + 발신)')
        return deleted

    async def disconnect(self):
        """모뎀 연결 해제"""
        if self.conn:
            try:
                await asyncio.wait_for(asyncio.to_thread(self.conn.close), timeout=MODEM_TIMEOUT)
            except Exception:
                pass
