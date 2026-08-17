# Deploy — GitHub Pages (sempre ativo)

Site estático em `docs/` + Supabase (mesmo banco do app Streamlit).

## 1. Supabase — SQL

No **SQL Editor**, execute na ordem:

1. `supabase/schema.sql` (se ainda não rodou)
2. `supabase/migration_evento_oficinas.sql` (se veio do modelo antigo)
3. **`supabase/browser_api.sql`** (RLS + funções para o navegador)
4. **`supabase/storage_banners.sql`** (upload de banners pelo admin)

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
- **SUPABASE_ANON_KEY** — Settings → API → **Publishable key** (`sb_publishable_...`)

Se aparecer *Invalid API key*, use a chave **anon** legacy (JWT `eyJ...`) em **Settings → API → Legacy API Keys**.

> A publishable/anon key é pública (vai no HTML). A segurança vem das **RLS policies** em `browser_api.sql`.

## 4. Banners e imagens

### Upload pelo admin (recomendado)

No painel **Eventos**, envie JPG/PNG (até 5 MB). A imagem vai para o **Supabase Storage** (bucket público `banners`) e a URL fica salva em `eventos.banner_path` — funciona no GitHub Pages sem commit manual de cada arquivo.

### Arquivos estáticos em `docs/image/`

Logos e banners fixos do repositório ficam em **`docs/image/`**:

- Logos do cabeçalho: `docs/image/LogoNextGen_nobg.png` e `docs/image/HOPE_nobg.png`
- Banners legados: caminhos como `image/nome.jpg` **desde que o arquivo exista em `docs/image/`**
- URLs completas (`https://...`) em `banner_path` também funcionam

## 5. Publicar o site (sempre ativo)

### Opção A — GitHub Pages (repositório **público**) ✅ configurado

Repositório público, branch `main`, pasta `/docs`.

URL: **https://hopenextgen.github.io/app_inscricoes/**

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
