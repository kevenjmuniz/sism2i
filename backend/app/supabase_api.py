import os
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from .db import BASE_DIR

load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip() or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
)
SUPABASE_REST_MODE = os.getenv("SUPABASE_REST_MODE", "").strip().lower() in {"1", "true", "yes", "sim"}


def enabled():
    return bool(SUPABASE_REST_MODE and SUPABASE_URL and SUPABASE_KEY)


def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def table_upsert(table, payload, on_conflict, ignore=False):
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    headers = _headers()
    resolution = "ignore-duplicates" if ignore else "merge-duplicates"
    headers["Prefer"] = f"resolution={resolution},return=representation"
    with httpx.Client(timeout=60) as client:
        response = client.post(
            url,
            params={"on_conflict": on_conflict},
            headers=headers,
            json=[payload],
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Erro Supabase upsert {table}: {response.status_code} - {response.text}")
    data = response.json()
    return data[0] if data else None


def table_upsert_many(table, payloads, on_conflict, ignore=False, chunk_size=500):
    if not payloads:
        return []
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    headers = _headers()
    resolution = "ignore-duplicates" if ignore else "merge-duplicates"
    headers["Prefer"] = f"resolution={resolution},return=representation"
    result = []
    with httpx.Client(timeout=120) as client:
        for start in range(0, len(payloads), chunk_size):
            chunk = payloads[start : start + chunk_size]
            response = client.post(
                url,
                params={"on_conflict": on_conflict},
                headers=headers,
                json=chunk,
            )
            if response.status_code >= 400:
                raise RuntimeError(f"Erro Supabase upsert {table}: {response.status_code} - {response.text}")
            if response.text:
                result.extend(response.json())
    return result


def table_delete_all(table):
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    with httpx.Client(timeout=60) as client:
        response = client.delete(
            url,
            params={"id": "not.is.null"},
            headers=_headers(),
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Erro Supabase delete {table}: {response.status_code} - {response.text}")


def table_patch(table, column, value, payload):
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    with httpx.Client(timeout=60) as client:
        response = client.patch(
            url,
            params={column: f"eq.{quote(str(value), safe='')}"},
            headers=headers,
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Erro Supabase update {table}: {response.status_code} - {response.text}")
    return response.json() if response.text else []


def rpc(name, payload=None):
    if not enabled():
        raise RuntimeError("Supabase REST nao configurado.")
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/{name}"
    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=_headers(), json=payload or {})
    if response.status_code >= 400:
        raise RuntimeError(f"Erro Supabase RPC {name}: {response.status_code} - {response.text}")
    return response.json()


def healthcheck():
    return rpc("api_healthcheck", {})
