from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import time

import httpx

from . import supabase_api

_snapshot_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 300  # 5 minutos


def num(value):
    if value is None or value == "":
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def parse_iso(value):
    if not value:
        return None
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def days_between(start, end):
    if not start or not end:
        return None
    return (end - start).days


def status_from(days_without, avg_frequency, order_count):
    if days_without is None:
        return "Perdido"
    if order_count >= 3 and avg_frequency:
        if days_without <= avg_frequency * 1.25:
            return "Ativo"
        if days_without <= avg_frequency * 2:
            return "Atenção"
        if days_without <= avg_frequency * 3:
            return "Inativo"
        return "Perdido"
    if days_without <= 30:
        return "Ativo"
    if days_without <= 60:
        return "Atenção"
    if days_without <= 90:
        return "Inativo"
    return "Perdido"


def status_rank(status):
    return {"Ativo": 1, "Atenção": 2, "Inativo": 3, "Perdido": 4}.get(status, 9)


def status_color(status):
    return {
        "Ativo": "green",
        "Atenção": "yellow",
        "Inativo": "orange",
        "Perdido": "red",
    }.get(status, "gray")


def table(name, order=None):
    url = f"{supabase_api.SUPABASE_URL.rstrip('/')}/rest/v1/{name}"
    headers = {
        "apikey": supabase_api.SUPABASE_KEY,
        "Authorization": f"Bearer {supabase_api.SUPABASE_KEY}",
    }
    params = {"select": "*"}
    if order:
        params["order"] = order
    data = []
    start = 0
    page_size = 1000
    with httpx.Client(timeout=60) as client:
        while True:
            response = client.get(
                url,
                params=params,
                headers={**headers, "Range": f"{start}-{start + page_size - 1}"},
            )
            if response.status_code >= 400:
                raise RuntimeError(f"Erro Supabase tabela {name}: {response.status_code} - {response.text}")
            page = response.json()
            data.extend(page)
            if len(page) < page_size:
                break
            start += page_size
    return data


def invalidate_snapshot_cache():
    _snapshot_cache["data"] = None
    _snapshot_cache["ts"] = 0.0


def snapshot():
    now = time.time()
    if _snapshot_cache["data"] is not None and now - _snapshot_cache["ts"] < _CACHE_TTL:
        return _snapshot_cache["data"]
    clientes = {row["id"]: row for row in table("clientes")}
    produtos = {row["id"]: row for row in table("produtos")}
    pedidos = {row["id"]: row for row in table("pedidos")}
    notas = {row["id"]: row for row in table("notas_fiscais")}
    itens = table("itens_pedido")
    data = (clientes, produtos, pedidos, notas, itens)
    _snapshot_cache["data"] = data
    _snapshot_cache["ts"] = now
    return data


def match_text(value, term):
    if not term:
        return True
    return term.lower() in str(value or "").lower()


def item_rows(filters=None):
    filters = filters or {}
    clientes, produtos, pedidos, notas, itens = snapshot()
    rows = []
    for item in itens:
        pedido = pedidos.get(item.get("pedido_id")) or {}
        cliente = clientes.get(pedido.get("cliente_id")) or {}
        produto = produtos.get(item.get("produto_id")) or {}
        nota = notas.get(item.get("nota_fiscal_id")) or {}
        data = nota.get("data_faturamento") or pedido.get("data_faturamento") or pedido.get("data_inclusao")

        if filters.get("start") and (not data or data < filters["start"]):
            continue
        if filters.get("end") and (not data or data > filters["end"]):
            continue
        if filters.get("cliente") and not (
            match_text(cliente.get("razao_social"), filters["cliente"])
            or match_text(cliente.get("nome_fantasia"), filters["cliente"])
            or match_text(cliente.get("cnpj_cpf"), filters["cliente"])
        ):
            continue
        if filters.get("cliente_id") and int(cliente.get("id") or 0) != int(filters["cliente_id"]):
            continue
        if filters.get("produto") and not (
            match_text(produto.get("descricao"), filters["produto"])
            or match_text(produto.get("codigo"), filters["produto"])
        ):
            continue
        if filters.get("vendedor") and pedido.get("vendedor") != filters["vendedor"]:
            continue
        if filters.get("cidade") and cliente.get("cidade") != filters["cidade"]:
            continue
        if filters.get("estado") and cliente.get("estado") != filters["estado"]:
            continue
        if filters.get("familia") and produto.get("familia") != filters["familia"]:
            continue

        rows.append({"item": item, "pedido": pedido, "cliente": cliente, "produto": produto, "nota": nota, "data": data})
    return rows


def client_metrics(filters=None, q=None, limit=None, only_status=None, _rows=None):
    filters = filters or {}
    rows = _rows if _rows is not None else item_rows(filters)
    today = date.today()
    by_client = defaultdict(
        lambda: {
            "cliente": None,
            "total": 0.0,
            "pedidos": set(),
            "dates": set(),
            "products": defaultdict(lambda: {"quantidade": 0.0, "valor": 0.0, "pedidos": set(), "ultima": None, "produto": None}),
        }
    )

    for r in rows:
        cliente = r["cliente"]
        if q and not (
            match_text(cliente.get("razao_social"), q)
            or match_text(cliente.get("nome_fantasia"), q)
            or match_text(cliente.get("cnpj_cpf"), q)
        ):
            continue

        client_id = cliente.get("id")
        entry = by_client[client_id]
        entry["cliente"] = cliente
        entry["total"] += num(r["item"].get("total_mercadoria"))
        entry["pedidos"].add(r["pedido"].get("id"))
        if r["data"]:
            entry["dates"].add(r["data"][:10])

        product_id = r["produto"].get("id")
        product = entry["products"][product_id]
        product["produto"] = r["produto"]
        product["quantidade"] += num(r["item"].get("quantidade"))
        product["valor"] += num(r["item"].get("total_mercadoria"))
        product["pedidos"].add(r["pedido"].get("id"))
        product["ultima"] = max(product["ultima"] or "", r["data"] or "") or None

    result = []
    for entry in by_client.values():
        cliente = entry["cliente"]
        dates = sorted(parse_iso(d) for d in entry["dates"] if d)
        first = dates[0] if dates else None
        last = dates[-1] if dates else None
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        avg_frequency = sum(gaps) / len(gaps) if gaps else None
        days_without = days_between(last, today)
        order_count = len(entry["pedidos"])
        ticket = entry["total"] / order_count if order_count else 0
        status = status_from(days_without, avg_frequency, order_count)
        top_products = sorted(entry["products"].values(), key=lambda p: p["quantidade"], reverse=True)
        product_names = ", ".join([p["produto"].get("descricao") for p in top_products[:3] if p["produto"]])
        priority = (
            (days_without or 0) * 1.4
            + (entry["total"] / 10000)
            + (ticket / 1500)
            + ((90 / avg_frequency) if avg_frequency and avg_frequency > 0 else 0)
            + status_rank(status) * 20
        )
        row = {
            **cliente,
            "primeira_compra": first.isoformat() if first else None,
            "ultima_compra": last.isoformat() if last else None,
            "dias_sem_comprar": days_without,
            "status": status,
            "status_cor": status_color(status),
            "total_comprado": entry["total"],
            "pedidos": order_count,
            "ticket_medio": ticket,
            "frequencia_media": avg_frequency,
            "produtos_recorrentes": product_names,
            "prioridade": priority,
        }
        if only_status and row["status"] != only_status:
            continue
        result.append(row)

    result = sorted(result, key=lambda x: x["prioridade"], reverse=True)
    if limit:
        return result[:limit]
    return result


def filters_from_args(**kwargs):
    return {key: value for key, value in kwargs.items() if value not in (None, "")}


def dashboard(filters):
    rows = item_rows(filters)
    # reutiliza os rows já carregados para não chamar item_rows duas vezes
    metrics = client_metrics(filters, _rows=rows)
    total = sum(num(r["item"].get("total_mercadoria")) for r in rows)
    clientes = {r["cliente"].get("id") for r in rows if r["cliente"].get("id")}
    pedidos = {r["pedido"].get("id") for r in rows if r["pedido"].get("id")}
    notas = {r["nota"].get("id") for r in rows if r["nota"].get("id")}

    by_product = defaultdict(lambda: {"quantidade": 0.0, "total": 0.0, "produto": None})
    by_client = defaultdict(lambda: {"total": 0.0, "cliente": None})
    by_month = defaultdict(float)
    for r in rows:
        product_id = r["produto"].get("id")
        client_id = r["cliente"].get("id")
        by_product[product_id]["produto"] = r["produto"]
        by_product[product_id]["quantidade"] += num(r["item"].get("quantidade"))
        by_product[product_id]["total"] += num(r["item"].get("total_mercadoria"))
        by_client[client_id]["cliente"] = r["cliente"]
        by_client[client_id]["total"] += num(r["item"].get("total_mercadoria"))
        if r["data"]:
            by_month[r["data"][:7]] += num(r["item"].get("total_mercadoria"))

    top_products = sorted(by_product.values(), key=lambda x: x["quantidade"], reverse=True)[:8]
    top_clients = sorted(by_client.values(), key=lambda x: x["total"], reverse=True)[:8]
    status_counts = defaultdict(int)
    for client in metrics:
        status_counts[client["status"]] += 1
    ticket_medio = total / len(pedidos) if pedidos else 0
    last_update = max((r["data"] for r in rows if r["data"]), default=None)
    return {
        "summary": {
            "total_vendido": total,
            "clientes": len(clientes),
            "clientes_ativos": status_counts["Ativo"],
            "clientes_atencao": status_counts["Atenção"],
            "clientes_inativos": status_counts["Inativo"],
            "clientes_perdidos": status_counts["Perdido"],
            "ticket_medio": ticket_medio,
            "pedidos": len(pedidos),
            "notas": len(notas),
            "ultima_atualizacao": last_update,
        },
        "top_products": [
            {
                "codigo": p["produto"].get("codigo"),
                "descricao": p["produto"].get("descricao"),
                "familia": p["produto"].get("familia"),
                "quantidade": p["quantidade"],
                "total": p["total"],
            }
            for p in top_products
            if p["produto"]
        ],
        "top_clients": [
            {
                "id": c["cliente"].get("id"),
                "razao_social": c["cliente"].get("razao_social"),
                "nome_fantasia": c["cliente"].get("nome_fantasia"),
                "cidade": c["cliente"].get("cidade"),
                "estado": c["cliente"].get("estado"),
                "total": c["total"],
            }
            for c in top_clients
            if c["cliente"]
        ],
        "monthly": [{"mes": month, "total": total} for month, total in sorted(by_month.items())],
    }


def clients(q=None, filters=None, limit=50):
    return client_metrics(filters, q=q, limit=limit)


def client_detail(client_id):
    # filtra por cliente_id desde o início — não varre todos os clientes
    rows = item_rows({"cliente_id": client_id})
    results = client_metrics({"cliente_id": client_id}, _rows=rows)
    return results[0] if results else None


def client_history(client_id):
    rows = item_rows({"cliente_id": client_id})
    by_product = defaultdict(lambda: {"quantidade": 0.0, "valor": 0.0, "pedidos": set(), "ultima": None, "produto": None})
    for r in rows:
        entry = by_product[r["produto"].get("id")]
        entry["produto"] = r["produto"]
        entry["quantidade"] += num(r["item"].get("quantidade"))
        entry["valor"] += num(r["item"].get("total_mercadoria"))
        entry["pedidos"].add(r["pedido"].get("id"))
        entry["ultima"] = max(entry["ultima"] or "", r["data"] or "") or None
    result = []
    for entry in by_product.values():
        p = entry["produto"]
        result.append({
            "codigo": p.get("codigo"),
            "produto": p.get("descricao"),
            "familia": p.get("familia"),
            "quantidade_total": entry["quantidade"],
            "valor_total": entry["valor"],
            "vezes_comprou": len(entry["pedidos"]),
            "ultima_compra": entry["ultima"],
        })
    return sorted(result, key=lambda x: x["quantidade_total"], reverse=True)


def orders(filters, limit=100):
    filters = dict(filters or {})  # copia para não mutar o dict original
    status_filter = filters.pop("status", None)
    allowed_clients = None
    if status_filter:
        allowed_clients = {c["id"] for c in client_metrics(only_status=status_filter)}
    result = []
    for r in item_rows(filters):
        if allowed_clients is not None and r["cliente"].get("id") not in allowed_clients:
            continue
        result.append({
            "pedido": r["pedido"].get("numero"),
            "nota_fiscal": r["nota"].get("numero"),
            "data_faturamento": r["data"],
            "cliente": r["cliente"].get("razao_social"),
            "nome_fantasia": r["cliente"].get("nome_fantasia"),
            "cnpj_cpf": r["cliente"].get("cnpj_cpf"),
            "codigo_produto": r["produto"].get("codigo"),
            "produto": r["produto"].get("descricao"),
            "familia": r["produto"].get("familia"),
            "quantidade": num(r["item"].get("quantidade")),
            "valor_unitario": num(r["item"].get("valor_unitario")),
            "total_mercadoria": num(r["item"].get("total_mercadoria")),
            "total_nota_fiscal": num(r["nota"].get("total_nota")),
        })
    return sorted(result, key=lambda x: (x["data_faturamento"] or "", x["pedido"] or ""), reverse=True)[:limit]


def client_orders(client_id):
    return orders({"cliente_id": client_id}, limit=10000)


def products(q=None, filters=None, limit=100):
    rows = item_rows(filters)
    by_product = defaultdict(lambda: {"quantidade": 0.0, "valor": 0.0, "clientes": set(), "ultima": None, "produto": None})
    for r in rows:
        p = r["produto"]
        if q and not (match_text(p.get("descricao"), q) or match_text(p.get("codigo"), q) or match_text(p.get("familia"), q)):
            continue
        entry = by_product[p.get("id")]
        entry["produto"] = p
        entry["quantidade"] += num(r["item"].get("quantidade"))
        entry["valor"] += num(r["item"].get("total_mercadoria"))
        entry["clientes"].add(r["cliente"].get("id"))
        entry["ultima"] = max(entry["ultima"] or "", r["data"] or "") or None
    result = []
    for entry in by_product.values():
        p = entry["produto"]
        result.append({
            "id": p.get("id"),
            "codigo": p.get("codigo"),
            "descricao": p.get("descricao"),
            "familia": p.get("familia"),
            "quantidade_total": entry["quantidade"],
            "valor_total": entry["valor"],
            "clientes": len(entry["clientes"]),
            "ultima_venda": entry["ultima"],
        })
    return sorted(result, key=lambda x: x["quantidade_total"], reverse=True)[:limit]


def product_clients(product_id):
    rows = [r for r in item_rows() if int(r["produto"].get("id") or 0) == int(product_id)]
    by_client = defaultdict(lambda: {"cliente": None, "quantidade": 0.0, "valor": 0.0, "ultima": None})
    product = None
    for r in rows:
        product = r["produto"]
        entry = by_client[r["cliente"].get("id")]
        entry["cliente"] = r["cliente"]
        entry["quantidade"] += num(r["item"].get("quantidade"))
        entry["valor"] += num(r["item"].get("total_mercadoria"))
        entry["ultima"] = max(entry["ultima"] or "", r["data"] or "") or None
    clients_data = []
    for entry in by_client.values():
        c = entry["cliente"]
        clients_data.append({
            "id": c.get("id"),
            "razao_social": c.get("razao_social"),
            "nome_fantasia": c.get("nome_fantasia"),
            "cidade": c.get("cidade"),
            "estado": c.get("estado"),
            "quantidade_total": entry["quantidade"],
            "valor_total": entry["valor"],
            "ultima_compra": entry["ultima"],
        })
    return {
        "produto": product,
        "clientes": sorted(clients_data, key=lambda x: x["valor_total"], reverse=True),
    }


def meta():
    clientes, produtos, pedidos, _, _ = snapshot()
    return {
        "vendedores": sorted({p.get("vendedor") for p in pedidos.values() if p.get("vendedor")}),
        "cidades": sorted({c.get("cidade") for c in clientes.values() if c.get("cidade")}),
        "estados": sorted({c.get("estado") for c in clientes.values() if c.get("estado")}),
        "familias": sorted({p.get("familia") for p in produtos.values() if p.get("familia")}),
    }
