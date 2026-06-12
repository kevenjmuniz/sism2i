import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Boxes,
  FileUp,
  LayoutDashboard,
  PackageSearch,
  ReceiptText,
  UsersRound,
} from "lucide-react";

import { GlobalFilters } from "./components/GlobalFilters";
import { Dashboard } from "./pages/Dashboard";
import { Recovery } from "./pages/Recovery";
import { Clients } from "./pages/Clients";
import { Products } from "./pages/Products";
import { Orders } from "./pages/Orders";
import { ImportCsv } from "./pages/ImportCsv";
import { useData, clearDataCache } from "./hooks";
import { qs } from "./utils";
import "./styles.css";

const blankFilters = {
  start: "",
  end: "",
  status: "",
  vendedor: "",
  cidade: "",
  estado: "",
  produto: "",
  familia: "",
};

const nav = [
  ["dashboard", LayoutDashboard, "Dashboard"],
  ["recuperar", AlertTriangle, "Clientes para Recuperar"],
  ["clientes", UsersRound, "Clientes"],
  ["produtos", Boxes, "Produtos"],
  ["pedidos", ReceiptText, "Pedidos e Notas"],
  ["importar", FileUp, "Importar CSV"],
];

function App() {
  const [page, setPage] = useState("dashboard");
  const [draftFilters, setDraftFilters] = useState(blankFilters);
  const [filters, setFilters] = useState(blankFilters);
  const [refresh, setRefresh] = useState(0);

  const meta = useData(`/api/meta`, [refresh]);
  const query = useMemo(() => qs(filters), [filters]);

  function handleImportDone() {
    clearDataCache();
    setRefresh((v) => v + 1);
  }

  function handleApply() {
    setFilters(draftFilters);
  }

  function handleClear() {
    setDraftFilters(blankFilters);
    setFilters(blankFilters);
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <PackageSearch size={28} />
          <div>
            <strong>Comercial</strong>
            <span>Pescados e frutos do mar</span>
          </div>
        </div>
        <nav>
          {nav.map(([id, Icon, label]) => (
            <button
              className={page === id ? "active" : ""}
              key={id}
              onClick={() => setPage(id)}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        <header className="topbar">
          <div>
            <h1>{nav.find(([id]) => id === page)?.[2]}</h1>
            <p>Priorize clientes, entenda frequência de compra e recupere oportunidades.</p>
          </div>
        </header>

        {page !== "importar" && (
          <GlobalFilters
            filters={draftFilters}
            setFilters={setDraftFilters}
            meta={meta.data || {}}
            onApply={handleApply}
            onClear={handleClear}
          />
        )}

        {page === "dashboard" && <Dashboard query={query} refresh={refresh} />}
        {page === "recuperar" && <Recovery query={query} refresh={refresh} />}
        {page === "clientes" && <Clients query={query} refresh={refresh} />}
        {page === "produtos" && <Products query={query} refresh={refresh} />}
        {page === "pedidos" && <Orders query={query} refresh={refresh} />}
        {page === "importar" && <ImportCsv onDone={handleImportDone} />}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
