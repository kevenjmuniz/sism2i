import React, { useState } from "react";
import { FileUp } from "lucide-react";
import { api, number } from "../utils";

export function ImportCsv({ onDone }) {
  const [file, setFile] = useState(null);
  const [clientFile, setClientFile] = useState(null);
  const [status, setStatus] = useState({ text: "", ok: true });
  const [clientStatus, setClientStatus] = useState({ text: "", ok: true });
  const [loading, setLoading] = useState(false);
  const [clientLoading, setClientLoading] = useState(false);

  async function send() {
    if (!file) return;
    setLoading(true);
    setStatus({ text: "", ok: true });
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api("/api/import", { method: "POST", body: form });
      setStatus({ text: `Importação concluída: ${number(result.imported_items)} itens gravados.`, ok: true });
      setFile(null);
      onDone();
    } catch (err) {
      setStatus({ text: err.message, ok: false });
    } finally {
      setLoading(false);
    }
  }

  async function sendClientAddresses() {
    if (!clientFile) return;
    setClientLoading(true);
    setClientStatus({ text: "", ok: true });
    const form = new FormData();
    form.append("file", clientFile);
    try {
      const result = await api("/api/import/client-addresses", { method: "POST", body: form });
      setClientStatus({
        text: `Endereços atualizados: ${number(result.updated)} clientes. Encontrados no sistema: ${number(result.matched)}. Sem endereço no CSV: ${number(result.skipped_without_address)}.`,
        ok: true,
      });
      setClientFile(null);
      onDone();
    } catch (err) {
      setClientStatus({ text: err.message, ok: false });
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
        {status.text && (
          <strong className={status.ok ? "statusOk" : "statusError"} role={status.ok ? "status" : "alert"}>
            {status.text}
          </strong>
        )}
      </section>

      <section className="import">
        <FileUp size={42} />
        <h2>Atualizar endereços</h2>
        <p>Atualiza somente a coluna de endereço dos clientes já existentes, usando o CNPJ/CPF como referência.</p>
        <input type="file" accept=".csv" onChange={(e) => setClientFile(e.target.files?.[0] || null)} />
        <button disabled={!clientFile || clientLoading} onClick={sendClientAddresses}>
          {clientLoading ? "Atualizando..." : "Atualizar endereços"}
        </button>
        {clientStatus.text && (
          <strong className={clientStatus.ok ? "statusOk" : "statusError"} role={clientStatus.ok ? "status" : "alert"}>
            {clientStatus.text}
          </strong>
        )}
      </section>
    </div>
  );
}
