"""모뎀 통신 서비스 — huawei-lte-api 래핑"""
import asyncio
import os

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.sms import BoxTypeEnum

MODEM_URL = os.getenv('MODEM_URL', '')
MODEM_USER = os.getenv('MODEM_USER', '')
MODEM_PASS = os.getenv('MODEM_PASS', '')

MMS_PATTERN = '¾¯'


class ModemService:
    def __init__(self):
        self.conn = None
        self.client = None
        self.imei = ''
        self.msisdn = ''

    async def connect(self):
        """모뎀 연결 + 기기 정보 획득"""
        def _connect():
            self.conn = Connection(MODEM_URL, username=MODEM_USER, password=MODEM_PASS)
            self.client = Client(self.conn)
            info = self.client.device.information()
            self.imei = info.get('Imei', '')
            self.msisdn = info.get('Msisdn', '')
            return info

        info = await asyncio.to_thread(_connect)
        print(f'[모뎀] 연결됨: {info.get("DeviceName")} (IMEI: {self.imei})')

    async def get_unread_sms(self) -> list:
        """안읽은 SMS 목록 조회 (MMS 자동 삭제)"""
        def _get():
            sms_list = self.client.sms.get_sms_list(
                1, box_type=BoxTypeEnum.LOCAL_INBOX,
                read_count=50, unread_preferred=True
            )
            raw = sms_list.get('Messages', {}).get('Message', [])
            if isinstance(raw, dict):
                raw = [raw]

            messages = []
            for sms in raw:
                if sms.get('Smstat') != '0':
                    continue

                content = sms.get('Content') or ''
                index = int(sms.get('Index', 0))

                is_mms = MMS_PATTERN in content
                if is_mms:
                    print(f'[모뎀] MMS 감지 [{index}]')

                messages.append({
                    'index': index,
                    'phone': sms.get('Phone', ''),
                    'content': content,
                    'date': sms.get('Date', ''),
                    'smsType': int(sms.get('SmsType', 1)),
                    'mms': is_mms,
                })
            return messages

        return await asyncio.to_thread(_get)

    async def set_read(self, index: int):
        """SMS 읽음 처리"""
        await asyncio.to_thread(self.client.sms.set_read, index)

    async def send_sms(self, phone: str, message: str):
        """SMS 발송"""
        await asyncio.to_thread(self.client.sms.send_sms, [phone], message)

    async def delete_sms(self, index: int):
        """SMS 삭제"""
        await asyncio.to_thread(self.client.sms.delete_sms, index)

    async def disconnect(self):
        """모뎀 연결 해제"""
        if self.conn:
            try:
                await asyncio.to_thread(self.conn.close)
            except Exception:
                pass
