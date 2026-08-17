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

## 5. GitHub Pages

1. Repositório → **Settings → Pages**
2. **Source:** Deploy from a branch  
3. **Branch:** `main`  
4. **Folder:** `/docs`  
5. Salvar — em ~2 min: `https://SEU_USUARIO.github.io/app_inscricoes/`

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
