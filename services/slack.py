"""Slack 알림 서비스

SMS 수신/답장/에러를 슬랙 채널로 알림
SLACK_WEBHOOK_URL 이 없으면 알림 없이 조용히 무시
"""
import os

import aiohttp

WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')


async def _send(payload: dict):
    """슬랙 웹훅으로 payload 전송 (실패해도 예외 안 던짐)"""
    if not WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f'[슬랙] 알림 실패: {e}')


async def notify(text: str):
    """단순 텍스트 알림"""
    await _send({'text': text})


# ── 모뎀 ────────────────────────────────────────

async def modem_connected(label: str, msisdn: str):
    """모뎀 연결 성공"""
    await _send({'attachments': [{
        'color': '#36a64f',
        'text': f'📡 *{label}* 연결됨\nMSISDN: `{msisdn}`',
    }]})


async def modem_disconnected(label: str, reason: str):
    """모뎀 연결 해제 / 실패"""
    await _send({'attachments': [{
        'color': '#ff0000',
        'text': f'📡 *{label}* 연결 끊김\n사유: {reason}',
    }]})


async def modem_reconnect_failed(label: str, error: str):
    """모뎀 재연결 실패"""
    await _send({'attachments': [{
        'color': '#ff0000',
        'text': f'🔄 *{label}* 재연결 실패\n{error}',
    }]})


# ── SMS 수신/발신 ────────────────────────────────

async def sms_received(messages: list):
    """SMS 수신 알림"""
    lines = []
    for msg in messages:
        phone = msg.get('phone', '?')
        content = msg.get('content', '')
        tag = ' [MMS]' if msg.get('mms') else ''
        lines.append(f'• `{phone}`{tag} {content[:50]}')

    await _send({'attachments': [{
        'color': '#2196F3',
        'text': f'📩 *SMS {len(messages)}건 수신*\n' + '\n'.join(lines),
    }]})


async def sms_replied(phone: str, message: str):
    """답장 발송 성공"""
    await _send({'attachments': [{
        'color': '#36a64f',
        'text': f'✅ 답장 발송 → `{phone}`\n{message[:100]}',
    }]})


async def sms_reply_failed(phone: str, error: str):
    """답장 발송 실패"""
    await _send({'attachments': [{
        'color': '#ff0000',
        'text': f'❌ 답장 실패 → `{phone}`\n{error}',
    }]})


async def sms_spam_skipped(phone: str):
    """스팸 답장 스킵"""
    await _send({'attachments': [{
        'color': '#FFA500',
        'text': f'🚫 스팸 답장 스킵 → `{phone}`',
    }]})


# ── 서버 ────────────────────────────────────────

async def server_error(label: str, error: str):
    """서버 API 에러"""
    await _send({'attachments': [{
        'color': '#ff0000',
        'text': f'🖥️ *서버 API 에러* [{label}]\n{error}',
    }]})


async def server_response_failed(label: str, result: dict):
    """서버 응답 실패 (ok: false)"""
    await _send({'attachments': [{
        'color': '#FFA500',
        'text': f'🖥️ *서버 응답 실패* [{label}]\n{result}',
    }]})


# ── 시스템 ───────────────────────────────────────

async def polling_started(label: str, interval: int):
    """폴링 시작"""
    await _send({'attachments': [{
        'color': '#36a64f',
        'text': f'🔁 *{label}* 폴링 시작 ({interval}초 간격)',
    }]})


async def poll_ok(label: str, msisdn: str):
    """폴링 성공 (수신 메시지 없음) — 연결 확인용"""
    await _send({'attachments': [{
        'color': '#36a64f',
        'text': f'💚 *{label}* (`{msisdn}`) 폴링 OK — 수신 없음',
    }]})


async def mms_parse_skipped(label: str, skipped: int):
    """MMS XML 파싱 실패로 스킵된 메시지"""
    await _send({'attachments': [{
        'color': '#FFA500',
        'text': f'⚠️ *{label}* MMS {skipped}건 XML 파싱 실패 — 스킵',
    }]})


async def cleanup_done(label: str, deleted: int, remaining: int):
    """SMS 정리 완료"""
    await _send({'attachments': [{
        'color': '#9E9E9E',
        'text': f'🧹 *{label}* SMS 정리: {deleted}건 삭제 (잔여 {remaining}건)',
    }]})


async def error(context: str, err: Exception):
    """일반 에러"""
    await _send({'attachments': [{
        'color': '#ff0000',
        'text': f'🚨 *에러* [{context}]\n{err}',
    }]})


# ── 하위 호환 ────────────────────────────────────

async def modem_status(status: str):
    """기존 호환용 (deprecated)"""
    await notify(f'📡 모뎀: {status}')
