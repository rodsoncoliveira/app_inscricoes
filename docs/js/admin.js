import {
  getSession,
  signInAdmin,
  signOutAdmin,
  onAuthChange,
  getAllEvents,
  getRegistrations,
  deleteRegistration,
  getWorkshopsVagas,
  getAllWorkshops,
  linkWorkshop,
  createWorkshopCatalog,
} from "./api.js";
import {
  escapeHtml,
  formatDateBR,
  formatDateTimeBR,
  isMinor,
  filterByName,
} from "./utils.js";

const root = document.getElementById("admin-app");
let tab = "dashboard";
let selectedEventId = null;

function renderLogin(msg = "") {
  root.innerHTML = `
    <div class="wrap admin-wrap">
      <header class="site-header"><h1>Administração</h1><p>Portal NextGen</p></header>
      <div class="card" style="max-width:420px;margin:0 auto">
        <h2>Entrar</h2>
        ${msg ? `<div class="alert alert-error">${escapeHtml(msg)}</div>` : ""}
        <form id="loginForm">
          <div class="field"><label>E-mail</label><input name="email" type="email" required></div>
          <div class="field"><label>Senha</label><input name="password" type="password" required></div>
          <button class="btn btn-primary" type="submit">Entrar</button>
        </form>
        <p style="margin-top:16px;font-size:0.85rem;color:var(--muted)">Use um usuário criado no Supabase Auth (Authentication → Users).</p>
        <p class="footer-link"><a href="index.html">← Voltar ao portal</a></p>
      </div>
    </div>`;
  root.querySelector("#loginForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await signInAdmin(fd.get("email"), fd.get("password"));
    } catch (err) {
      renderLogin(err.message);
    }
  };
}

function shell(content) {
  return `
    <div class="wrap admin-wrap">
      <header class="site-header">
        <h1>Painel administrativo</h1>
        <p>Gerencie eventos, oficinas e inscrições</p>
      </header>
      <nav class="tabs">
        <button class="tab ${tab === "dashboard" ? "active" : ""}" data-tab="dashboard">Dashboard</button>
        <button class="tab ${tab === "inscricoes" ? "active" : ""}" data-tab="inscricoes">Inscrições</button>
        <button class="tab ${tab === "oficinas" ? "active" : ""}" data-tab="oficinas">Oficinas</button>
        <button class="tab" id="logoutBtn">Sair</button>
      </nav>
      ${content}
      <p class="footer-link"><a href="index.html">← Portal público</a></p>
    </div>`;
}

async function renderDashboard(events) {
  if (!selectedEventId && events[0]) selectedEventId = events[0].id;
  const options = events.map((e) => `<option value="${e.id}" ${e.id === selectedEventId ? "selected" : ""}>${escapeHtml(e.nome)}</option>`).join("");

  root.innerHTML = shell(`
    <div class="field"><label>Evento</label><select id="eventSelect">${options}</select></div>
    <div id="dashBody">Carregando...</div>
  `);
  bindTabs();
  root.querySelector("#eventSelect").onchange = (e) => {
    selectedEventId = Number(e.target.value);
    loadDashboard();
  };
  await loadDashboard();
}

async function loadDashboard() {
  const body = root.querySelector("#dashBody");
  const [regs, workshops] = await Promise.all([
    getRegistrations(selectedEventId),
    getWorkshopsVagas(selectedEventId),
  ]);
  const total = regs.length;
  const menores = regs.filter((r) => isMinor(r.data_nascimento)).length;
  const comOficina = regs.filter((r) => r.oficina_id || r.oficina_id_2).length;
  const vagasT = workshops.reduce((s, w) => s + w.vagas_totais, 0);
  const vagasO = workshops.reduce((s, w) => s + w.vagas_ocupadas, 0);
  const pct = vagasT ? Math.round((vagasO / vagasT) * 1000) / 10 : 0;

  const igrejas = {};
  regs.forEach((r) => {
    const k = (r.igreja || "N/I").trim();
    igrejas[k] = (igrejas[k] || 0) + 1;
  });
  const topIgrejas = Object.entries(igrejas).sort((a, b) => b[1] - a[1]).slice(0, 5);

  body.innerHTML = `
    <div class="metrics">
      <div class="metric"><div class="val">${total}</div><div class="lbl">Inscritos</div></div>
      <div class="metric"><div class="val">${menores}</div><div class="lbl">Menores</div></div>
      <div class="metric"><div class="val">${comOficina}</div><div class="lbl">Com oficina</div></div>
      <div class="metric"><div class="val">${pct}%</div><div class="lbl">Ocupação</div></div>
    </div>
    <div class="card">
      <h3>Top igrejas</h3>
      ${topIgrejas.map(([n, c]) => `<p>${escapeHtml(n)} — <strong>${c}</strong></p>`).join("") || "<p style='color:var(--muted)'>Sem dados</p>"}
    </div>
    <div class="card">
      <h3>Oficinas</h3>
      ${workshops.map((w) => {
        const p = w.vagas_totais ? w.vagas_ocupadas / w.vagas_totais : 0;
        return `<p><strong>${escapeHtml(w.nome)}</strong> — ${w.vagas_ocupadas}/${w.vagas_totais}
          <div class="progress"><span style="width:${Math.round(p * 100)}%"></span></div></p>`;
      }).join("") || "<p style='color:var(--muted)'>Nenhuma oficina vinculada</p>"}
    </div>`;
}

async function renderInscricoes(events) {
  if (!selectedEventId && events[0]) selectedEventId = events[0].id;
  root.innerHTML = shell(`
    <div class="field"><label>Evento</label><select id="eventSelect">${events.map((e) => `<option value="${e.id}" ${e.id === selectedEventId ? "selected" : ""}>${escapeHtml(e.nome)}</option>`).join("")}</select></div>
    <div class="field"><label>Buscar por nome</label><input id="nameFilter" placeholder="Parte do nome"></div>
    <div id="insBody"></div>
  `);
  bindTabs();
  const reload = () => loadInscricoes(root.querySelector("#nameFilter").value);
  root.querySelector("#eventSelect").onchange = (e) => { selectedEventId = Number(e.target.value); reload(); };
  root.querySelector("#nameFilter").oninput = reload;
  await loadInscricoes("");
}

async function loadInscricoes(filter) {
  const body = root.querySelector("#insBody");
  const [rows, catalog] = await Promise.all([
    getRegistrations(selectedEventId),
    getAllWorkshops(),
  ]);
  const names = Object.fromEntries(catalog.map((w) => [w.id, w.nome]));
  const filtered = filterByName(rows, filter);
  const tableRows = filtered.map((r) => {
    const oficinas = [r.oficina_id && names[r.oficina_id], r.oficina_id_2 && names[r.oficina_id_2]].filter(Boolean).join(" / ") || "—";
    return `<tr>
      <td>${r.id}</td>
      <td>${escapeHtml(r.nome)}</td>
      <td>${formatDateBR(r.data_nascimento)}</td>
      <td>${escapeHtml(r.whatsapp)}</td>
      <td>${escapeHtml(oficinas)}</td>
      <td><button class="btn btn-secondary" data-del="${r.id}" style="width:auto;padding:6px 10px">🗑️</button></td>
    </tr>`;
  }).join("");

  body.innerHTML = `
    <div class="card table-wrap">
      <p><strong>${filtered.length}</strong> inscrição(ões)</p>
      <table>
        <thead><tr><th>ID</th><th>Nome</th><th>Nasc.</th><th>WhatsApp</th><th>Oficinas</th><th></th></tr></thead>
        <tbody>${tableRows || `<tr><td colspan="6">Nenhuma inscrição</td></tr>`}</tbody>
      </table>
    </div>`;

  body.querySelectorAll("[data-del]").forEach((btn) => {
    btn.onclick = async () => {
      if (!confirm("Excluir esta inscrição?")) return;
      await deleteRegistration(Number(btn.dataset.del));
      await loadInscricoes(filter);
    };
  });
}

async function renderOficinas(events) {
  if (!selectedEventId && events[0]) selectedEventId = events[0].id;
  const [catalog, linked] = await Promise.all([
    getAllWorkshops(),
    getWorkshopsVagas(selectedEventId),
  ]);
  const linkedIds = new Set(linked.map((w) => w.id));
  const available = catalog.filter((w) => !linkedIds.has(w.id));

  root.innerHTML = shell(`
    <div class="field"><label>Evento</label><select id="eventSelect">${events.map((e) => `<option value="${e.id}" ${e.id === selectedEventId ? "selected" : ""}>${escapeHtml(e.nome)}</option>`).join("")}</select></div>
    <div class="card">
      <h3>Vincular oficina do catálogo</h3>
      <form id="linkForm" class="${available.length ? "" : "hidden"}">
        <div class="field"><label>Oficina</label><select name="oficina_id">${available.map((w) => `<option value="${w.id}">${escapeHtml(w.nome)}</option>`).join("")}</select></div>
        <div class="field"><label>Vagas</label><input name="vagas" type="number" min="1" value="30"></div>
        <button class="btn btn-primary" type="submit">Vincular</button>
      </form>
      ${!available.length ? "<p style='color:var(--muted)'>Todas as oficinas já estão neste evento.</p>" : ""}
    </div>
    <div class="card">
      <h3>Nova oficina no catálogo</h3>
      <form id="createForm">
        <div class="field"><label>Nome</label><input name="nome" required></div>
        <div class="field"><label>Preletor</label><input name="preletor" required></div>
        <div class="field"><label>Vagas neste evento</label><input name="vagas" type="number" min="1" value="30"></div>
        <button class="btn btn-primary" type="submit">Criar e vincular</button>
      </form>
    </div>
    <div class="card">
      <h3>Oficinas deste evento (${linked.length})</h3>
      ${linked.map((w) => `<p><strong>${escapeHtml(w.nome)}</strong> — ${w.vagas_ocupadas}/${w.vagas_totais} vagas</p>`).join("") || "<p style='color:var(--muted)'>Nenhuma</p>"}
    </div>
    <div class="card">
      <h3>Catálogo (${catalog.length})</h3>
      ${catalog.map((w) => `<p>${escapeHtml(w.nome)} · ${escapeHtml(w.preletor)}</p>`).join("") || "<p style='color:var(--muted)'>Vazio</p>"}
    </div>
  `);
  bindTabs();
  root.querySelector("#eventSelect").onchange = (e) => { selectedEventId = Number(e.target.value); renderOficinas(events); };

  const linkForm = root.querySelector("#linkForm");
  if (linkForm) {
    linkForm.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      await linkWorkshop(selectedEventId, Number(fd.get("oficina_id")), Number(fd.get("vagas")));
      renderOficinas(events);
    };
  }
  root.querySelector("#createForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const w = await createWorkshopCatalog(fd.get("nome"), fd.get("preletor"));
    await linkWorkshop(selectedEventId, w.id, Number(fd.get("vagas")));
    renderOficinas(events);
  };
}

function bindTabs() {
  root.querySelectorAll(".tab[data-tab]").forEach((btn) => {
    btn.onclick = () => { tab = btn.dataset.tab; bootAdmin(); };
  });
  root.querySelector("#logoutBtn").onclick = async () => {
    await signOutAdmin();
    renderLogin();
  };
}

async function bootAdmin() {
  const events = await getAllEvents();
  if (tab === "dashboard") await renderDashboard(events);
  else if (tab === "inscricoes") await renderInscricoes(events);
  else await renderOficinas(events);
}

async function init() {
  try {
    const session = await getSession();
    if (!session) {
      renderLogin();
      onAuthChange((s) => { if (s) bootAdmin(); });
      return;
    }
    await bootAdmin();
  } catch (e) {
    root.innerHTML = `<div class="wrap"><div class="alert alert-error">${escapeHtml(e.message)}</div></div>`;
  }
}

init();
