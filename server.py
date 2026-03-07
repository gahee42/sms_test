"""SMS API 서버 (aiohttp) + 모뎀 폴링

make run 으로 실행하면:
  - API 서버 (포트 3000) 시작
  - 모뎀 폴링 백그라운드 자동 시작

API:
  POST /v1/sms  — SMS 수신 저장 + 답장 응답
  GET  /v1/sms  — 저장된 SMS 목록 조회
"""
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from aiohttp import web

from services.modem import ModemService
from services.poller import poll_loop
from routes import sms as sms_routes

PORT = int(os.getenv('PORT', '3000'))


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
sms_routes.setup(app)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == '__main__':
    print(f'SMS 서버 시작 → http://localhost:{PORT}')
    web.run_app(app, port=PORT, print=None)
