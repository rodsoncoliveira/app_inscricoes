export function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

export function formatDateBR(iso) {
  if (!iso) return "";
  const [y, m, d] = String(iso).slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function formatDateTimeBR(iso) {
  if (!iso) return "";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return formatDateBR(iso);
  return dt.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export function todayBR() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/Sao_Paulo" });
}

export function isMinor(isoDate) {
  if (!isoDate) return false;
  const datePart = String(isoDate).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(datePart)) return false;

  const [y, m, d] = datePart.split("-").map(Number);
  const [ty, tm, td] = todayBR().split("-").map(Number);

  let age = ty - y;
  if (tm < m || (tm === m && td < d)) age -= 1;
  return age < 18;
}

export function trimOrEmpty(value) {
  return String(value ?? "").trim();
}

export function normalizeName(name) {
  return (name || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function filterByName(rows, search) {
  const needle = normalizeName(search);
  if (!needle) return rows;
  return rows.filter((r) => normalizeName(r.nome).includes(needle));
}

export function resolveBanner(path) {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const clean = path.replace(/^\.?\//, "");
  if (clean.startsWith("docs/")) return clean.slice(5);
  return clean;
}

export function renderSiteHeader(title, subtitle = "") {
  return `
    <div class="header-container">
      <img class="logo-left" src="image/LogoNextGen_nobg.png" alt="NextGen">
      <div class="header-title-wrapper">
        <h1 class="header-title">${escapeHtml(title)}</h1>
        ${subtitle ? `<p class="header-subtitle">${escapeHtml(subtitle)}</p>` : ""}
      </div>
      <img class="logo-right" src="image/HOPE_nobg.png" alt="Hope">
    </div>`;
}

export function showError(root, msg) {
  root.innerHTML = `<div class="wrap"><div class="alert alert-error">${escapeHtml(msg)}</div>
    <p class="footer-link">Configure <code>docs/js/config.js</code> (veja config.example.js e DEPLOY.md).</p></div>`;
}
