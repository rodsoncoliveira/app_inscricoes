import {
  getActiveEvents,
  getEvent,
  getWorkshopsVagas,
  createOrUpdateRegistration,
  updateRegistrationWorkshops,
  getRegistrationSummary,
} from "./api.js?v=12";
import { escapeHtml, formatDateBR, isMinor, todayBR, trimOrEmpty, digitsOnly, bindNumericPhoneInput, bannerSrc, renderSiteHeader, showError } from "./utils.js?v=14";

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
    const banner = bannerSrc(ev.banner_path);
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

function renderRegisterForm(errorMsg = "", formValues = {}) {
  const ev = state.event;
  const banner = bannerSrc(ev.banner_path);
  const birthValue = formValues.data_nascimento || "2000-01-01";
  const minor = isMinor(birthValue);

  root.innerHTML = `
    <div class="wrap">
      ${renderSiteHeader(ev.nome, `${formatDateBR(ev.data_inicio)} a ${formatDateBR(ev.data_fim)}`)}
      ${banner ? `<div class="banner-frame banner-frame-lg"><img class="banner" src="${escapeHtml(banner)}" alt="Banner do evento"></div>` : ""}
      <div class="card">
        <h2>Formulário de Inscrição</h2>
        ${errorMsg ? `<div class="alert alert-error">${escapeHtml(errorMsg)}</div>` : ""}
        <form id="regForm" novalidate>
          <div class="field"><label>Nome completo *</label><input name="nome" required placeholder="Seu nome" value="${escapeHtml(formValues.nome || "")}"></div>
          <div class="field"><label>Data de nascimento *</label><input id="birthInput" name="data_nascimento" type="date" required value="${escapeHtml(birthValue)}" max="${todayBR()}"></div>

          <div id="guardianWarn" class="alert alert-info ${minor ? "" : "hidden"}">Participante menor de 18 anos: nome e telefone do responsável são obrigatórios.</div>
          <div id="guardianSection" class="guardian-section ${minor ? "guardian-required" : "hidden-guardian"}">
            <h3 style="margin:0 0 8px;font-size:1rem">Dados do responsável</h3>
            <p id="guardianCaption" style="color:var(--muted);font-size:0.85rem;margin:0 0 12px">${minor ? "Campos obrigatórios para menores de idade." : "Opcional."}</p>
            <div class="field" id="guardianNomeField">
              <label id="guardianNomeLabel">${minor ? "Nome do Responsável *" : "Nome do Responsável"}</label>
              <input name="responsavel_nome" placeholder="Nome completo" value="${escapeHtml(formValues.responsavel_nome || "")}">
            </div>
            <div class="field" id="guardianTelField">
              <label id="guardianTelLabel">${minor ? "Telefone do Responsável *" : "Telefone do Responsável"}</label>
              <input name="responsavel_telefone" type="tel" inputmode="numeric" pattern="[0-9]*" autocomplete="tel" maxlength="15" placeholder="11999998888" value="${escapeHtml(digitsOnly(formValues.responsavel_telefone || ""))}">
            </div>
          </div>

          <div class="field"><label>WhatsApp *</label><input name="whatsapp" type="tel" inputmode="numeric" pattern="[0-9]*" autocomplete="tel" maxlength="15" required placeholder="11999998888" value="${escapeHtml(digitsOnly(formValues.whatsapp || ""))}"></div>
          <div class="field"><label>Igreja / Congregação *</label><input name="igreja" required placeholder="Ex: Comunidade Hope" value="${escapeHtml(formValues.igreja || "")}"></div>
          <button type="submit" class="btn btn-primary">Confirmar minha inscrição</button>
        </form>
      </div>
      <button class="btn btn-secondary" id="backHome">Voltar ao início</button>
    </div>`;

  const form = root.querySelector("#regForm");
  const birthInput = root.querySelector("#birthInput");
  const guardianWarn = root.querySelector("#guardianWarn");
  const guardianSection = root.querySelector("#guardianSection");
  const guardianCaptionEl = root.querySelector("#guardianCaption");
  const guardianNomeLabel = root.querySelector("#guardianNomeLabel");
  const guardianTelLabel = root.querySelector("#guardianTelLabel");
  const guardianNomeInput = root.querySelector('[name="responsavel_nome"]');
  const guardianTelInput = root.querySelector('[name="responsavel_telefone"]');
  const whatsappInput = root.querySelector('[name="whatsapp"]');
  bindNumericPhoneInput(guardianTelInput);
  bindNumericPhoneInput(whatsappInput);

  function syncGuardianFields() {
    const needsGuardian = isMinor(birthInput.value);
    guardianWarn.classList.toggle("hidden", !needsGuardian);
    guardianSection.classList.toggle("hidden-guardian", !needsGuardian);
    guardianSection.classList.toggle("guardian-required", needsGuardian);
    guardianCaptionEl.textContent = needsGuardian
      ? "Campos obrigatórios para menores de idade."
      : "Opcional.";
    guardianNomeLabel.textContent = needsGuardian ? "Nome do Responsável *" : "Nome do Responsável";
    guardianTelLabel.textContent = needsGuardian ? "Telefone do Responsável *" : "Telefone do Responsável";
    guardianNomeInput.required = needsGuardian;
    guardianTelInput.required = needsGuardian;
    if (!needsGuardian) {
      guardianNomeInput.value = "";
      guardianTelInput.value = "";
      guardianNomeInput.setCustomValidity("");
      guardianTelInput.setCustomValidity("");
    }
    if (needsGuardian) {
      guardianSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  ["input", "change", "blur"].forEach((evt) => {
    birthInput.addEventListener(evt, syncGuardianFields);
  });
  syncGuardianFields();

  root.querySelector("#backHome").onclick = () => renderHome();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    syncGuardianFields();

    const fd = new FormData(form);
    const payload = {
      evento_id: ev.id,
      nome: trimOrEmpty(fd.get("nome")),
      data_nascimento: String(fd.get("data_nascimento") || "").slice(0, 10),
      whatsapp: digitsOnly(fd.get("whatsapp")),
      igreja: trimOrEmpty(fd.get("igreja")),
      responsavel_nome: trimOrEmpty(fd.get("responsavel_nome")),
      responsavel_telefone: digitsOnly(fd.get("responsavel_telefone")),
    };

    if (!payload.nome || !payload.whatsapp || !payload.igreja || !payload.data_nascimento) {
      renderRegisterForm("Por favor, preencha todos os campos obrigatórios (*).", payload);
      return;
    }

    if (isMinor(payload.data_nascimento) && (!payload.responsavel_nome || !payload.responsavel_telefone)) {
      renderRegisterForm("Menores de 18 anos devem informar nome e telefone do responsável.", payload);
      return;
    }

    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = "Salvando...";
    try {
      const result = await createOrUpdateRegistration(payload);
      if (!result?.ok) {
        renderRegisterForm(result?.error || "Não foi possível salvar a inscrição.", payload);
        return;
      }
      state.registrationId = result.id;
      state.action = result.action;
      const workshops = await getWorkshopsVagas(ev.id);
      if (workshops.length > 0) {
        renderWorkshops(workshops, "", result.action);
      } else {
        await renderSummary(result.action);
      }
    } catch (err) {
      renderRegisterForm(err.message || "Erro ao salvar inscrição.", payload);
    }
  });
}

function renderWorkshops(workshops, errorMsg = "", action = state.action) {
  const ev = state.event;
  const successMsg = action === "updated"
    ? "✅ Inscrição atualizada! Escolha ou revise suas oficinas."
    : "🎉 Inscrição confirmada! Escolha sua oficina.";
  const options = workshops.map((w) => {
    const soldOut = w.vagas_restantes <= 0;
    const label = soldOut
      ? `🔴 ${w.nome} — ${w.preletor} (ESGOTADO)`
      : `${w.nome} — ${w.preletor} (${w.vagas_restantes} vagas)`;
    return `<option value="${w.id}" ${soldOut ? "disabled" : ""}>${escapeHtml(label)}</option>`;
  }).join("");

  root.innerHTML = `
    <div class="wrap">
      <div class="alert alert-success">${successMsg}</div>
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
      const whatsappUrl = (ev.whatsapp_grupo_url || "").trim();
      if (whatsappUrl) {
        await showWhatsAppPopup(whatsappUrl);
      }
      await renderSummary();
    } catch (err) {
      renderWorkshops(workshops, err.message);
    }
  };
}

function showWhatsAppPopup(url) {
  return new Promise((resolve) => {
    let overlay = document.getElementById("whatsappModal");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "whatsappModal";
      overlay.className = "modal-overlay hidden";
      overlay.innerHTML = `
        <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="whatsappModalTitle">
          <h3 id="whatsappModalTitle">📱 Entre no grupo do WhatsApp</h3>
          <p>Avisos e novidades do congresso. Toque abaixo para participar.</p>
          <a class="btn-whatsapp" id="whatsappModalJoin" href="#" target="_blank" rel="noopener">Entrar no grupo</a>
          <button type="button" class="btn-later" id="whatsappModalLater">Agora não</button>
        </div>`;
      document.body.appendChild(overlay);
    }

    const joinBtn = overlay.querySelector("#whatsappModalJoin");
    const laterBtn = overlay.querySelector("#whatsappModalLater");
    joinBtn.href = url;

    const close = () => {
      overlay.classList.add("hidden");
      resolve();
    };

    joinBtn.onclick = () => {
      close();
    };
    laterBtn.onclick = close;
    overlay.onclick = (event) => {
      if (event.target === overlay) close();
    };

    overlay.classList.remove("hidden");
  });
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

async function renderSummary(action = state.action) {
  const summary = await getRegistrationSummary(state.registrationId);
  const workshops = [];
  if (summary.oficina_nome) workshops.push(`${summary.oficina_nome} (${summary.oficina_preletor || ""})`);
  if (summary.oficina_nome_2) workshops.push(`${summary.oficina_nome_2} (${summary.oficina_preletor_2 || ""})`);
  const successMsg = action === "updated"
    ? "✅ Inscrição atualizada! Confira o resumo abaixo."
    : "✅ Inscrição concluída! Confira o resumo abaixo.";

  root.innerHTML = `
    <div class="wrap">
      <div class="alert alert-success">${successMsg}</div>
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
