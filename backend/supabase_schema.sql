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
