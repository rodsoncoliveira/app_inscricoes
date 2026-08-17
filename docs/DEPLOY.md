# Deploy — GitHub Pages (sempre ativo)

Site estático em `docs/` + Supabase (mesmo banco do app Streamlit).

## 1. Supabase — SQL

No **SQL Editor**, execute na ordem:

1. `supabase/schema.sql` (se ainda não rodou)
2. `supabase/migration_evento_oficinas.sql` (se veio do modelo antigo)
3. **`supabase/browser_api.sql`** (RLS + funções para o navegador)

## 2. Supabase — usuário admin

1. **Authentication → Users → Add user**
2. E-mail e senha do organizador
3. Esse login entra em `admin.html`

## 3. Configurar o site

```bash
cp docs/js/config.example.js docs/js/config.js
```

Edite `docs/js/config.js`:

- **SUPABASE_URL** — Settings → API → Project URL  
- **SUPABASE_ANON_KEY** — Settings → API → `anon` `public`

> A anon key é pública (vai no HTML). A segurança vem das **RLS policies** em `browser_api.sql`.

## 4. Banners

Copie imagens de banner para `docs/image/` e mantenha em `eventos.banner_path` caminhos como `image/nome.jpg`.

Ou use URL completa (`https://...`) no campo `banner_path`.

## 5. Publicar o site (sempre ativo)

### Opção A — GitHub Pages (repositório **público**)

No plano gratuito, GitHub Pages **não funciona em repositório privado**.

1. Repositório → **Settings → General → Danger Zone → Change visibility → Public**
2. **Settings → Pages**
3. **Source:** Deploy from a branch  
4. **Branch:** `main`  
5. **Folder:** `/docs`  
6. Salvar — em ~2 min: `https://rodsoncoliveira.github.io/app_inscricoes/`

> A anon key no `config.js` é pública por design; o banco fica protegido por RLS.

### Opção B — Cloudflare Pages (repo pode continuar privado)

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages → Create → Pages → Connect to Git**
2. Autorize o GitHub e selecione `app_inscricoes`
3. **Build command:** (vazio)  
4. **Build output directory:** `docs`  
5. Deploy — URL tipo `https://app-inscricoes.pages.dev`

### Opção C — Netlify (repo privado OK no plano grátis)

1. [app.netlify.com](https://app.netlify.com) → **Add new site → Import an existing project**
2. Conecte o GitHub, branch `main`
3. **Publish directory:** `docs`  
4. Deploy

## 6. URLs

| Página | Caminho |
|--------|---------|
| Inscrições | `/docs/index.html` ou raiz do Pages |
| Admin | `/docs/admin.html` |

## Streamlit

O app Python (`app.py`) pode continuar como backup local ou ser desligado no Streamlit Cloud após validar o site estático.

## Checklist pós-deploy

- [ ] Inscrição teste no portal público  
- [ ] Escolha de oficinas  
- [ ] Login admin  
- [ ] Dashboard e exclusão de inscrição  
- [ ] Executar `browser_api.sql` em produção  
