import React, { useState } from "react";
import { FileUp } from "lucide-react";
import { api, number } from "../utils";

export function ImportCsv({ onDone }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  async function send() {
    if (!file) return;
    setLoading(true);
    setStatus("");
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api("/api/import", { method: "POST", body: form });
      setStatus(`Importação concluída: ${number(result.imported_items)} itens gravados.`);
      setFile(null);
      onDone();
    } catch (err) {
      setStatus(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="import">
      <FileUp size={42} />
      <h2>Importar novo CSV</h2>
      <p>
        A importação substitui os dados atuais depois de validar as colunas obrigatórias.
      </p>
      <input
        type="file"
        accept=".csv"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button disabled={!file || loading} onClick={send}>
        {loading ? "Importando..." : "Importar CSV"}
      </button>
      {status && <strong>{status}</strong>}
    </section>
  );
}
