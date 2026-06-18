import csv
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from . import supabase_api
from . import supabase_store
from .db import get_connection, init_db

CNPJ_COLUMNS = ["CNPJ / CPF", "CNPJ/CPF", "CPF/CNPJ", "Documento"]
ADDRESS_COLUMNS = ["Endereço", "Endereco", "Endereço Completo", "Endereco Completo"]


def normalize_document(value):
    return re.sub(r"\D+", "", str(value or ""))


def client_document(row):
    return normalize_document(row.get("cnpj_cpf") or row.get("cnpj") or row.get("CNPJ/CPF") or row.get("CNPJ / CPF"))


def clean_key(value):
    return (value or "").lstrip("\ufeff").strip()


def sniff_dialect(sample):
    try:
        return csv.Sniffer().sniff(sample, delimiters=";\t,")
    except csv.Error:
        return csv.excel


def pick_column(headers, candidates):
    normalized = {clean_key(header).lower(): clean_key(header) for header in headers or []}
    for candidate in candidates:
        found = normalized.get(candidate.lower())
        if found:
            return found
    return None


def load_address_rows(path):
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        sample = file.read(4096)
        file.seek(0)
        reader = csv.DictReader(file, dialect=sniff_dialect(sample))
        headers = [clean_key(header) for header in reader.fieldnames or []]
        document_column = pick_column(headers, CNPJ_COLUMNS)
        address_column = pick_column(headers, ADDRESS_COLUMNS)
        if not document_column:
            raise ValueError("Coluna de CNPJ/CPF não encontrada no CSV de clientes.")
        if not address_column:
            raise ValueError("Coluna de endereço não encontrada no CSV de clientes.")

        result = []
        for raw in reader:
            row = {clean_key(key): (value.strip() if isinstance(value, str) else value) for key, value in raw.items()}
            document = normalize_document(row.get(document_column))
            address = row.get(address_column, "").strip()
            result.append({"document": document, "address": address})
        return result


def import_client_addresses_local(path):
    init_db()
    address_rows = load_address_rows(path)
    with get_connection() as conn:
        existing = {
            normalize_document(row["cnpj_cpf"]): row["id"]
            for row in conn.execute("SELECT id, cnpj_cpf FROM clientes").fetchall()
            if normalize_document(row["cnpj_cpf"])
        }
        updated_ids = set()
        with_address = matched = skipped_without_address = unmatched = 0
        for row in address_rows:
            if not row["address"]:
                skipped_without_address += 1
                continue
            with_address += 1
            client_id = existing.get(row["document"])
            if not client_id:
                unmatched += 1
                continue
            matched += 1
            conn.execute("UPDATE clientes SET endereco = ? WHERE id = ?", (row["address"], client_id))
            updated_ids.add(client_id)

    return {
        "rows": len(address_rows),
        "with_address": with_address,
        "matched": matched,
        "updated": len(updated_ids),
        "unmatched": unmatched,
        "skipped_without_address": skipped_without_address,
        "mode": "local",
    }


def import_client_addresses_supabase(path):
    if not supabase_api.enabled():
        raise RuntimeError("Supabase REST não configurado.")
    address_rows = load_address_rows(path)
    clientes = supabase_store.table("clientes")
    existing = {
        client_document(row): row.get("id")
        for row in clientes
        if client_document(row)
    }
    updated_ids = set()
    with_address = matched = skipped_without_address = unmatched = 0
    for row in address_rows:
        if not row["address"]:
            skipped_without_address += 1
            continue
        with_address += 1
        client_id = existing.get(row["document"])
        if not client_id:
            unmatched += 1
            continue
        matched += 1
        supabase_api.table_patch("clientes", "id", client_id, {"endereco": row["address"]})
        updated_ids.add(client_id)
    supabase_store.invalidate_snapshot_cache()
    return {
        "rows": len(address_rows),
        "with_address": with_address,
        "matched": matched,
        "updated": len(updated_ids),
        "unmatched": unmatched,
        "skipped_without_address": skipped_without_address,
        "mode": "supabase-rest",
    }


def import_client_addresses(path):
    if supabase_api.enabled():
        return import_client_addresses_supabase(path)
    return import_client_addresses_local(path)


async def import_client_addresses_upload(upload_file):
    suffix = Path(upload_file.filename or "clientes.csv").suffix or ".csv"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        content = await upload_file.read()
        temp.write(content)
        temp_path = temp.name
    return import_client_addresses(temp_path)
