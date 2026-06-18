export const API = import.meta.env.VITE_API_URL || "";

export function money(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value || 0);
}

export function number(value) {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value || 0);
}

export function days(value) {
  return value == null ? "-" : `${number(value)} dias`;
}

export function frequency(value) {
  return value == null ? "Histórico curto" : `${number(value)} dias`;
}

export function qs(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (key !== "periodPreset" && value) params.set(key, value);
  });
  return params.toString();
}

export async function api(path, options) {
  const res = await fetch(`${API}${path}`, { credentials: "include", ...(options || {}) });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Não foi possível carregar os dados.");
  return res.json();
}

function exportValue(row, column) {
  const [key, , format] = column;
  const value = row[key] ?? "";
  if (!format) return value;
  const formatted = format(value, row);
  const type = typeof formatted;
  return type === "string" || type === "number" || type === "boolean" ? formatted : value;
}

function isDocumentColumn(column) {
  const [key, label] = column;
  return key === "cnpj_cpf" || String(label || "").toLowerCase().includes("cnpj");
}

function documentText(value) {
  return String(value ?? "").trim();
}

export function exportCsv(filename, rows, columns) {
  const header = columns.map(([, label]) => `"${label}"`).join(",");
  const body = rows
    .map((row) =>
      columns
        .map((column) => {
          const val = exportValue(row, column);
          const str = isDocumentColumn(column) && val ? `="${documentText(val)}"` : String(val);
          return str.includes(",") || str.includes('"') || str.includes("\n")
            ? `"${str.replace(/"/g, '""')}"`
            : str;
        })
        .join(",")
    )
    .join("\n");
  const blob = new Blob(["﻿" + header + "\n" + body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function exportExcel(filename, rows, columns) {
  const table = `
    <table>
      <thead>
        <tr>${columns.map(([, label]) => `<th>${escapeHtml(label)}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) =>
              `<tr>${columns
                .map((column) => {
                  const value = exportValue(row, column);
                  const style = isDocumentColumn(column) ? ` style="mso-number-format:'\\@';"` : "";
                  return `<td${style}>${escapeHtml(isDocumentColumn(column) ? documentText(value) : value)}</td>`;
                })
                .join("")}</tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
  const html = `<!doctype html><html><head><meta charset="UTF-8"></head><body>${table}</body></html>`;
  const blob = new Blob([html], { type: "application/vnd.ms-excel;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
