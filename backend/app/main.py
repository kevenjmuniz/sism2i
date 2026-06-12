from pathlib import Path
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import get_connection, init_db
from .importer import import_csv, import_upload
from . import supabase_api
from . import supabase_store
from .supabase_importer import import_csv_supabase, import_upload_supabase

app = FastAPI(title="Histórico de Compras por Cliente")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8013",
        "http://127.0.0.1:8013",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    if not supabase_api.enabled():
        init_db()


def rows(sql, params=()):
    with get_connection() as conn:
        return [normalize_result(row) for row in conn.execute(sql, params).fetchall()]


def one(sql, params=()):
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return normalize_result(row) if row else None


def normalize_result(row):
    data = dict(row)
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = float(value)
    return data


def filter_clause(
    start: Optional[str] = None,
    end: Optional[str] = None,
    cliente: Optional[str] = None,
    produto: Optional[str] = None,
    vendedor: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    familia: Optional[str] = None,
):
    clauses = []
    params = []
    date_expr = "COALESCE(p.data_faturamento, p.data_inclusao)"
    if start:
        clauses.append(f"{date_expr} >= ?")
        params.append(start)
    if end:
        clauses.append(f"{date_expr} <= ?")
        params.append(end)
    if cliente:
        clauses.append("(c.razao_social LIKE ? OR c.nome_fantasia LIKE ? OR c.cnpj_cpf LIKE ?)")
        params.extend([f"%{cliente}%", f"%{cliente}%", f"%{cliente}%"])
    if produto:
        clauses.append("(pr.descricao LIKE ? OR pr.codigo LIKE ?)")
        params.extend([f"%{produto}%", f"%{produto}%"])
    if vendedor:
        clauses.append("p.vendedor = ?")
        params.append(vendedor)
    if cidade:
        clauses.append("c.cidade = ?")
        params.append(cidade)
    if estado:
        clauses.append("c.estado = ?")
        params.append(estado)
    if familia:
        clauses.append("pr.familia = ?")
        params.append(familia)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


def filter_payload(
    start=None,
    end=None,
    cliente=None,
    produto=None,
    vendedor=None,
    cidade=None,
    estado=None,
    familia=None,
    status=None,
):
    return {
        "p_start": start or None,
        "p_end": end or None,
        "p_cliente": cliente or None,
        "p_produto": produto or None,
        "p_vendedor": vendedor or None,
        "p_cidade": cidade or None,
        "p_estado": estado or None,
        "p_familia": familia or None,
        "p_status": status or None,
    }


@app.post("/api/import")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo CSV.")
    try:
        if supabase_api.enabled():
            result = await import_upload_supabase(file)
            supabase_store.invalidate_snapshot_cache()
            return result
        return await import_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/import/local")
def import_local(path: str):
    resolved = Path(path).resolve()
    if resolved.suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Apenas arquivos CSV são permitidos.")
    try:
        if supabase_api.enabled():
            result = import_csv_supabase(str(resolved), replace=True)
            supabase_store.invalidate_snapshot_cache()
            return result
        return import_csv(str(resolved), replace=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/dashboard")
def dashboard(
    start: Optional[str] = None,
    end: Optional[str] = None,
    cliente: Optional[str] = None,
    produto: Optional[str] = None,
    vendedor: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    familia: Optional[str] = None,
):
    if supabase_api.enabled():
        return supabase_store.dashboard({"start": start, "end": end, "cliente": cliente, "produto": produto, "vendedor": vendedor, "cidade": cidade, "estado": estado, "familia": familia})

    where, params = filter_clause(start, end, cliente, produto, vendedor, cidade, estado, familia)
    base = f"""
        FROM itens_pedido i
        JOIN pedidos p ON p.id = i.pedido_id
        JOIN clientes c ON c.id = p.cliente_id
        JOIN produtos pr ON pr.id = i.produto_id
        LEFT JOIN notas_fiscais nf ON nf.id = i.nota_fiscal_id
        {where}
    """
    summary = one(
        f"""
        SELECT
            COALESCE(SUM(i.total_mercadoria), 0) AS total_vendido,
            COUNT(DISTINCT c.id) AS clientes,
            COUNT(DISTINCT p.id) AS pedidos,
            COUNT(DISTINCT nf.id) AS notas
        {base}
        """,
        params,
    )
    top_products = rows(
        f"""
        SELECT pr.codigo, pr.descricao, pr.familia, SUM(i.quantidade) AS quantidade,
               SUM(i.total_mercadoria) AS total
        {base}
        GROUP BY pr.id
        ORDER BY quantidade DESC
        LIMIT 8
        """,
        params,
    )
    top_clients = rows(
        f"""
        SELECT c.id, c.razao_social, c.nome_fantasia, c.cidade, c.estado,
               SUM(i.total_mercadoria) AS total
        {base}
        GROUP BY c.id
        ORDER BY total DESC
        LIMIT 8
        """,
        params,
    )
    monthly = rows(
        f"""
        SELECT substr(COALESCE(p.data_faturamento, p.data_inclusao), 1, 7) AS mes,
               SUM(i.total_mercadoria) AS total
        {base}
        GROUP BY mes
        ORDER BY mes
        """,
        params,
    )
    return {
        "summary": summary,
        "top_products": top_products,
        "top_clients": top_clients,
        "monthly": monthly,
    }


@app.get("/api/recovery")
def recovery(
    start: Optional[str] = None,
    end: Optional[str] = None,
    cliente: Optional[str] = None,
    produto: Optional[str] = None,
    vendedor: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    familia: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    if supabase_api.enabled():
        filters = {"start": start, "end": end, "cliente": cliente, "produto": produto, "vendedor": vendedor, "cidade": cidade, "estado": estado, "familia": familia}
        rows = supabase_store.client_metrics(filters, only_status=status)
        return rows[:limit]
    return []


@app.get("/api/clients")
def clients(
    q: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    cliente: Optional[str] = None,
    produto: Optional[str] = None,
    vendedor: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    familia: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    if supabase_api.enabled():
        filters = {
            "start": start,
            "end": end,
            "cliente": cliente or q,
            "produto": produto,
            "vendedor": vendedor,
            "cidade": cidade,
            "estado": estado,
            "familia": familia,
        }
        rows = supabase_store.clients(q=q, filters=filters, limit=None)
        if status:
            rows = [row for row in rows if row["status"] == status]
        return rows[:limit]

    params = []
    where = ""
    clauses = []
    if q or cliente:
        term = cliente or q
        clauses.append("(c.razao_social LIKE ? OR c.nome_fantasia LIKE ? OR c.cnpj_cpf LIKE ?)")
        params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
    if cidade:
        clauses.append("c.cidade = ?")
        params.append(cidade)
    if estado:
        clauses.append("c.estado = ?")
        params.append(estado)
    if vendedor:
        clauses.append("c.vendedor = ?")
        params.append(vendedor)
    if clauses:
        where = "WHERE " + " AND ".join(clauses)
    params.append(limit)
    return rows(
        f"""
        SELECT c.id, c.razao_social, c.nome_fantasia, c.cnpj_cpf, c.cidade, c.estado, c.vendedor,
               COALESCE(SUM(i.total_mercadoria), 0) AS total_comprado,
               COUNT(DISTINCT p.id) AS pedidos,
               MAX(COALESCE(p.data_faturamento, p.data_inclusao)) AS ultima_compra,
               CASE WHEN COUNT(DISTINCT p.id) = 0 THEN 0
                    ELSE COALESCE(SUM(i.total_mercadoria), 0) / COUNT(DISTINCT p.id)
               END AS ticket_medio
        FROM clientes c
        LEFT JOIN pedidos p ON p.cliente_id = c.id
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        {where}
        GROUP BY c.id
        ORDER BY total_comprado DESC
        LIMIT ?
        """,
        params,
    )


@app.get("/api/clients/{client_id}")
def client_detail(client_id: int):
    if supabase_api.enabled():
        data = supabase_store.client_detail(client_id)
        if not data:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")
        return data

    data = one(
        """
        SELECT c.id, c.razao_social, c.nome_fantasia, c.cnpj_cpf, c.cidade, c.estado, c.vendedor,
               COALESCE(SUM(i.total_mercadoria), 0) AS total_comprado,
               COUNT(DISTINCT p.id) AS pedidos,
               MAX(COALESCE(p.data_faturamento, p.data_inclusao)) AS ultima_compra,
               CASE WHEN COUNT(DISTINCT p.id) = 0 THEN 0
                    ELSE COALESCE(SUM(i.total_mercadoria), 0) / COUNT(DISTINCT p.id)
               END AS ticket_medio
        FROM clientes c
        LEFT JOIN pedidos p ON p.cliente_id = c.id
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        WHERE c.id = ?
        GROUP BY c.id
        """,
        (client_id,),
    )
    if not data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return data


@app.get("/api/clients/{client_id}/history")
def client_history(client_id: int):
    if supabase_api.enabled():
        return supabase_store.client_history(client_id)

    return rows(
        """
        SELECT pr.codigo, pr.descricao AS produto, pr.familia,
               SUM(i.quantidade) AS quantidade_total,
               SUM(i.total_mercadoria) AS valor_total,
               COUNT(DISTINCT p.id) AS vezes_comprou,
               MAX(COALESCE(p.data_faturamento, p.data_inclusao)) AS ultima_compra
        FROM itens_pedido i
        JOIN pedidos p ON p.id = i.pedido_id
        JOIN produtos pr ON pr.id = i.produto_id
        WHERE p.cliente_id = ?
        GROUP BY pr.id
        ORDER BY quantidade_total DESC
        """,
        (client_id,),
    )


@app.get("/api/clients/{client_id}/orders")
def client_orders(client_id: int):
    if supabase_api.enabled():
        return supabase_store.client_orders(client_id)
    return []


@app.get("/api/orders")
def orders(
    start: Optional[str] = None,
    end: Optional[str] = None,
    cliente: Optional[str] = None,
    produto: Optional[str] = None,
    vendedor: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    familia: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    if supabase_api.enabled():
        return supabase_store.orders({"start": start, "end": end, "cliente": cliente, "produto": produto, "vendedor": vendedor, "cidade": cidade, "estado": estado, "familia": familia, "status": status}, limit=limit)

    where, params = filter_clause(start, end, cliente, produto, vendedor, cidade, estado, familia)
    params.append(limit)
    return rows(
        f"""
        SELECT p.numero AS pedido, nf.numero AS nota_fiscal,
               COALESCE(nf.data_faturamento, p.data_faturamento, p.data_inclusao) AS data_faturamento,
               c.razao_social AS cliente, c.nome_fantasia, c.cnpj_cpf,
               pr.codigo AS codigo_produto, pr.descricao AS produto, pr.familia,
               i.quantidade, i.valor_unitario, i.total_mercadoria,
               nf.total_nota AS total_nota_fiscal
        FROM itens_pedido i
        JOIN pedidos p ON p.id = i.pedido_id
        JOIN clientes c ON c.id = p.cliente_id
        JOIN produtos pr ON pr.id = i.produto_id
        LEFT JOIN notas_fiscais nf ON nf.id = i.nota_fiscal_id
        {where}
        ORDER BY data_faturamento DESC, p.numero DESC
        LIMIT ?
        """,
        params,
    )


@app.get("/api/products")
def products(
    q: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    cliente: Optional[str] = None,
    produto: Optional[str] = None,
    vendedor: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    familia: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=300),
):
    if supabase_api.enabled():
        filters = {
            "start": start,
            "end": end,
            "cliente": cliente,
            "produto": produto or q,
            "vendedor": vendedor,
            "cidade": cidade,
            "estado": estado,
            "familia": familia,
        }
        return supabase_store.products(q=q, filters=filters, limit=limit)

    where = ""
    params = []
    if q:
        where = "WHERE pr.descricao LIKE ? OR pr.codigo LIKE ? OR pr.familia LIKE ?"
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    params.append(limit)
    return rows(
        f"""
        SELECT pr.id, pr.codigo, pr.descricao, pr.familia,
               SUM(i.quantidade) AS quantidade_total,
               SUM(i.total_mercadoria) AS valor_total,
               COUNT(DISTINCT p.cliente_id) AS clientes,
               MAX(COALESCE(p.data_faturamento, p.data_inclusao)) AS ultima_venda
        FROM produtos pr
        LEFT JOIN itens_pedido i ON i.produto_id = pr.id
        LEFT JOIN pedidos p ON p.id = i.pedido_id
        {where}
        GROUP BY pr.id
        ORDER BY quantidade_total DESC
        LIMIT ?
        """,
        params,
    )


@app.get("/api/products/{product_id}/clients")
def product_clients(product_id: int):
    if supabase_api.enabled():
        return supabase_store.product_clients(product_id)
    return {"produto": None, "clientes": []}


@app.get("/api/meta")
def meta():
    if supabase_api.enabled():
        return supabase_store.meta()

    return {
        "vendedores": [r["vendedor"] for r in rows("SELECT DISTINCT vendedor FROM pedidos WHERE vendedor <> '' ORDER BY vendedor")],
        "cidades": [r["cidade"] for r in rows("SELECT DISTINCT cidade FROM clientes WHERE cidade <> '' ORDER BY cidade")],
        "estados": [r["estado"] for r in rows("SELECT DISTINCT estado FROM clientes WHERE estado <> '' ORDER BY estado")],
        "familias": [r["familia"] for r in rows("SELECT DISTINCT familia FROM produtos WHERE familia <> '' ORDER BY familia")],
    }


static_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
