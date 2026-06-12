import React, { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { exportCsv, number } from "../utils";

const PAGE_SIZE = 50;

export function Table({ title, rows = [], columns, onRowClick, filename }) {
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState({ key: null, direction: "desc" });

  useEffect(() => {
    setPage(0);
  }, [rows, sort]);

  const sortedRows = sort.key
    ? [...rows].sort((a, b) => compareValues(a[sort.key], b[sort.key], sort.direction))
    : rows;
  const total = sortedRows.length;
  const pages = Math.ceil(total / PAGE_SIZE);
  const pageRows = sortedRows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function handleSort(key) {
    setSort((current) => {
      if (current.key !== key) return { key, direction: "desc" };
      return { key, direction: current.direction === "desc" ? "asc" : "desc" };
    });
  }

  return (
    <section className="panel">
      <div className="tableHeader">
        <h2>
          {title} <span className="rowCount">{number(total)}</span>
        </h2>
        {filename && (
          <button
            className="exportBtn"
            title="Exportar CSV"
            onClick={() => exportCsv(filename, rows, columns)}
          >
            <Download size={15} />
            Exportar CSV
          </button>
        )}
      </div>
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              {columns.map(([key, label]) => (
                <th key={label}>
                  <button className="sortHeader" onClick={() => handleSort(key)} title="Ordenar">
                    {label}
                    <span>{sort.key === key ? (sort.direction === "desc" ? "↓" : "↑") : "↕"}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 && (
              <tr>
                <td colSpan={columns.length}>Nenhum dado encontrado.</td>
              </tr>
            )}
            {pageRows.map((row, index) => (
              <tr
                key={row.id || `${title}-${page * PAGE_SIZE + index}`}
                onClick={() => onRowClick?.(row)}
                className={onRowClick ? "clickable" : ""}
              >
                {columns.map(([key, , format]) => (
                  <td key={key}>{format ? format(row[key], row) : (row[key] ?? "-")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="pagination">
          <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            ← Anterior
          </button>
          <span>
            Página {page + 1} de {pages}
          </span>
          <button disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>
            Próxima →
          </button>
        </div>
      )}
    </section>
  );
}

function compareValues(a, b, direction) {
  const dir = direction === "asc" ? 1 : -1;
  const aEmpty = a === null || a === undefined || a === "";
  const bEmpty = b === null || b === undefined || b === "";
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;

  const aNumber = Number(a);
  const bNumber = Number(b);
  if (!Number.isNaN(aNumber) && !Number.isNaN(bNumber)) {
    return (aNumber - bNumber) * dir;
  }

  const aTime = Date.parse(a);
  const bTime = Date.parse(b);
  if (!Number.isNaN(aTime) && !Number.isNaN(bTime)) {
    return (aTime - bTime) * dir;
  }

  return String(a).localeCompare(String(b), "pt-BR", { sensitivity: "base" }) * dir;
}
