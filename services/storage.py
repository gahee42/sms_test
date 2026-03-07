"""SMS 저장/조회 서비스"""
import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / 'sms_log.jsonl'


def save(imei: str, msisdn: str, messages: list):
    """SMS를 jsonl 파일에 저장"""
    entry = {
        'imei': imei,
        'msisdn': msisdn,
        'messages': messages,
        'received_at': datetime.now().isoformat(),
    }
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'[저장] {len(messages)}건 from {msisdn}')


def get_all() -> list:
    """저장된 SMS 전체 조회"""
    if not LOG_PATH.exists():
        return []

    entries = []
    for line in LOG_PATH.read_text().strip().split('\n'):
        if line:
            entries.append(json.loads(line))
    return entries
