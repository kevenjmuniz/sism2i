import os
from pathlib import Path
import sqlite3
from urllib.parse import quote, urlparse

from dotenv import load_dotenv

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # SQLite local still works without psycopg installed.
    psycopg = None
    dict_row = None

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "compras.sqlite"
load_dotenv(BASE_DIR / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip() or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
SUPABASE_DIRECT_DB_MODE = os.getenv("SUPABASE_DIRECT_DB_MODE", "").strip().lower() in {"1", "true", "yes", "sim"}
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL and SUPABASE_DIRECT_DB_MODE and SUPABASE_URL and SUPABASE_DB_PASSWORD:
    project_ref = urlparse(SUPABASE_URL).hostname.split(".")[0]
    password = quote(SUPABASE_DB_PASSWORD, safe="")
    DATABASE_URL = (
        f"postgresql://postgres:{password}"
        f"@db.{project_ref}.supabase.co:5432/postgres?sslmode=require"
    )
DB_KIND = "postgres" if DATABASE_URL else "sqlite"


class DatabaseConnection:
    def __init__(self):
        self.kind = DB_KIND
        if self.kind == "postgres":
            if psycopg is None:
                raise RuntimeError("Instale psycopg[binary] para usar Supabase/PostgreSQL.")
            self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def _sql(self, sql):
        if self.kind == "postgres":
            return sql.replace("?", "%s")
        return sql

    def execute(self, sql, params=()):
        return self.conn.execute(self._sql(sql), params)

    def executescript(self, sql):
        if self.kind == "postgres":
            with self.conn.cursor() as cur:
                cur.execute(sql)
            return None
        return self.conn.executescript(sql)

    @property
    def total_changes(self):
        if self.kind == "postgres":
            return None
        return self.conn.total_changes


def get_connection():
    return DatabaseConnection()


def init_db():
    with get_connection() as conn:
        if conn.kind == "postgres":
            conn.executescript(POSTGRES_SCHEMA)
        else:
            conn.executescript(SQLITE_SCHEMA)
        ensure_schema(conn)


def ensure_schema(conn):
    if conn.kind == "postgres":
        exists = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'clientes' AND column_name = 'endereco'
            """
        ).fetchone()
        if not exists:
            conn.execute("ALTER TABLE clientes ADD COLUMN endereco TEXT")
        return

    columns = conn.execute("PRAGMA table_info(clientes)").fetchall()
    if "endereco" not in {column["name"] for column in columns}:
        conn.execute("ALTER TABLE clientes ADD COLUMN endereco TEXT")


def reset_db(conn):
    if conn.kind == "postgres":
        conn.executescript(
            """
            TRUNCATE TABLE itens_pedido, notas_fiscais, pedidos, produtos, clientes
            RESTART IDENTITY CASCADE;
            """
        )
    else:
        conn.executescript(
            """
            DELETE FROM itens_pedido;
            DELETE FROM notas_fiscais;
            DELETE FROM pedidos;
            DELETE FROM produtos;
            DELETE FROM clientes;
            DELETE FROM sqlite_sequence WHERE name IN (
                'itens_pedido', 'notas_fiscais', 'pedidos', 'produtos', 'clientes'
            );
            """
        )


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    cnpj_cpf TEXT NOT NULL UNIQUE,
    endereco TEXT,
    cidade TEXT,
    estado TEXT,
    vendedor TEXT
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    familia TEXT
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    cliente_id INTEGER NOT NULL,
    vendedor TEXT,
    data_inclusao TEXT,
    data_faturamento TEXT,
    UNIQUE(numero, cliente_id),
    FOREIGN KEY(cliente_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS notas_fiscais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    pedido_id INTEGER NOT NULL,
    data_faturamento TEXT,
    total_nota REAL NOT NULL DEFAULT 0,
    UNIQUE(numero, pedido_id),
    FOREIGN KEY(pedido_id) REFERENCES pedidos(id)
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    nota_fiscal_id INTEGER,
    item_numero TEXT,
    quantidade REAL NOT NULL DEFAULT 0,
    valor_unitario REAL NOT NULL DEFAULT 0,
    total_mercadoria REAL NOT NULL DEFAULT 0,
    UNIQUE(pedido_id, produto_id, item_numero),
    FOREIGN KEY(pedido_id) REFERENCES pedidos(id),
    FOREIGN KEY(produto_id) REFERENCES produtos(id),
    FOREIGN KEY(nota_fiscal_id) REFERENCES notas_fiscais(id)
);

CREATE INDEX IF NOT EXISTS idx_clientes_busca
ON clientes(razao_social, nome_fantasia, cnpj_cpf);

CREATE INDEX IF NOT EXISTS idx_pedidos_datas
ON pedidos(data_faturamento, data_inclusao);

CREATE INDEX IF NOT EXISTS idx_itens_pedido_produto
ON itens_pedido(pedido_id, produto_id);
"""


POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    id BIGSERIAL PRIMARY KEY,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    cnpj_cpf TEXT NOT NULL UNIQUE,
    endereco TEXT,
    cidade TEXT,
    estado TEXT,
    vendedor TEXT
);

CREATE TABLE IF NOT EXISTS produtos (
    id BIGSERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    familia TEXT
);

CREATE TABLE IF NOT EXISTS pedidos (
    id BIGSERIAL PRIMARY KEY,
    numero TEXT NOT NULL,
    cliente_id BIGINT NOT NULL REFERENCES clientes(id),
    vendedor TEXT,
    data_inclusao TEXT,
    data_faturamento TEXT,
    UNIQUE(numero, cliente_id)
);

CREATE TABLE IF NOT EXISTS notas_fiscais (
    id BIGSERIAL PRIMARY KEY,
    numero TEXT NOT NULL,
    pedido_id BIGINT NOT NULL REFERENCES pedidos(id),
    data_faturamento TEXT,
    total_nota NUMERIC(15, 2) NOT NULL DEFAULT 0,
    UNIQUE(numero, pedido_id)
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedidos(id),
    produto_id BIGINT NOT NULL REFERENCES produtos(id),
    nota_fiscal_id BIGINT REFERENCES notas_fiscais(id),
    item_numero TEXT,
    quantidade NUMERIC(15, 4) NOT NULL DEFAULT 0,
    valor_unitario NUMERIC(15, 4) NOT NULL DEFAULT 0,
    total_mercadoria NUMERIC(15, 2) NOT NULL DEFAULT 0,
    UNIQUE(pedido_id, produto_id, item_numero)
);

CREATE INDEX IF NOT EXISTS idx_clientes_busca
ON clientes(razao_social, nome_fantasia, cnpj_cpf);

CREATE INDEX IF NOT EXISTS idx_pedidos_datas
ON pedidos(data_faturamento, data_inclusao);

CREATE INDEX IF NOT EXISTS idx_itens_pedido_produto
ON itens_pedido(pedido_id, produto_id);
"""
