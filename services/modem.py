"""모뎀 통신 서비스 — huawei-lte-api 래핑"""
import asyncio
import json
import os

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.sms import BoxTypeEnum

MMS_PATTERN = '¾¯'

RECONNECT_INTERVAL = 10  # 재연결 시도 간격 (초)
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

        info = await asyncio.to_thread(_connect)
        self.connected = True
        print(f'[{self.label}] 연결됨: {info.get("DeviceName")} (IMEI: {self.imei})')

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

    async def get_unread_sms(self) -> list:
        """안읽은 SMS 목록 조회 (MMS 자동 삭제)"""
        def _get():
            sms_list = self.client.sms.get_sms_list(
                1, box_type=BoxTypeEnum.LOCAL_INBOX,
                read_count=50, sort_type=0, ascending=1,
                unread_preferred=True
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

                sms_type = int(sms.get('SmsType', 1))
                is_mms = MMS_PATTERN in content or sms_type == 5
                if is_mms:
                    print(f'[{self.label}] MMS 감지 [{index}]')

                messages.append({
                    'index': index,
                    'phone': sms.get('Phone', ''),
                    'content': content,
                    'date': sms.get('Date', ''),
                    'smsType': sms_type,
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
