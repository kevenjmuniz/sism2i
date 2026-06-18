import React, { useState } from "react";
import { Table } from "../components/Table";
import { StatusBadge } from "../components/StatusBadge";
import { clearDataCache, useData } from "../hooks";
import { api, money, days, frequency } from "../utils";

function Empty({ text }) {
  return <section className="panel empty">{text}</section>;
}

export function Recovery({ query, refresh }) {
  const [localRefresh, setLocalRefresh] = useState(0);
  const [busyClient, setBusyClient] = useState(null);
  const { data, loading, error } = useData(`/api/recovery?${query}&limit=500`, [query, refresh, localRefresh]);

  async function hideSupplier(row) {
    if (!row?.id || busyClient) return;
    setBusyClient(row.id);
    try {
      await api(`/api/clients/${row.id}/hide-supplier`, { method: "POST" });
      clearDataCache();
      setLocalRefresh((value) => value + 1);
    } finally {
      setBusyClient(null);
    }
  }

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
        [
          "__actions",
          "Ações",
          (_, row) => (
            <button className="linkAction" disabled={busyClient === row.id} onClick={() => hideSupplier(row)}>
              {busyClient === row.id ? "Ocultando..." : "Ocultar"}
            </button>
          ),
        ],
      ]}
    />
  );
}
