import hashlib
import os

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from settlement import minimum_cash_flow

app = FastAPI(title='Settlement Service')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

DJANGO_URL = os.environ.get('DJANGO_URL', 'http://127.0.0.1:8000')
DJANGO_SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production'
)
INTERNAL_TOKEN = hashlib.sha256(
    (DJANGO_SECRET_KEY + ':settlement-service').encode()
).hexdigest()

JWT_SECRET = DJANGO_SECRET_KEY
JWT_ALG = 'HS256'


class SettleRequest(BaseModel):
    group_id: int


def authenticate_user_token(access_token: str) -> int:
    """Verify the caller's Django-issued JWT and return their user id.

    Tenant identity is derived from the verified token, never from a
    client-sent user or group membership claim.
    """
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(payload['user_id'])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail='invalid or expired token')


def get_token_from_request(request: Request) -> str:
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='missing bearer token')
    return auth[len('Bearer '):]


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/settle')
def settle(req: SettleRequest, request: Request):
    """Main endpoint.

    The caller must present their own Django JWT. We verify it here, then
    forward it when fetching the group data from Django, which re-checks
    that this user is actually a member of the group (defense in depth for
    tenant isolation — the settlement service never trusts the client's
    group_id beyond an id to look up, and Django refuses to serve data for
    groups the token's user doesn't belong to).
    """
    token = get_token_from_request(request)
    user_id = authenticate_user_token(token)

    try:
        resp = httpx.get(
            f'{DJANGO_URL}/api/internal/groups/{req.group_id}/',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Internal-Token': INTERNAL_TOKEN,
            },
            timeout=10,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail='core API unavailable')

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail='group not found')
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f'core API error: {resp.status_code}')

    data = resp.json()
    balances = {m['user_id']: m['balance_cents'] for m in data['members']}
    transfers = minimum_cash_flow(balances)

    names = {m['user_id']: m['username'] for m in data['members']}
    return {
        'group_id': data['group_id'],
        'group_name': data['name'],
        'transfers': [
            {
                'from': {'user_id': t['from'], 'username': names.get(t['from'], '?')},
                'to': {'user_id': t['to'], 'username': names.get(t['to'], '?')},
                'amount_cents': t['amount_cents'],
            }
            for t in transfers
        ],
    }

