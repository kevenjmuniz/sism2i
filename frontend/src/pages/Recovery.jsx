import React from "react";
import { Table } from "../components/Table";
import { StatusBadge } from "../components/StatusBadge";
import { useData } from "../hooks";
import { money, days, frequency } from "../utils";

function Empty({ text }) {
  return <section className="panel empty">{text}</section>;
}

export function Recovery({ query, refresh }) {
  const { data, loading, error } = useData(`/api/recovery?${query}&limit=500`, [query, refresh]);

  if (loading) return <Empty text="Calculando prioridade comercial..." />;
  if (error) return <Empty text={error} />;

  return (
    <Table
      title="Quem chamar primeiro"
      rows={data || []}
      filename="clientes-recuperar.csv"
      columns={[
        ["razao_social", "Cliente"],
        ["nome_fantasia", "Fantasia"],
        ["cnpj_cpf", "CNPJ/CPF"],
        ["endereco", "Endereço"],
        ["cidade", "Cidade"],
        ["estado", "UF"],
        ["vendedor", "Vendedor"],
        ["ultima_compra", "Última compra"],
        ["dias_sem_comprar", "Dias sem comprar", days],
        ["status", "Status", (v) => <StatusBadge status={v} />],
        ["total_comprado", "Total comprado", money],
        ["ticket_medio", "Ticket médio", money],
        ["frequencia_media", "Frequência média", frequency],
        ["produtos_recorrentes", "Produtos recorrentes"],
      ]}
    />
  );
}
