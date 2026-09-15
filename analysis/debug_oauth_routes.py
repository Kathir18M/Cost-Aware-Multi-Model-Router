import os
os.environ['GITHUB_CLIENT_ID']='demo-client'
os.environ['GITHUB_CLIENT_SECRET']='demo-secret'
os.environ['GITHUB_REDIRECT_URI']='http://localhost:8000/api/connectors/github/callback'
os.environ['SESSION_SECRET_KEY']='phase4-test-secret'
import api_server
from fastapi.testclient import TestClient
print('ROUTES', [(r.path, getattr(r, 'methods', None)) for r in api_server.app.routes if 'connectors' in str(getattr(r, 'path', ''))])
print('route exists?', any(getattr(r, 'path', None) == '/api/connectors/github/connect' for r in api_server.app.routes))
print('generic exists?', any(getattr(r, 'path', None) == '/api/connectors/{provider}/connect' for r in api_server.app.routes))
client = TestClient(api_server.app)
resp = client.get('/api/connectors/github/connect')
print('STATUS', resp.status_code)
print('HEADERS', dict(resp.headers))
print('BODY', resp.text)
