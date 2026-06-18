import React from "react";
import { Table } from "../components/Table";
import { useData } from "../hooks";
import { money, number } from "../utils";

function Empty({ text }) {
  return <section className="panel empty">{text}</section>;
}

export function Orders({ query, refresh }) {
  const { data, loading, error } = useData(`/api/orders?${query}&limit=500`, [query, refresh]);

  if (loading) return <Empty text="Carregando pedidos e notas..." />;
  if (error) return <Empty text={error} />;

  return (
    <Table
      title="Pedidos e notas fiscais"
      rows={data || []}
      filename="pedidos.csv"
      columns={[
        ["data_faturamento", "Data"],
        ["cliente", "Cliente"],
        ["pedido", "Pedido"],
        ["nota_fiscal", "NF"],
        ["produto", "Produto"],
        ["quantidade", "Qtd", number],
        ["valor_unitario", "Unitário", money],
        ["total_mercadoria", "Mercadoria", money],
        ["total_nota_fiscal", "Total NF", money],
      ]}
    />
  );
}
