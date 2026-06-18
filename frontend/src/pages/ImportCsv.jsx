import React, { useState } from "react";
import { FileUp } from "lucide-react";
import { api, number } from "../utils";

export function ImportCsv({ onDone }) {
  const [file, setFile] = useState(null);
  const [clientFile, setClientFile] = useState(null);
  const [status, setStatus] = useState("");
  const [clientStatus, setClientStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [clientLoading, setClientLoading] = useState(false);

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

  async function sendClientAddresses() {
    if (!clientFile) return;
    setClientLoading(true);
    setClientStatus("");
    const form = new FormData();
    form.append("file", clientFile);
    try {
      const result = await api("/api/import/client-addresses", { method: "POST", body: form });
      setClientStatus(
        `Endereços atualizados: ${number(result.updated)} clientes. Encontrados no sistema: ${number(result.matched)}. Fornecedores ocultados: ${number(result.suppliers_marked)}. Sem endereço no CSV: ${number(result.skipped_without_address)}.`
      );
      setClientFile(null);
      onDone();
    } catch (err) {
      setClientStatus(err.message);
    } finally {
      setClientLoading(false);
    }
  }

  return (
    <div className="importGrid">
      <section className="import">
        <FileUp size={42} />
        <h2>Importar CSV de vendas</h2>
        <p>A importação substitui os dados atuais depois de validar as colunas obrigatórias.</p>
        <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <button disabled={!file || loading} onClick={send}>
          {loading ? "Importando..." : "Importar vendas"}
        </button>
        {status && <strong>{status}</strong>}
      </section>

      <section className="import">
        <FileUp size={42} />
        <h2>Atualizar endereços</h2>
        <p>Atualiza somente a coluna de endereço dos clientes já existentes, usando o CNPJ/CPF como referência.</p>
        <input type="file" accept=".csv" onChange={(e) => setClientFile(e.target.files?.[0] || null)} />
        <button disabled={!clientFile || clientLoading} onClick={sendClientAddresses}>
          {clientLoading ? "Atualizando..." : "Atualizar endereços"}
        </button>
        {clientStatus && <strong>{clientStatus}</strong>}
      </section>
    </div>
  );
}
