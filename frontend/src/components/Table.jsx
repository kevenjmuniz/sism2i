import React, { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { exportCsv, number } from "../utils";

const PAGE_SIZE = 50;

export function Table({ title, rows = [], columns, onRowClick, filename }) {
  const [page, setPage] = useState(0);

  useEffect(() => {
    setPage(0);
  }, [rows]);

  const total = rows.length;
  const pages = Math.ceil(total / PAGE_SIZE);
  const pageRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

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
              {columns.map(([, label]) => (
                <th key={label}>{label}</th>
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
