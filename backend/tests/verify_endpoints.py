import urllib.request
import json

endpoints = [
    '/api/v1/conversations',
    '/api/v1/settings/power',
    '/api/v1/settings/whatsapp',
    '/api/v1/security/lock-folders',
    '/api/add-path',
    '/api/v1/settings/desktop-overlay',
    '/api/profile',
    '/api/v1/system/overview',
    '/api/v1/mcp/status'
]

passed = 0
for ep in endpoints:
    url = f'http://127.0.0.1:8000{ep}'
    try:
        req = urllib.request.urlopen(url, timeout=10)
        print(f'[OK {req.status}] {ep}')
        passed += 1
    except Exception as e:
        print(f'[FAIL] {ep}: {e}')

print(f"\nResult: {passed}/{len(endpoints)} endpoints operational.")
