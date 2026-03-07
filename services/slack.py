"""Slack 알림 서비스

SMS 수신/답장/에러를 슬랙 채널로 알림
SLACK_WEBHOOK_URL 이 없으면 알림 없이 조용히 무시
"""
import os

import aiohttp

WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')


async def notify(text: str):
    """슬랙 웹훅으로 메시지 전송 (실패해도 예외 안 던짐)"""
    if not WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(WEBHOOK_URL, json={'text': text})
    except Exception as e:
        print(f'[슬랙] 알림 실패: {e}')


async def sms_received(messages: list):
    """SMS 수신 알림"""
    lines = [f'📩 *SMS {len(messages)}건 수신*']
    for msg in messages:
        sender = msg.get('phone', '?')
        content = msg.get('content', '')
        tag = '[MMS]' if msg.get('mms') else ''
        lines.append(f'  • {sender} {tag} {content[:50]}')
    await notify('\n'.join(lines))


async def sms_replied(phone: str, message: str):
    """답장 발송 알림"""
    await notify(f'✅ 답장 발송 → {phone}\n{message[:100]}')


async def error(context: str, err: Exception):
    """에러 알림"""
    await notify(f'🚨 *에러* [{context}]\n{err}')


async def modem_status(status: str):
    """모뎀 상태 변경 알림"""
    await notify(f'📡 모뎀: {status}')
