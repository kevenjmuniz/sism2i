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
  Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return params.toString();
}

export async function api(path, options) {
  const res = await fetch(`${API}${path}`, { credentials: "include", ...(options || {}) });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Não foi possível carregar os dados.");
  return res.json();
}

export function exportCsv(filename, rows, columns) {
  const header = columns.map(([, label]) => `"${label}"`).join(",");
  const body = rows
    .map((row) =>
      columns
        .map(([key]) => {
          const val = row[key] ?? "";
          const str = String(val);
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
