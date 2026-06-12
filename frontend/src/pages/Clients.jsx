import React, { useState } from "react";
import { X } from "lucide-react";
import { Table } from "../components/Table";
import { SearchBox } from "../components/SearchBox";
import { StatusBadge } from "../components/StatusBadge";
import { useData } from "../hooks";
import { money, days, number, frequency } from "../utils";

function Empty({ text }) {
  return <section className="panel empty">{text}</section>;
}

function ClientAnalysis({ clientId, onClose }) {
  const detail = useData(`/api/clients/${clientId}`, [clientId]);
  const history = useData(`/api/clients/${clientId}/history`, [clientId]);
  const orders = useData(`/api/clients/${clientId}/orders`, [clientId]);

  if (detail.loading) return <Empty text="Abrindo análise do cliente..." />;
  if (detail.error) return <Empty text={detail.error} />;

  const c = detail.data;
  return (
    <div className="stack">
      <section className="clientHeader">
        <div>
          <h2>{c.razao_social}</h2>
          <p>
            {c.nome_fantasia || "-"} · {c.cnpj_cpf} · {c.cidade}/{c.estado}
          </p>
        </div>
        <div className="clientHeaderRight">
          <StatusBadge status={c.status} />
          <button className="closeBtn" onClick={onClose} title="Fechar análise">
            <X size={18} />
          </button>
        </div>
      </section>
      <section className="cards dense">
        <article className="metric">
          <span>Primeira compra</span>
          <strong>{c.primeira_compra || "-"}</strong>
        </article>
        <article className="metric">
          <span>Última compra</span>
          <strong>{c.ultima_compra || "-"}</strong>
        </article>
        <article className="metric">
          <span>Dias sem comprar</span>
          <strong>{days(c.dias_sem_comprar)}</strong>
        </article>
        <article className="metric">
          <span>Total comprado</span>
          <strong>{money(c.total_comprado)}</strong>
        </article>
        <article className="metric">
          <span>Pedidos</span>
          <strong>{number(c.pedidos)}</strong>
        </article>
        <article className="metric">
          <span>Ticket médio</span>
          <strong>{money(c.ticket_medio)}</strong>
        </article>
        <article className="metric">
          <span>Frequência média</span>
          <strong>{frequency(c.frequencia_media)}</strong>
        </article>
        <article className="metric">
          <span>Vendedor</span>
          <strong>{c.vendedor || "-"}</strong>
        </article>
      </section>
      <Table
        title="Produtos mais comprados"
        rows={history.data || []}
        filename={`historico-${c.cnpj_cpf || clientId}.csv`}
        columns={[
          ["produto", "Produto"],
          ["familia", "Família"],
          ["quantidade_total", "Qtd total", number],
          ["valor_total", "Valor total", money],
          ["vezes_comprou", "Pedidos"],
          ["ultima_compra", "Última compra"],
        ]}
      />
      <Table
        title="Histórico de pedidos"
        rows={orders.data || []}
        filename={`pedidos-${c.cnpj_cpf || clientId}.csv`}
        columns={[
          ["data_faturamento", "Data"],
          ["pedido", "Pedido"],
          ["nota_fiscal", "NF"],
          ["produto", "Produto"],
          ["quantidade", "Qtd", number],
          ["valor_unitario", "Unitário", money],
          ["total_mercadoria", "Mercadoria", money],
          ["total_nota_fiscal", "Total NF", money],
        ]}
      />
    </div>
  );
}

export function Clients({ query, refresh }) {
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState(null);
  const list = useData(
    `/api/clients?${query}&q=${encodeURIComponent(q)}&limit=1000`,
    [query, q, refresh]
  );

  return (
    <div className="stack">
      <SearchBox
        value={draft}
        onChange={setDraft}
        onSubmit={() => setQ(draft)}
        placeholder="Buscar cliente por razão, fantasia ou CNPJ"
      />
      <Table
        title="Clientes"
        rows={list.data || []}
        filename="clientes.csv"
        onRowClick={(row) => setSelected(row.id === selected ? null : row.id)}
        columns={[
          ["razao_social", "Cliente"],
          ["nome_fantasia", "Fantasia"],
          ["cidade", "Cidade"],
          ["estado", "UF"],
          ["status", "Status", (v) => <StatusBadge status={v} />],
          ["dias_sem_comprar", "Dias sem comprar", days],
          ["total_comprado", "Total", money],
          ["ticket_medio", "Ticket", money],
        ]}
      />
      {selected && (
        <ClientAnalysis clientId={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
