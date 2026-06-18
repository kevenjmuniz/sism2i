CREATE OR REPLACE FUNCTION api_healthcheck()
RETURNS jsonb
LANGUAGE sql
AS $$
    SELECT jsonb_build_object('ok', true, 'database', current_database(), 'user', current_user);
$$;

CREATE OR REPLACE FUNCTION api_dashboard(
    p_start text DEFAULT NULL,
    p_end text DEFAULT NULL,
    p_cliente text DEFAULT NULL,
    p_produto text DEFAULT NULL,
    p_vendedor text DEFAULT NULL,
    p_cidade text DEFAULT NULL,
    p_estado text DEFAULT NULL,
    p_familia text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE sql
AS $$
WITH base AS (
    SELECT i.pedido_id, i.produto_id, i.quantidade, i.total_mercadoria,
           p.numero AS pedido_numero, p.data_inclusao, p.data_faturamento, p.vendedor,
           c.id AS cliente_id, c.razao_social, c.nome_fantasia, c.cnpj_cpf, c.cidade, c.estado,
           pr.codigo, pr.descricao, pr.familia,
           nf.id AS nota_id
    FROM itens_pedido i
    JOIN pedidos p ON p.id = i.pedido_id
    JOIN clientes c ON c.id = p.cliente_id
    JOIN produtos pr ON pr.id = i.produto_id
    LEFT JOIN notas_fiscais nf ON nf.id = i.nota_fiscal_id
    WHERE (p_start IS NULL OR COALESCE(p.data_faturamento, p.data_inclusao) >= p_start)
      AND (p_end IS NULL OR COALESCE(p.data_faturamento, p.data_inclusao) <= p_end)
      AND (p_cliente IS NULL OR c.razao_social ILIKE '%' || p_cliente || '%' OR c.nome_fantasia ILIKE '%' || p_cliente || '%' OR c.cnpj_cpf ILIKE '%' || p_cliente || '%')
      AND (p_produto IS NULL OR pr.descricao ILIKE '%' || p_produto || '%' OR pr.codigo ILIKE '%' || p_produto || '%')
      AND (p_vendedor IS NULL OR p.vendedor = p_vendedor)
      AND (p_cidade IS NULL OR c.cidade = p_cidade)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_familia IS NULL OR pr.familia = p_familia)
),
summary AS (
    SELECT COALESCE(SUM(total_mercadoria), 0) AS total_vendido,
           COUNT(DISTINCT cliente_id) AS clientes,
           COUNT(DISTINCT pedido_id) AS pedidos,
           COUNT(DISTINCT nota_id) AS notas
    FROM base
),
top_products AS (
    SELECT codigo, descricao, familia, SUM(quantidade) AS quantidade, SUM(total_mercadoria) AS total
    FROM base
    GROUP BY produto_id, codigo, descricao, familia
    ORDER BY quantidade DESC
    LIMIT 8
),
top_clients AS (
    SELECT cliente_id AS id, razao_social, nome_fantasia, cidade, estado, SUM(total_mercadoria) AS total
    FROM base
    GROUP BY cliente_id, razao_social, nome_fantasia, cidade, estado
    ORDER BY total DESC
    LIMIT 8
),
monthly AS (
    SELECT substring(COALESCE(data_faturamento, data_inclusao), 1, 7) AS mes,
           SUM(total_mercadoria) AS total
    FROM base
    GROUP BY mes
    ORDER BY mes
)
SELECT jsonb_build_object(
    'summary', (SELECT to_jsonb(summary) FROM summary),
    'top_products', COALESCE((SELECT jsonb_agg(to_jsonb(top_products)) FROM top_products), '[]'::jsonb),
    'top_clients', COALESCE((SELECT jsonb_agg(to_jsonb(top_clients)) FROM top_clients), '[]'::jsonb),
    'monthly', COALESCE((SELECT jsonb_agg(to_jsonb(monthly)) FROM monthly), '[]'::jsonb)
);
$$;

CREATE OR REPLACE FUNCTION api_clients(p_q text DEFAULT NULL, p_limit integer DEFAULT 50)
RETURNS jsonb
LANGUAGE sql
AS $$
WITH data AS (
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
    WHERE (p_q IS NULL OR c.razao_social ILIKE '%' || p_q || '%' OR c.nome_fantasia ILIKE '%' || p_q || '%' OR c.cnpj_cpf ILIKE '%' || p_q || '%')
    GROUP BY c.id
    ORDER BY total_comprado DESC
    LIMIT p_limit
)
SELECT COALESCE(jsonb_agg(to_jsonb(data)), '[]'::jsonb) FROM data;
$$;

CREATE OR REPLACE FUNCTION api_client_detail(p_client_id bigint)
RETURNS jsonb
LANGUAGE sql
AS $$
SELECT to_jsonb(data)
FROM (
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
    WHERE c.id = p_client_id
    GROUP BY c.id
) data;
$$;

CREATE OR REPLACE FUNCTION api_client_history(p_client_id bigint)
RETURNS jsonb
LANGUAGE sql
AS $$
WITH data AS (
    SELECT pr.codigo, pr.descricao AS produto, pr.familia,
           SUM(i.quantidade) AS quantidade_total,
           SUM(i.total_mercadoria) AS valor_total,
           COUNT(DISTINCT p.id) AS vezes_comprou,
           MAX(COALESCE(p.data_faturamento, p.data_inclusao)) AS ultima_compra
    FROM itens_pedido i
    JOIN pedidos p ON p.id = i.pedido_id
    JOIN produtos pr ON pr.id = i.produto_id
    WHERE p.cliente_id = p_client_id
    GROUP BY pr.id
    ORDER BY quantidade_total DESC
)
SELECT COALESCE(jsonb_agg(to_jsonb(data)), '[]'::jsonb) FROM data;
$$;

CREATE OR REPLACE FUNCTION api_orders(
    p_start text DEFAULT NULL,
    p_end text DEFAULT NULL,
    p_cliente text DEFAULT NULL,
    p_produto text DEFAULT NULL,
    p_vendedor text DEFAULT NULL,
    p_cidade text DEFAULT NULL,
    p_estado text DEFAULT NULL,
    p_familia text DEFAULT NULL,
    p_limit integer DEFAULT 100
)
RETURNS jsonb
LANGUAGE sql
AS $$
WITH data AS (
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
    WHERE (p_start IS NULL OR COALESCE(p.data_faturamento, p.data_inclusao) >= p_start)
      AND (p_end IS NULL OR COALESCE(p.data_faturamento, p.data_inclusao) <= p_end)
      AND (p_cliente IS NULL OR c.razao_social ILIKE '%' || p_cliente || '%' OR c.nome_fantasia ILIKE '%' || p_cliente || '%' OR c.cnpj_cpf ILIKE '%' || p_cliente || '%')
      AND (p_produto IS NULL OR pr.descricao ILIKE '%' || p_produto || '%' OR pr.codigo ILIKE '%' || p_produto || '%')
      AND (p_vendedor IS NULL OR p.vendedor = p_vendedor)
      AND (p_cidade IS NULL OR c.cidade = p_cidade)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_familia IS NULL OR pr.familia = p_familia)
    ORDER BY data_faturamento DESC, p.numero DESC
    LIMIT p_limit
)
SELECT COALESCE(jsonb_agg(to_jsonb(data)), '[]'::jsonb) FROM data;
$$;

CREATE OR REPLACE FUNCTION api_products(p_q text DEFAULT NULL, p_limit integer DEFAULT 100)
RETURNS jsonb
LANGUAGE sql
AS $$
WITH data AS (
    SELECT pr.id, pr.codigo, pr.descricao, pr.familia,
           SUM(i.quantidade) AS quantidade_total,
           SUM(i.total_mercadoria) AS valor_total,
           COUNT(DISTINCT p.cliente_id) AS clientes,
           MAX(COALESCE(p.data_faturamento, p.data_inclusao)) AS ultima_venda
    FROM produtos pr
    LEFT JOIN itens_pedido i ON i.produto_id = pr.id
    LEFT JOIN pedidos p ON p.id = i.pedido_id
    WHERE (p_q IS NULL OR pr.descricao ILIKE '%' || p_q || '%' OR pr.codigo ILIKE '%' || p_q || '%' OR pr.familia ILIKE '%' || p_q || '%')
    GROUP BY pr.id
    ORDER BY quantidade_total DESC
    LIMIT p_limit
)
SELECT COALESCE(jsonb_agg(to_jsonb(data)), '[]'::jsonb) FROM data;
$$;

CREATE OR REPLACE FUNCTION api_meta()
RETURNS jsonb
LANGUAGE sql
AS $$
SELECT jsonb_build_object(
    'vendedores', COALESCE((SELECT jsonb_agg(vendedor ORDER BY vendedor) FROM (SELECT DISTINCT vendedor FROM pedidos WHERE vendedor <> '') v), '[]'::jsonb),
    'cidades', COALESCE((SELECT jsonb_agg(cidade ORDER BY cidade) FROM (SELECT DISTINCT cidade FROM clientes WHERE cidade <> '') c), '[]'::jsonb),
    'estados', COALESCE((SELECT jsonb_agg(estado ORDER BY estado) FROM (SELECT DISTINCT estado FROM clientes WHERE estado <> '') e), '[]'::jsonb),
    'familias', COALESCE((SELECT jsonb_agg(familia ORDER BY familia) FROM (SELECT DISTINCT familia FROM produtos WHERE familia <> '') f), '[]'::jsonb)
);
$$;
