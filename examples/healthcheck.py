# healthcheck script for Docker

import requests
import sys

url = 'http://127.0.0.1:8000/service/health'

try:
    resp = requests.get(url, timeout=1.0)
except:
    sys.exit(1)

if resp.status_code != 200:
    sys.exit(1)
