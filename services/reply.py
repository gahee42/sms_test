"""답장 생성 서비스

나중에 echo → AI 답장 등으로 바꿀 때 이 파일만 수정하면 됨
"""


def generate(messages: list) -> list:
    """수신 메시지 목록 → 답장 목록 생성"""
    replies = []
    replied_mms = set()  # MMS 중복 답장 방지 (같은 번호 1번만)

    for msg in messages:
        content = msg.get('content', '').strip()
        phone = msg.get('phone')

        if msg.get('mms') or not content:
            if phone in replied_mms:
                continue
            replied_mms.add(phone)
            text = '[AI 발신] 지원하지 않는 형식의 문자입니다.'
        else:
            text = f'[AI 발신] {content}'

        replies.append({
            'phone': phone,
            'message': text,
        })
    return replies
