import os
os.environ['GMAIL_CLIENT_ID'] = 'demo-google-client'
os.environ['GMAIL_CLIENT_SECRET'] = 'demo-google-secret'
os.environ['GMAIL_REDIRECT_URI'] = 'http://localhost:8000/api/connectors/gmail/callback'
os.environ['SESSION_SECRET_KEY'] = 'gmail-phase5-secret'

import api_server
from fastapi.testclient import TestClient
from starlette.requests import Request

print('ROUTES')
for r in api_server.app.routes:
    if 'connectors' in getattr(r, 'path', ''):
        print(getattr(r, 'path', None), getattr(r, 'methods', None))
        scope = {'type': 'http', 'method': 'GET', 'path': '/api/connectors/gmail/connect', 'headers': [], 'query_string': b'', 'session': {}}
        try:
            print('MATCH', r.matches(scope))
        except Exception as exc:
            print('MATCH_ERR', type(exc).__name__, exc)

client = TestClient(api_server.app)
for path in ['/api/connectors/gmail/connect', '/api/connectors/gmail/status']:
    r = client.get(path)
    print('PATH', path, 'STATUS', r.status_code, 'LOCATION', r.headers.get('location'), 'BODY', r.text[:200])
