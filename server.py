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

from services.modem import load_modem_configs
from services.poller import poll_loop
from routes import sms as sms_routes

PORT = int(os.getenv('PORT', '3000'))


# ──────────────────────────────────────────────
# 서버 시작/종료
# ──────────────────────────────────────────────
modems = load_modem_configs()


async def on_startup(app: web.Application):
    """서버 시작 시 모뎀 연결 + 폴링 시작"""
    app['poller_tasks'] = []
    for modem in modems:
        try:
            await modem.connect()
        except Exception as e:
            print(f'[서버] {modem.label} 초기 연결 실패: {e}')
            print(f'[서버] 폴링 루프에서 재연결 시도합니다')
        task = asyncio.create_task(poll_loop(modem))
        app['poller_tasks'].append(task)
    print(f'[서버] {len(modems)}개 모뎀 폴링 시작')


async def on_cleanup(app: web.Application):
    """서버 종료 시 정리"""
    for task in app.get('poller_tasks', []):
        task.cancel()
    for modem in modems:
        await modem.disconnect()


app = web.Application()
sms_routes.setup(app)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == '__main__':
    print(f'SMS 서버 시작 → http://localhost:{PORT}')
    web.run_app(app, port=PORT, print=None)
