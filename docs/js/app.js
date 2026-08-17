import {
  getActiveEvents,
  getEvent,
  getWorkshopsVagas,
  createOrUpdateRegistration,
  updateRegistrationWorkshops,
  getRegistrationSummary,
} from "./api.js";
import { escapeHtml, formatDateBR, isMinor, resolveBanner, renderSiteHeader, showError } from "./utils.js";

const root = document.getElementById("app");

const state = {
  view: "home",
  event: null,
  registrationId: null,
  action: "created",
};

function setEventTheme(event) {
  if (!event) return;
  document.documentElement.style.setProperty("--accent", event.cor_primaria || "#ff5733");
  document.documentElement.style.setProperty("--accent-2", event.cor_secundaria || "#e65100");
}

async function renderHome() {
  state.view = "home";
  let events = [];
  try {
    events = await getActiveEvents();
  } catch (e) {
    showError(root, e.message);
    return;
  }

  if (events.length === 0) {
    root.innerHTML = `
      <div class="wrap">
        ${renderSiteHeader("Portal de Inscrições", "NextGen")}
        <div class="alert alert-info">No momento não há eventos com inscrições abertas. Volte em breve!</div>
        <p class="footer-link"><a href="admin.html">Área administrativa</a></p>
      </div>`;
    return;
  }

  const cards = events.map((ev) => {
    const banner = resolveBanner(ev.banner_path);
    const bannerHtml = banner
      ? `<div class="banner-frame"><img class="banner" src="${escapeHtml(banner)}" alt="Banner do evento"></div>`
      : "";
    const dates = `${formatDateBR(ev.data_inicio)} a ${formatDateBR(ev.data_fim)}`;
    return `
      <article class="card event-card" data-id="${ev.id}">
        ${bannerHtml}
        <h2>${escapeHtml(ev.nome)}</h2>
        <p>${escapeHtml(ev.descricao || "")}</p>
        <p><strong>Data:</strong> ${dates}</p>
        <p style="color:var(--muted);font-size:0.85rem">Toque para se inscrever</p>
      </article>`;
  }).join("");

  root.innerHTML = `
    <div class="wrap">
      ${renderSiteHeader("Portal de Inscrições", "Clique no evento desejado para realizar sua inscrição")}
      ${cards}
      <p class="footer-link"><a href="admin.html">Área administrativa</a></p>
    </div>`;

  root.querySelectorAll(".event-card").forEach((el) => {
    el.addEventListener("click", () => openEvent(Number(el.dataset.id)));
  });
}

async function openEvent(id) {
  const event = await getEvent(id);
  if (!event) {
    root.innerHTML = `<div class="wrap"><div class="alert alert-error">Evento não encontrado.</div></div>`;
    return;
  }
  state.event = event;
  setEventTheme(event);
  renderRegisterForm();
}

function renderRegisterForm(errorMsg = "") {
  const ev = state.event;
  const banner = resolveBanner(ev.banner_path);
  root.innerHTML = `
    <div class="wrap">
      ${renderSiteHeader(ev.nome, `${formatDateBR(ev.data_inicio)} a ${formatDateBR(ev.data_fim)}`)}
      ${banner ? `<div class="banner-frame banner-frame-lg"><img class="banner" src="${escapeHtml(banner)}" alt="Banner do evento"></div>` : ""}
      <div class="card">
        <h2>Formulário de Inscrição</h2>
        ${errorMsg ? `<div class="alert alert-error">${escapeHtml(errorMsg)}</div>` : ""}
        <form id="regForm">
          <div class="field"><label>Nome completo *</label><input name="nome" required placeholder="Seu nome"></div>
          <div class="field"><label>Data de nascimento *</label><input name="data_nascimento" type="date" required value="2000-01-01"></div>
          <div id="guardianWarn" class="alert alert-info hidden">Menores de 18: informe o responsável.</div>
          <div class="field"><label>WhatsApp *</label><input name="whatsapp" required placeholder="(00) 90000-0000"></div>
          <div class="field"><label>Igreja / Congregação *</label><input name="igreja" required placeholder="Ex: Comunidade Hope"></div>
          <h3 style="margin:18px 0 8px;font-size:1rem">Dados do responsável</h3>
          <p style="color:var(--muted);font-size:0.85rem;margin:0 0 12px">Obrigatório apenas para menores de 18 anos.</p>
          <div class="field"><label>Nome do responsável</label><input name="responsavel_nome" placeholder="Nome completo"></div>
          <div class="field"><label>Telefone do responsável</label><input name="responsavel_telefone" placeholder="(00) 90000-0000"></div>
          <button type="submit" class="btn btn-primary">Confirmar minha inscrição</button>
        </form>
      </div>
      <button class="btn btn-secondary" id="backHome">Voltar ao início</button>
    </div>`;

  const birthInput = root.querySelector('[name="data_nascimento"]');
  const guardianWarn = root.querySelector("#guardianWarn");
  birthInput.addEventListener("change", () => {
    guardianWarn.classList.toggle("hidden", !isMinor(birthInput.value));
  });
  birthInput.dispatchEvent(new Event("change"));

  root.querySelector("#backHome").onclick = () => renderHome();
  root.querySelector("#regForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = {
      evento_id: ev.id,
      nome: fd.get("nome"),
      data_nascimento: fd.get("data_nascimento"),
      whatsapp: fd.get("whatsapp"),
      igreja: fd.get("igreja"),
      responsavel_nome: fd.get("responsavel_nome"),
      responsavel_telefone: fd.get("responsavel_telefone"),
    };
    if (isMinor(payload.data_nascimento) && (!payload.responsavel_nome || !payload.responsavel_telefone)) {
      renderRegisterForm("Menores de 18 anos devem informar nome e telefone do responsável.");
      return;
    }
    const btn = e.target.querySelector("button");
    btn.disabled = true;
    btn.textContent = "Salvando...";
    try {
      const result = await createOrUpdateRegistration(payload);
      if (!result.ok) {
        renderRegisterForm(result.error);
        return;
      }
      state.registrationId = result.id;
      state.action = result.action;
      const workshops = await getWorkshopsVagas(ev.id);
      if (workshops.length > 0) {
        renderWorkshops(workshops);
      } else {
        await renderSummary();
      }
    } catch (err) {
      renderRegisterForm(err.message || "Erro ao salvar inscrição.");
    }
  };
}

function renderWorkshops(workshops, errorMsg = "") {
  const ev = state.event;
  const options = workshops.map((w) => {
    const soldOut = w.vagas_restantes <= 0;
    const label = soldOut
      ? `🔴 ${w.nome} — ${w.preletor} (ESGOTADO)`
      : `${w.nome} — ${w.preletor} (${w.vagas_restantes} vagas)`;
    return `<option value="${w.id}" ${soldOut ? "disabled" : ""}>${escapeHtml(label)}</option>`;
  }).join("");

  root.innerHTML = `
    <div class="wrap">
      <div class="alert alert-success">🎉 Inscrição confirmada! Escolha sua oficina.</div>
      <div class="card">
        <h2>Escolha suas oficinas</h2>
        <p>Até 2 oficinas opcionais. Vagas limitadas.</p>
        ${errorMsg ? `<div class="alert alert-error">${escapeHtml(errorMsg)}</div>` : ""}
        <form id="wsForm">
          <div class="field"><label>Oficina 1</label><select name="o1"><option value="">Nenhuma</option>${options}</select></div>
          <div class="field"><label>Oficina 2</label><select name="o2"><option value="">Nenhuma</option>${options}</select></div>
          <button type="submit" class="btn btn-primary">Confirmar oficinas</button>
        </form>
      </div>
      ${whatsappBlock(ev)}
    </div>`;

  root.querySelector("#wsForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const o1 = fd.get("o1") ? Number(fd.get("o1")) : null;
    const o2 = fd.get("o2") ? Number(fd.get("o2")) : null;
    if (o1 && o2 && o1 === o2) {
      renderWorkshops(workshops, "Selecione duas oficinas diferentes.");
      return;
    }
    const btn = e.target.querySelector("button");
    btn.disabled = true;
    try {
      const result = await updateRegistrationWorkshops(state.registrationId, o1, o2);
      if (!result.ok) {
        renderWorkshops(workshops, result.error);
        return;
      }
      await renderSummary();
    } catch (err) {
      renderWorkshops(workshops, err.message);
    }
  };
}

function whatsappBlock(ev) {
  const url = (ev.whatsapp_grupo_url || "").trim();
  if (!url) return "";
  return `
    <div class="whatsapp-cta">
      <strong>📱 Entre no grupo do WhatsApp</strong>
      <p style="color:#ecfdf3;margin:8px 0 0">Avisos e novidades do congresso</p>
      <a href="${escapeHtml(url)}" target="_blank" rel="noopener">Entrar no grupo</a>
    </div>`;
}

async function renderSummary() {
  const summary = await getRegistrationSummary(state.registrationId);
  const workshops = [];
  if (summary.oficina_nome) workshops.push(`${summary.oficina_nome} (${summary.oficina_preletor || ""})`);
  if (summary.oficina_nome_2) workshops.push(`${summary.oficina_nome_2} (${summary.oficina_preletor_2 || ""})`);

  root.innerHTML = `
    <div class="wrap">
      <div class="alert alert-success">✅ Inscrição concluída! Confira o resumo abaixo.</div>
      <div class="card">
        <h2>Resumo da inscrição</h2>
        <ul class="summary-list">
          <li><span>Nome</span><span>${escapeHtml(summary.nome)}</span></li>
          <li><span>Data nasc.</span><span>${formatDateBR(summary.data_nascimento)}</span></li>
          <li><span>Evento</span><span>${escapeHtml(summary.evento_nome)}</span></li>
          <li><span>Oficinas</span><span>${workshops.length ? escapeHtml(workshops.join(" / ")) : "—"}</span></li>
        </ul>
      </div>
      ${whatsappBlock({ whatsapp_grupo_url: summary.whatsapp_grupo_url })}
      <button class="btn btn-secondary" style="margin-top:16px" id="backHome">Voltar ao início</button>
    </div>`;
  root.querySelector("#backHome").onclick = () => renderHome();
}

try {
  renderHome();
} catch (e) {
  showError(root, e.message);
}
