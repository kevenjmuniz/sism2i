import csv
from pathlib import Path
from tempfile import NamedTemporaryFile

from . import supabase_api
from .importer import is_supplier_row, normalize_row, parse_date, parse_number, row_endereco, validate_columns


def reset_tables():
    for table in ["itens_pedido", "notas_fiscais", "pedidos", "produtos", "clientes"]:
        supabase_api.table_delete_all(table)


def unique_values(items):
    return list(items.values())


def import_csv_supabase(path, replace=True):
    if not supabase_api.enabled():
        raise RuntimeError("Supabase REST nao configurado.")

    path = Path(path)
    skipped_invalid_date = 0
    skipped_supplier = 0
    valid_rows = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        validate_columns(reader.fieldnames)
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
            row["_data_faturamento"] = data_faturamento
            row["_data_inclusao"] = data_inclusao
            valid_rows.append(row)

    if replace:
        reset_tables()

    clientes = {}
    produtos = {}
    for row in valid_rows:
        cnpj = row["CNPJ/CPF"] or "SEM-CNPJ-" + row["Cliente (Razão Social)"]
        clientes[cnpj] = {
            "razao_social": row["Cliente (Razão Social)"],
            "nome_fantasia": row["Cliente (Nome Fantasia)"],
            "cnpj_cpf": cnpj,
            "endereco": row_endereco(row),
            "cidade": row["Cidade"],
            "estado": row["Estado"],
            "vendedor": row["Vendedor"],
        }
        codigo = row["Código do Produto"] or "SEM-CODIGO-" + row["Descrição do Produto"]
        produtos[codigo] = {
            "codigo": codigo,
            "descricao": row["Descrição do Produto"],
            "familia": row["Família de Produto"],
        }

    cliente_rows = supabase_api.table_upsert_many("clientes", unique_values(clientes), "cnpj_cpf")
    produto_rows = supabase_api.table_upsert_many("produtos", unique_values(produtos), "codigo")
    cliente_ids = {row["cnpj_cpf"]: row["id"] for row in cliente_rows}
    produto_ids = {row["codigo"]: row["id"] for row in produto_rows}

    pedidos = {}
    for row in valid_rows:
        cnpj = row["CNPJ/CPF"] or "SEM-CNPJ-" + row["Cliente (Razão Social)"]
        cliente_id = cliente_ids[cnpj]
        numero = row["Pedido de Venda"] or "SEM-PEDIDO"
        pedidos[(numero, cliente_id)] = {
            "numero": numero,
            "cliente_id": cliente_id,
            "vendedor": row["Vendedor"],
            "data_inclusao": row["_data_inclusao"],
            "data_faturamento": row["_data_faturamento"],
        }

    pedido_rows = supabase_api.table_upsert_many("pedidos", unique_values(pedidos), "numero,cliente_id")
    pedido_ids = {(row["numero"], row["cliente_id"]): row["id"] for row in pedido_rows}

    notas = {}
    for row in valid_rows:
        cnpj = row["CNPJ/CPF"] or "SEM-CNPJ-" + row["Cliente (Razão Social)"]
        pedido_numero = row["Pedido de Venda"] or "SEM-PEDIDO"
        pedido_id = pedido_ids[(pedido_numero, cliente_ids[cnpj])]
        nota_numero = row["Nota Fiscal"] or "SEM-NOTA"
        key = (nota_numero, pedido_id)
        total_nota = parse_number(row["Total da Nota Fiscal"])
        current = notas.get(key)
        if current and current["total_nota"] > total_nota:
            total_nota = current["total_nota"]
        notas[key] = {
            "numero": nota_numero,
            "pedido_id": pedido_id,
            "data_faturamento": row["_data_faturamento"],
            "total_nota": total_nota,
        }

    nota_rows = supabase_api.table_upsert_many("notas_fiscais", unique_values(notas), "numero,pedido_id")
    nota_ids = {(row["numero"], row["pedido_id"]): row["id"] for row in nota_rows}

    itens = {}
    for row in valid_rows:
        cnpj = row["CNPJ/CPF"] or "SEM-CNPJ-" + row["Cliente (Razão Social)"]
        pedido_id = pedido_ids[(row["Pedido de Venda"] or "SEM-PEDIDO", cliente_ids[cnpj])]
        codigo = row["Código do Produto"] or "SEM-CODIGO-" + row["Descrição do Produto"]
        produto_id = produto_ids[codigo]
        nota_id = nota_ids[(row["Nota Fiscal"] or "SEM-NOTA", pedido_id)]
        item_numero = row.get("Item") or str(produto_id)
        itens[(pedido_id, produto_id, item_numero)] = {
            "pedido_id": pedido_id,
            "produto_id": produto_id,
            "nota_fiscal_id": nota_id,
            "item_numero": item_numero,
            "quantidade": parse_number(row["Quantidade"]),
            "valor_unitario": parse_number(row["Valor Unitário"]),
            "total_mercadoria": parse_number(row["Total de Mercadoria"]),
        }

    item_rows = supabase_api.table_upsert_many(
        "itens_pedido",
        unique_values(itens),
        "pedido_id,produto_id,item_numero",
        ignore=True,
    )

    return {
        "imported_items": len(item_rows),
        "skipped_invalid_date": skipped_invalid_date,
        "skipped_supplier": skipped_supplier,
        "skipped_duplicates": len(valid_rows) - len(itens),
        "database": "supabase-rest",
    }


async def import_upload_supabase(upload_file):
    suffix = Path(upload_file.filename or "dados.csv").suffix or ".csv"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        content = await upload_file.read()
        temp.write(content)
        temp_path = temp.name
    return import_csv_supabase(temp_path, replace=True)
