import React from "react";
import { Chart } from "../components/Chart";
import { Table } from "../components/Table";
import { useData } from "../hooks";
import { money, number } from "../utils";

function Empty({ text }) {
  return <section className="panel empty">{text}</section>;
}

export function Dashboard({ query, refresh }) {
  const { data, loading, error } = useData(`/api/dashboard?${query}`, [query, refresh]);

  if (loading) return <Empty text="Carregando dashboard..." />;
  if (error) return <Empty text={error} />;

  const s = data.summary;
  const cards = [
    ["Total de clientes", number(s.clientes)],
    ["Ativos", number(s.clientes_ativos ?? 0), "green"],
    ["Em atenção", number(s.clientes_atencao ?? 0), "yellow"],
    ["Inativos", number(s.clientes_inativos ?? 0), "orange"],
    ["Perdidos", number(s.clientes_perdidos ?? 0), "red"],
    ["Faturamento total", money(s.total_vendido)],
    ["Ticket médio", money(s.ticket_medio)],
    ["Total de pedidos", number(s.pedidos)],
    ["Última atualização", s.ultima_atualizacao || "-"],
  ];

  return (
    <div className="stack">
      <section className="cards dense">
        {cards.map(([label, value, color]) => (
          <article className={`metric ${color || ""}`} key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>
      <section className="grid2">
        <Chart title="Faturamento por mês" data={data.monthly} />
        <Table
          title="Clientes que mais compraram"
          rows={data.top_clients}
          filename="top-clientes.csv"
          columns={[
            ["razao_social", "Cliente"],
            ["cidade", "Cidade"],
            ["estado", "UF"],
            ["total", "Total", money],
          ]}
        />
      </section>
    </div>
  );
}
