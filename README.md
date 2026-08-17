# Portal de Inscrições — NextGen

Inscrições em eventos com oficinas, painel admin e dashboard.

## Versões

| Versão | Onde | Hibernação |
|--------|------|------------|
| **Site estático** (`docs/`) | GitHub Pages / Cloudflare / Netlify | Não |
| **Streamlit** (`app.py`) | Streamlit Cloud | Sim (plano grátis) |

## Site sempre ativo (GitHub Pages)

Siga o guia completo: **[DEPLOY.md](DEPLOY.md)**

Resumo:

1. Executar `supabase/browser_api.sql` no Supabase  
2. Criar usuário admin em **Authentication → Users**  
3. Preencher `docs/js/config.js` com a **anon key**  
4. Publicar `docs/` — GitHub Pages (repo **público**). Ver **[DEPLOY.md](DEPLOY.md)**

## Streamlit (legado / backup)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configure `.streamlit/secrets.toml` (veja `.streamlit/secrets.toml.example`).
