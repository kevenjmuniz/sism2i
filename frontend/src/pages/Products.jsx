import React, { useState } from "react";
import { Table } from "../components/Table";
import { SearchBox } from "../components/SearchBox";
import { Empty } from "../components/Empty";
import { useData } from "../hooks";
import { money, number } from "../utils";

export function Products({ query, refresh }) {
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState(null);
  const { data, loading, error } = useData(
    `/api/products?${query}&q=${encodeURIComponent(q)}&limit=300`,
    [query, q, refresh]
  );
  const detail = useData(selected ? `/api/products/${selected}/clients` : "", [selected]);

  return (
    <div className="stack">
      <SearchBox
        value={draft}
        onChange={setDraft}
        onSubmit={() => setQ(draft)}
        placeholder="Buscar produto, código ou família"
      />
      {loading ? (
        <Empty text="Carregando produtos..." />
      ) : error ? (
        <Empty text={error} tone="error" />
      ) : (
        <Table
          title="Produtos"
          rows={data || []}
          filename="produtos.csv"
          onRowClick={(row) => setSelected(row.id === selected ? null : row.id)}
          columns={[
            ["codigo", "Código"],
            ["descricao", "Produto"],
            ["familia", "Família"],
            ["quantidade_total", "Qtd vendida", number],
            ["valor_total", "Faturamento", money],
            ["clientes", "Clientes"],
            ["ultima_venda", "Última venda"],
          ]}
        />
      )}
      {selected && detail.data?.clientes && (
        <Table
          title="Clientes que compraram o produto"
          rows={detail.data.clientes}
          filename="clientes-do-produto.csv"
          columns={[
            ["razao_social", "Cliente"],
            ["nome_fantasia", "Fantasia"],
            ["cidade", "Cidade"],
            ["estado", "UF"],
            ["quantidade_total", "Qtd", number],
            ["valor_total", "Total", money],
            ["ultima_compra", "Última compra"],
          ]}
        />
      )}
    </div>
  );
}
