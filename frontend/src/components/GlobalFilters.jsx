import React from "react";

const periodOptions = [
  ["30", "Ultimos 30 dias"],
  ["60", "Ultimos 60 dias"],
  ["90", "Ultimos 90 dias"],
  ["180", "Ultimos 180 dias"],
];

const STATUS_OPTIONS = ["Ativo", "Atenção", "Inativo", "Perdido"];

const FILTER_KEYS = [
  "start",
  "end",
  "status",
  "vendedor",
  "cidade",
  "estado",
  "cliente",
  "produto",
  "familia",
  "dias_min",
  "dias_max",
  "valor_min",
];

function formatDate(date) {
  return date.toISOString().slice(0, 10);
}

function countActive(filters) {
  return FILTER_KEYS.reduce((count, key) => count + (filters[key] ? 1 : 0), 0);
}

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

function StatusMultiSelect({ value, onChange }) {
  const selected = value ? value.split(",").filter(Boolean) : [];
  function toggle(opt) {
    const next = selected.includes(opt) ? selected.filter((s) => s !== opt) : [...selected, opt];
    onChange(next.join(","));
  }
  return (
    <div className="statusMulti">
      <span className="statusMultiLabel">Status</span>
      <div className="statusMultiOptions">
        {STATUS_OPTIONS.map((opt) => (
          <label key={opt} className="statusMultiOption">
            <input type="checkbox" checked={selected.includes(opt)} onChange={() => toggle(opt)} />
            {opt}
          </label>
        ))}
      </div>
    </div>
  );
}

export function GlobalFilters({ filters, setFilters, appliedFilters, meta, onApply, onClear }) {
  const update = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  function updateDate(key, value) {
    setFilters((prev) => ({ ...prev, periodPreset: "", [key]: value }));
  }

  function updatePeriodPreset(value) {
    if (!value) {
      update("periodPreset", "");
      return;
    }
    const days = Number(value);
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days);
    setFilters((prev) => ({
      ...prev,
      periodPreset: value,
      start: formatDate(start),
      end: formatDate(end),
    }));
  }

  function applyRecoveryPreset() {
    setFilters((prev) => ({ ...prev, status: "Atenção,Inativo,Perdido" }));
    onApply({ ...filters, status: "Atenção,Inativo,Perdido" });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") onApply();
  }

  const dateError = filters.start && filters.end && filters.start > filters.end;
  const dirty = FILTER_KEYS.some((key) => (filters[key] || "") !== (appliedFilters?.[key] || ""));
  const activeCount = appliedFilters ? countActive(appliedFilters) : 0;

  return (
    <section className="filters" onKeyDown={handleKeyDown}>
      <div className="filtersTop">
        <div className="filtersInfo">
          {activeCount > 0 && <span className="filterCount">{activeCount} filtro(s) aplicado(s)</span>}
          {dirty && <span className="filterDirty">Alterações não aplicadas</span>}
        </div>
        <button type="button" className="presetBtn" onClick={applyRecoveryPreset}>
          Recuperação prioritária
        </button>
      </div>
      <div className="filtersGrid">
        <label>
          Atalho de periodo
          <select value={filters.periodPreset} onChange={(e) => updatePeriodPreset(e.target.value)}>
            <option value="">Personalizado</option>
            {periodOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Período inicial
          <input
            type="date"
            value={filters.start}
            onChange={(e) => updateDate("start", e.target.value)}
            aria-invalid={dateError ? "true" : "false"}
          />
        </label>
        <label>
          Período final
          <input
            type="date"
            value={filters.end}
            onChange={(e) => updateDate("end", e.target.value)}
            aria-invalid={dateError ? "true" : "false"}
          />
        </label>
        <label>
          Cliente
          <input
            value={filters.cliente || ""}
            onChange={(e) => update("cliente", e.target.value)}
            placeholder="Razão social, fantasia ou CNPJ"
          />
        </label>
        <StatusMultiSelect value={filters.status} onChange={(v) => update("status", v)} />
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
        <label>
          Dias sem comprar (mín.)
          <input
            type="number"
            min="0"
            value={filters.dias_min || ""}
            onChange={(e) => update("dias_min", e.target.value)}
            placeholder="Ex: 60"
          />
        </label>
        <label>
          Dias sem comprar (máx.)
          <input
            type="number"
            min="0"
            value={filters.dias_max || ""}
            onChange={(e) => update("dias_max", e.target.value)}
            placeholder="Ex: 120"
          />
        </label>
        <label>
          Valor total comprado (mín.)
          <input
            type="number"
            min="0"
            step="100"
            value={filters.valor_min || ""}
            onChange={(e) => update("valor_min", e.target.value)}
            placeholder="Ex: 10000"
          />
        </label>
      </div>
      {dateError && (
        <p className="filterError" role="alert">
          O período inicial não pode ser depois do período final.
        </p>
      )}
      <div className="filterActions">
        <button className="primaryAction" onClick={() => onApply()}>
          Aplicar filtros
        </button>
        <button className="secondaryAction" onClick={onClear}>
          Limpar
        </button>
      </div>
    </section>
  );
}
