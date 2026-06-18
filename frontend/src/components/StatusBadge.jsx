import React from "react";

function statusClass(status) {
  return { Ativo: "green", Atenção: "yellow", Inativo: "orange", Perdido: "red" }[status] || "gray";
}

export function StatusBadge({ status }) {
  return <span className={`status ${statusClass(status)}`}>{status || "-"}</span>;
}
