import httpx

TIMEOUT = httpx.Timeout(20.0)

def get_client(headers=None, params=None) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, headers=headers, params=params)
