import csv
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from .db import get_connection, init_db, reset_db

REQUIRED_COLUMNS = [
    "Cliente (Razão Social)",
    "Cliente (Nome Fantasia)",
    "CNPJ/CPF",
    "Cidade",
    "Estado",
    "Vendedor",
    "Pedido de Venda",
    "Nota Fiscal",
    "Data do Faturamento",
    "Data de Inclusão",
    "Descrição do Produto",
    "Código do Produto",
    "Família de Produto",
    "Quantidade",
    "Valor Unitário",
    "Total de Mercadoria",
    "Total da Nota Fiscal",
]


def clean_key(value):
    return (value or "").lstrip("\ufeff").strip()


def normalize_row(row):
    return {clean_key(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def is_supplier_row(row):
    tags = f"{row.get('Tags', '')} {row.get('Tag - Fornecedor', '')}".lower()
    is_client = "cliente" in tags or row.get("Tag - Cliente", "").strip().lower() in {"sim", "s", "true", "1"}
    is_supplier = "fornecedor" in tags or row.get("Tag - Fornecedor", "").strip().lower() in {"sim", "s", "true", "1"}
    return is_supplier and not is_client


def parse_number(value):
    text = str(value or "").strip().replace('"', "")
    if not text:
        return 0.0
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    if text.startswith("."):
        text = "0" + text
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def validate_columns(headers):
    normalized = {clean_key(h) for h in headers or []}
    missing = [col for col in REQUIRED_COLUMNS if col not in normalized]
    if missing:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(missing))


def upsert_cliente(conn, row):
    cnpj = row["CNPJ/CPF"] or "SEM-CNPJ-" + row["Cliente (Razão Social)"]
    conn.execute(
        """
        INSERT INTO clientes (razao_social, nome_fantasia, cnpj_cpf, cidade, estado, vendedor)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(cnpj_cpf) DO UPDATE SET
            razao_social=excluded.razao_social,
            nome_fantasia=excluded.nome_fantasia,
            cidade=excluded.cidade,
            estado=excluded.estado,
            vendedor=excluded.vendedor
        """,
        (
            row["Cliente (Razão Social)"],
            row["Cliente (Nome Fantasia)"],
            cnpj,
            row["Cidade"],
            row["Estado"],
            row["Vendedor"],
        ),
    )
    return conn.execute("SELECT id FROM clientes WHERE cnpj_cpf = ?", (cnpj,)).fetchone()["id"]


def upsert_produto(conn, row):
    codigo = row["Código do Produto"] or "SEM-CODIGO-" + row["Descrição do Produto"]
    conn.execute(
        """
        INSERT INTO produtos (codigo, descricao, familia)
        VALUES (?, ?, ?)
        ON CONFLICT(codigo) DO UPDATE SET
            descricao=excluded.descricao,
            familia=excluded.familia
        """,
        (codigo, row["Descrição do Produto"], row["Família de Produto"]),
    )
    return conn.execute("SELECT id FROM produtos WHERE codigo = ?", (codigo,)).fetchone()["id"]


def import_csv(path, replace=True):
    init_db()
    path = Path(path)
    imported = skipped_invalid_date = skipped_duplicates = skipped_supplier = 0

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        validate_columns(reader.fieldnames)

        with get_connection() as conn:
            if replace:
                reset_db(conn)

            for raw in reader:
                row = normalize_row(raw)
                if is_supplier_row(row):
                    skipped_supplier += 1
                    continue
                data_faturamento = parse_date(row["Data do Faturamento"])
                data_inclusao = parse_date(row["Data de Inclusão"])
                if not data_faturamento and not data_inclusao:
                    skipped_invalid_date += 1
                    continue

                cliente_id = upsert_cliente(conn, row)
                produto_id = upsert_produto(conn, row)
                pedido_numero = row["Pedido de Venda"] or "SEM-PEDIDO"
                nota_numero = row["Nota Fiscal"] or "SEM-NOTA"

                conn.execute(
                    """
                    INSERT INTO pedidos (numero, cliente_id, vendedor, data_inclusao, data_faturamento)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(numero, cliente_id) DO UPDATE SET
                        vendedor=excluded.vendedor,
                        data_inclusao=COALESCE(excluded.data_inclusao, pedidos.data_inclusao),
                        data_faturamento=COALESCE(excluded.data_faturamento, pedidos.data_faturamento)
                    """,
                    (pedido_numero, cliente_id, row["Vendedor"], data_inclusao, data_faturamento),
                )
                pedido_id = conn.execute(
                    "SELECT id FROM pedidos WHERE numero = ? AND cliente_id = ?",
                    (pedido_numero, cliente_id),
                ).fetchone()["id"]

                total_nota = parse_number(row["Total da Nota Fiscal"])
                max_total_nota = (
                    "GREATEST(notas_fiscais.total_nota, excluded.total_nota)"
                    if conn.kind == "postgres"
                    else "MAX(notas_fiscais.total_nota, excluded.total_nota)"
                )
                conn.execute(
                    f"""
                    INSERT INTO notas_fiscais (numero, pedido_id, data_faturamento, total_nota)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(numero, pedido_id) DO UPDATE SET
                        data_faturamento=COALESCE(excluded.data_faturamento, notas_fiscais.data_faturamento),
                        total_nota={max_total_nota}
                    """,
                    (nota_numero, pedido_id, data_faturamento, total_nota),
                )
                nota_id = conn.execute(
                    "SELECT id FROM notas_fiscais WHERE numero = ? AND pedido_id = ?",
                    (nota_numero, pedido_id),
                ).fetchone()["id"]

                if conn.kind == "postgres":
                    insert_item_sql = """
                        INSERT INTO itens_pedido (
                            pedido_id, produto_id, nota_fiscal_id, item_numero,
                            quantidade, valor_unitario, total_mercadoria
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(pedido_id, produto_id, item_numero) DO NOTHING
                    """
                else:
                    insert_item_sql = """
                        INSERT OR IGNORE INTO itens_pedido (
                            pedido_id, produto_id, nota_fiscal_id, item_numero,
                            quantidade, valor_unitario, total_mercadoria
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """

                inserted = conn.execute(
                    insert_item_sql,
                    (
                        pedido_id,
                        produto_id,
                        nota_id,
                        row.get("Item") or str(produto_id),
                        parse_number(row["Quantidade"]),
                        parse_number(row["Valor Unitário"]),
                        parse_number(row["Total de Mercadoria"]),
                    ),
                )
                if inserted.rowcount == 0:
                    skipped_duplicates += 1
                else:
                    imported += 1

    return {
        "imported_items": imported,
        "skipped_invalid_date": skipped_invalid_date,
        "skipped_supplier": skipped_supplier,
        "skipped_duplicates": skipped_duplicates,
        "database": str(path),
    }


async def import_upload(upload_file):
    suffix = Path(upload_file.filename or "dados.csv").suffix or ".csv"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        content = await upload_file.read()
        temp.write(content)
        temp_path = temp.name
    return import_csv(temp_path, replace=True)
