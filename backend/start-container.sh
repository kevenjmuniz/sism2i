#!/bin/sh
set -eu

: "${AUTH_USERNAME:?Defina AUTH_USERNAME no ambiente do serviço}"
: "${AUTH_PASSWORD:?Defina AUTH_PASSWORD no ambiente do serviço}"
: "${AUTH_SECRET:?Defina AUTH_SECRET no ambiente do serviço}"

if [ "$AUTH_PASSWORD" = admin ] || [ "${#AUTH_SECRET}" -lt 32 ]; then
    echo 'Defina uma senha diferente de admin e um AUTH_SECRET com pelo menos 32 caracteres.' >&2
    exit 1
fi

if [ "$SUPABASE_REST_MODE" = true ]; then
    : "${SUPABASE_URL:?Defina SUPABASE_URL no ambiente do serviço}"
    : "${SUPABASE_SERVICE_ROLE_KEY:-${SUPABASE_PUBLISHABLE_KEY:?Defina uma chave Supabase no ambiente do serviço}}"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8013
