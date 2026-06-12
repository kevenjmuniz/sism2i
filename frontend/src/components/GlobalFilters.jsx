import React from "react";

function Select({ label, value, options = [], onChange }) {
  return (
    <label>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Todos</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function GlobalFilters({ filters, setFilters, meta, onApply, onClear }) {
  const update = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  function handleKeyDown(e) {
    if (e.key === "Enter") onApply();
  }

  return (
    <section className="filters" onKeyDown={handleKeyDown}>
      <label>
        Período inicial
        <input
          type="date"
          value={filters.start}
          onChange={(e) => update("start", e.target.value)}
        />
      </label>
      <label>
        Período final
        <input
          type="date"
          value={filters.end}
          onChange={(e) => update("end", e.target.value)}
        />
      </label>
      <Select
        label="Status"
        value={filters.status}
        options={["Ativo", "Atenção", "Inativo", "Perdido"]}
        onChange={(v) => update("status", v)}
      />
      <Select
        label="Vendedor"
        value={filters.vendedor}
        options={meta.vendedores}
        onChange={(v) => update("vendedor", v)}
      />
      <Select
        label="Cidade"
        value={filters.cidade}
        options={meta.cidades}
        onChange={(v) => update("cidade", v)}
      />
      <Select
        label="Estado"
        value={filters.estado}
        options={meta.estados}
        onChange={(v) => update("estado", v)}
      />
      <label>
        Produto
        <input
          value={filters.produto}
          onChange={(e) => update("produto", e.target.value)}
          placeholder="Produto ou código"
        />
      </label>
      <Select
        label="Família"
        value={filters.familia}
        options={meta.familias}
        onChange={(v) => update("familia", v)}
      />
      <div className="filterActions">
        <button className="primaryAction" onClick={onApply}>
          Aplicar filtros
        </button>
        <button className="secondaryAction" onClick={onClear}>
          Limpar
        </button>
      </div>
    </section>
  );
}
