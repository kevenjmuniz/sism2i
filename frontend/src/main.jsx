import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Boxes,
  FileUp,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
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
import { api, qs } from "./utils";
import logoM2i from "./assets/m2i-logo.png";
import "./styles.css";

const blankFilters = {
  periodPreset: "",
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
  const [auth, setAuth] = useState({ checking: true, authenticated: false, error: "" });
  const [page, setPage] = useState("dashboard");
  const [draftFilters, setDraftFilters] = useState(blankFilters);
  const [filters, setFilters] = useState(blankFilters);
  const [refresh, setRefresh] = useState(0);
  const [sidebarHidden, setSidebarHidden] = useState(false);

  React.useEffect(() => {
    api("/api/auth/me")
      .then((data) => setAuth({ checking: false, authenticated: data.authenticated, error: "" }))
      .catch(() => setAuth({ checking: false, authenticated: false, error: "" }));
  }, []);

  const meta = useData(auth.authenticated ? `/api/meta` : "", [refresh, auth.authenticated]);
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

  if (auth.checking) {
    return <div className="loginPage"><section className="loginBox"><strong>Carregando...</strong></section></div>;
  }

  if (!auth.authenticated) {
    return <Login onLogin={() => setAuth({ checking: false, authenticated: true, error: "" })} />;
  }

  return (
    <div className={sidebarHidden ? "app sidebarHidden" : "app"}>
      {!sidebarHidden && (
        <aside className="sidebar">
          <div className="sidebarHeader">
            <div className="brand">
              <img className="brandLogo" src={logoM2i} alt="M2i Comercial" />
              <div>
                <strong>M2i Comercial</strong>
                <span>Pescados e frutos do mar</span>
              </div>
            </div>
            <button className="iconAction dark" title="Esconder menu" onClick={() => setSidebarHidden(true)}>
              <PanelLeftClose size={18} />
            </button>
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
      )}
      <main className="content">
        <header className="topbar">
          <div className="topbarTitle">
            {sidebarHidden && (
              <button className="iconAction" title="Mostrar menu" onClick={() => setSidebarHidden(false)}>
                <PanelLeftOpen size={18} />
              </button>
            )}
            <div>
              <h1>{nav.find(([id]) => id === page)?.[2]}</h1>
              <p>Priorize clientes, entenda frequência de compra e recupere oportunidades.</p>
            </div>
          </div>
          <button className="secondaryAction" onClick={async () => { await api("/api/auth/logout", { method: "POST" }); clearDataCache(); setAuth({ checking: false, authenticated: false, error: "" }); }}>Sair</button>
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

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event?.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      clearDataCache();
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="loginPage">
      <form className="loginBox" onSubmit={submit}>
        <div className="brand loginBrand">
          <img className="brandLogo" src={logoM2i} alt="M2i Comercial" />
          <div>
            <strong>M2i Comercial</strong>
            <span>Acesso ao sistema</span>
          </div>
        </div>
        <label>Usuário<input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus /></label>
        <label>Senha<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        <button className="primaryAction" disabled={loading}>{loading ? "Entrando..." : "Entrar"}</button>
        {error && <p className="loginError">{error}</p>}
      </form>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
