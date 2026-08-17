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

export async function getActiveEvents() {
  const sb = getSupabase();
  const today = new Date().toISOString().slice(0, 10);
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
