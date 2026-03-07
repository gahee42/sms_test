"""SMS API 서버 (aiohttp)

POST /v1/sms  — SMS 수신 저장 + 답장 응답
GET  /v1/sms  — 저장된 SMS 목록 조회

사용법:
  python server.py
"""
import json
import os
from datetime import datetime
from pathlib import Path

from aiohttp import web

PORT = int(os.getenv('PORT', '3000'))
LOG_PATH = Path(__file__).parent / 'sms_log.jsonl'


async def receive_sms(request: web.Request) -> web.Response:
    """POST /v1/sms — SMS 수신 저장 + echo 답장"""
    body = await request.json()

    imei = body.get('imei', '')
    msisdn = body.get('msisdn', '')
    messages = body.get('messages', [])

    # 저장
    entry = {
        'imei': imei,
        'msisdn': msisdn,
        'messages': messages,
        'received_at': datetime.now().isoformat(),
    }
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'[저장] {len(messages)}건 from {msisdn} (IMEI: {imei})')
    for msg in messages:
        print(f'  [{msg.get("index")}] {msg.get("phone")}: {msg.get("content")}')

    # echo 답장 생성
    replies = []
    for msg in messages:
        replies.append({
            'phone': msg.get('phone'),
            'message': f'[echo] {msg.get("content", "")}',
        })

    return web.json_response({'ok': True, 'replies': replies})


async def list_sms(request: web.Request) -> web.Response:
    """GET /v1/sms — 저장된 SMS 목록"""
    if not LOG_PATH.exists():
        return web.json_response([])

    entries = []
    for line in LOG_PATH.read_text().strip().split('\n'):
        if line:
            entries.append(json.loads(line))

    return web.json_response(entries)


app = web.Application()
app.router.add_post('/v1/sms', receive_sms)
app.router.add_get('/v1/sms', list_sms)

if __name__ == '__main__':
    print(f'SMS 서버 시작 → http://localhost:{PORT}')
    web.run_app(app, port=PORT, print=None)
