"""답장 생성 서비스

나중에 echo → AI 답장 등으로 바꿀 때 이 파일만 수정하면 됨
"""


def generate(messages: list) -> list:
    """수신 메시지 목록 → 답장 목록 생성"""
    replies = []
    for msg in messages:
        if msg.get('mms'):
            text = '[AI 발신] 지원하지 않는 형식의 문자입니다.'
        else:
            text = f'[AI 발신] {msg.get("content", "")}'

        replies.append({
            'phone': msg.get('phone'),
            'message': text,
        })
    return replies
