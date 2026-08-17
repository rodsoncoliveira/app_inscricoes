let client = null;

export function getSupabase() {
  if (client) return client;
  const cfg = window.APP_CONFIG;
  if (!cfg?.SUPABASE_URL || !cfg?.SUPABASE_ANON_KEY) {
    throw new Error("Configure docs/js/config.js a partir de config.example.js");
  }
  if (cfg.SUPABASE_URL.includes("SEU_PROJECT")) {
    throw new Error("Preencha SUPABASE_URL e SUPABASE_ANON_KEY em config.js");
  }
  if (!window.supabase?.createClient) {
    throw new Error("Biblioteca Supabase não carregou. Verifique sua conexão.");
  }
  client = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
  return client;
}

function todayBR() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/Sao_Paulo" });
}

export async function getActiveEvents() {
  const sb = getSupabase();
  const today = todayBR();
  const { data, error } = await sb
    .from("eventos")
    .select("*")
    .eq("ativo", 1)
    .lte("inicio_inscricoes", today)
    .gte("fim_inscricoes", today)
    .order("data_inicio", { ascending: true });
  if (error) throw error;
  return data || [];
}

export async function getEvent(id) {
  const sb = getSupabase();
  const { data, error } = await sb.from("eventos").select("*").eq("id", id).maybeSingle();
  if (error) throw error;
  return data;
}

export async function getAllEvents() {
  const sb = getSupabase();
  const { data, error } = await sb.from("eventos").select("*").order("data_inicio", { ascending: false });
  if (error) throw error;
  return data || [];
}

export async function getWorkshopsVagas(eventoId) {
  const sb = getSupabase();
  const { data, error } = await sb.rpc("get_oficinas_vagas", { p_evento_id: eventoId });
  if (error) throw error;
  return data || [];
}

export async function createOrUpdateRegistration(payload) {
  const sb = getSupabase();
  const { data, error } = await sb.rpc("create_or_update_inscricao", {
    p_evento_id: payload.evento_id,
    p_nome: payload.nome,
    p_data_nascimento: payload.data_nascimento,
    p_whatsapp: payload.whatsapp,
    p_igreja: payload.igreja,
    p_responsavel_nome: payload.responsavel_nome || null,
    p_responsavel_telefone: payload.responsavel_telefone || null,
  });
  if (error) throw error;
  if (typeof data === "string") {
    try {
      return JSON.parse(data);
    } catch {
      return { ok: false, error: "Resposta inválida do servidor." };
    }
  }
  return data;
}

export async function updateRegistrationWorkshops(inscricaoId, oficinaId, oficinaId2) {
  const sb = getSupabase();
  const { data, error } = await sb.rpc("update_inscricao_oficinas", {
    p_inscricao_id: inscricaoId,
    p_oficina_id: oficinaId,
    p_oficina_id_2: oficinaId2,
  });
  if (error) throw error;
  return data;
}

export async function getRegistrationSummary(inscricaoId) {
  const sb = getSupabase();
  const { data, error } = await sb.rpc("get_inscricao_resumo", { p_inscricao_id: inscricaoId });
  if (error) throw error;
  return data;
}

export async function getRegistrations(eventoId) {
  const sb = getSupabase();
  const { data, error } = await sb
    .from("inscricoes")
    .select("id, nome, data_nascimento, whatsapp, igreja, responsavel_nome, responsavel_telefone, data_inscricao, oficina_id, oficina_id_2")
    .eq("evento_id", eventoId)
    .order("data_inscricao", { ascending: false });
  if (error) throw error;
  return data || [];
}

export async function deleteRegistration(id) {
  const sb = getSupabase();
  const { error } = await sb.from("inscricoes").delete().eq("id", id);
  if (error) throw error;
}

export async function signInAdmin(email, password) {
  const sb = getSupabase();
  const { data, error } = await sb.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

export async function signOutAdmin() {
  const sb = getSupabase();
  await sb.auth.signOut();
}

export async function getSession() {
  const sb = getSupabase();
  const { data } = await sb.auth.getSession();
  return data.session;
}

export function onAuthChange(cb) {
  const sb = getSupabase();
  return sb.auth.onAuthStateChange((_event, session) => cb(session));
}

export async function getAllWorkshops() {
  const sb = getSupabase();
  const { data, error } = await sb.from("oficinas").select("*").order("nome");
  if (error) throw error;
  return data || [];
}

export async function linkWorkshop(eventoId, oficinaId, vagas) {
  const sb = getSupabase();
  const { error } = await sb.from("evento_oficinas").upsert({
    evento_id: eventoId,
    oficina_id: oficinaId,
    vagas,
  });
  if (error) throw error;
}

export async function createWorkshopCatalog(nome, preletor) {
  const sb = getSupabase();
  const { data, error } = await sb.from("oficinas").insert({ nome, preletor }).select("id").single();
  if (error) throw error;
  return data;
}

function eventPayloadFromForm(fd) {
  return {
    nome: String(fd.get("nome") || "").trim(),
    descricao: String(fd.get("descricao") || "").trim(),
    data_inicio: String(fd.get("data_inicio") || "").slice(0, 10),
    data_fim: String(fd.get("data_fim") || "").slice(0, 10),
    inicio_inscricoes: String(fd.get("inicio_inscricoes") || "").slice(0, 10),
    fim_inscricoes: String(fd.get("fim_inscricoes") || "").slice(0, 10),
    banner_path: String(fd.get("banner_path") || "").trim(),
    cor_primaria: String(fd.get("cor_primaria") || "#FF5733"),
    cor_secundaria: String(fd.get("cor_secundaria") || "#1e1e24"),
    ativo: fd.get("ativo") ? 1 : 0,
    whatsapp_grupo_url: String(fd.get("whatsapp_grupo_url") || "").trim() || null,
  };
}

export async function createEvent(formData) {
  const sb = getSupabase();
  const payload = eventPayloadFromForm(formData);
  const { data, error } = await sb.from("eventos").insert(payload).select("id").single();
  if (error) throw error;
  return data;
}

export async function updateEvent(id, formData) {
  const sb = getSupabase();
  const payload = eventPayloadFromForm(formData);
  const { error } = await sb.from("eventos").update(payload).eq("id", id);
  if (error) throw error;
}

export async function deleteEvent(id) {
  const sb = getSupabase();
  const { error } = await sb.from("eventos").delete().eq("id", id);
  if (error) throw error;
}

const BANNER_BUCKET = "banners";
const BANNER_MAX_BYTES = 5 * 1024 * 1024;
const BANNER_MIME = new Set(["image/jpeg", "image/jpg", "image/png"]);

function bannerObjectPathFromUrl(bannerPath) {
  if (!bannerPath) return null;
  const marker = `/storage/v1/object/public/${BANNER_BUCKET}/`;
  const idx = bannerPath.indexOf(marker);
  if (idx === -1) return null;
  return decodeURIComponent(bannerPath.slice(idx + marker.length));
}

function bannerFilename(eventName, file) {
  const ext = /\.png$/i.test(file.name) ? "png" : "jpg";
  const slug = String(eventName || "evento")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 30) || "evento";
  const id = crypto.randomUUID().replace(/-/g, "").slice(0, 8);
  return `banner_${slug}_${id}.${ext}`;
}

export async function uploadEventBanner(file, eventName) {
  if (!(file instanceof File) || file.size === 0) {
    throw new Error("Selecione uma imagem de banner.");
  }
  if (!BANNER_MIME.has(file.type)) {
    throw new Error("Use uma imagem JPG ou PNG.");
  }
  if (file.size > BANNER_MAX_BYTES) {
    throw new Error("A imagem deve ter no máximo 5 MB.");
  }

  const sb = getSupabase();
  const path = bannerFilename(eventName, file);
  const { error } = await sb.storage.from(BANNER_BUCKET).upload(path, file, {
    cacheControl: "3600",
    upsert: false,
    contentType: file.type || "image/jpeg",
  });
  if (error) throw error;

  const { data } = sb.storage.from(BANNER_BUCKET).getPublicUrl(path);
  return data.publicUrl;
}

export async function deleteEventBanner(bannerPath) {
  const objectPath = bannerObjectPathFromUrl(bannerPath);
  if (!objectPath) return;
  const sb = getSupabase();
  const { error } = await sb.storage.from(BANNER_BUCKET).remove([objectPath]);
  if (error) throw error;
}
