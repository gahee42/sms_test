"""스팸 필터 — 번호 prefix + 키워드 기반"""

BLOCK_PREFIXES = ['070']

BLOCK_KEYWORDS = ['대출', '보험', '당첨', '무료상담', '투자', '광고']


def is_spam(message: dict) -> bool:
    phone = message.get('phone', '')
    content = message.get('content', '')

    for prefix in BLOCK_PREFIXES:
        if phone.startswith(prefix):
            return True

    for keyword in BLOCK_KEYWORDS:
        if keyword in content:
            return True

    return False
