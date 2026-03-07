"""SMS API 라우트 — NestJS의 Controller 역할"""
from aiohttp import web

from services import storage, reply


async def receive_sms(request: web.Request) -> web.Response:
    """POST /v1/sms — SMS 수신 저장 + echo 답장"""
    body = await request.json()
    imei = body.get('imei', '')
    msisdn = body.get('msisdn', '')
    messages = body.get('messages', [])

    storage.save(imei, msisdn, messages)
    replies = reply.generate(messages)

    return web.json_response({'ok': True, 'replies': replies})


async def list_sms(request: web.Request) -> web.Response:
    """GET /v1/sms — 저장된 SMS 목록"""
    return web.json_response(storage.get_all())


def setup(app: web.Application):
    """라우트 등록"""
    app.router.add_post('/v1/sms', receive_sms)
    app.router.add_get('/v1/sms', list_sms)
