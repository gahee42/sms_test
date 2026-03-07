"""SMS API 서버 (aiohttp) + 모뎀 폴링

make run 으로 실행하면:
  - API 서버 (포트 3000) 시작
  - 모뎀 폴링 백그라운드 자동 시작

API:
  POST /v1/sms  — SMS 수신 저장 + 답장 응답
  GET  /v1/sms  — 저장된 SMS 목록 조회
"""
import asyncio
import json
import os
from pathlib import Path

from aiohttp import web

from services.modem import ModemService
from services.poller import poll_loop, save_and_reply

PORT = int(os.getenv('PORT', '3000'))
LOG_PATH = Path(__file__).parent / 'sms_log.jsonl'


# ──────────────────────────────────────────────
# API 라우트
# ──────────────────────────────────────────────
async def receive_sms(request: web.Request) -> web.Response:
    """POST /v1/sms — SMS 수신 저장 + echo 답장"""
    body = await request.json()
    result = save_and_reply(
        body.get('imei', ''),
        body.get('msisdn', ''),
        body.get('messages', []),
    )
    return web.json_response(result)


async def list_sms(request: web.Request) -> web.Response:
    """GET /v1/sms — 저장된 SMS 목록"""
    if not LOG_PATH.exists():
        return web.json_response([])

    entries = []
    for line in LOG_PATH.read_text().strip().split('\n'):
        if line:
            entries.append(json.loads(line))

    return web.json_response(entries)


# ──────────────────────────────────────────────
# 서버 시작/종료
# ──────────────────────────────────────────────
modem = ModemService()


async def on_startup(app: web.Application):
    """서버 시작 시 모뎀 연결 + 폴링 시작"""
    try:
        await modem.connect()
        app['poller_task'] = asyncio.create_task(poll_loop(modem))
    except Exception as e:
        print(f'[서버] 모뎀 연결 실패: {e}')
        print(f'[서버] API만 실행됩니다 (폴링 없음)')


async def on_cleanup(app: web.Application):
    """서버 종료 시 정리"""
    task = app.get('poller_task')
    if task:
        task.cancel()
    await modem.disconnect()


app = web.Application()
app.router.add_post('/v1/sms', receive_sms)
app.router.add_get('/v1/sms', list_sms)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == '__main__':
    print(f'SMS 서버 시작 → http://localhost:{PORT}')
    web.run_app(app, port=PORT, print=None)
