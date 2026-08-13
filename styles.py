import streamlit as st
import base64
import html
import os
import re
import uuid

DEFAULT_BANNER_PATH = "image/BannerSent.jpg"

def resolve_asset_path(path):
    """Resolve caminhos relativos de assets com base na pasta do projeto."""
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)

def get_image_base64(image_path):
    """Retorna a representação em base64 de uma imagem local para uso em HTML/CSS."""
    resolved_path = resolve_asset_path(image_path)
    if os.path.exists(resolved_path):
        with open(resolved_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return ""

def apply_global_styles():
    """Aplica o estilo CSS global que serve para todas as páginas (layout, fontes, scrollbar, cards)."""
    
    # Pegar caminhos das imagens de logos do cabeçalho
    image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image")
    logo_nextgen_path = os.path.join(image_dir, "LogoNextGen_nobg.png")
    logo_nextstep_path = os.path.join(image_dir, "NextStep_nobg.png")
    
    nextgen_b64 = get_image_base64(logo_nextgen_path)
    nextstep_b64 = get_image_base64(logo_nextstep_path)

    global_css = f"""
    <style>
    /* Importando fonte Outfit do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {{
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
        background-color: #0E0E10;
        color: #F3F4F6;
    }}
    
    /* Remover margens e preenchimentos excessivos da página Streamlit */
    div.block-container {{
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 800px;
    }}
    
    /* Ocultar menu hambúrguer padrão do Streamlit, mas manter botão da sidebar */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    [data-testid="stHeader"] {{
        background: transparent;
    }}

    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarCollapsedControl"] {{
        visibility: visible !important;
        display: flex !important;
        color: #F3F4F6 !important;
    }}
    
    /* Scrollbar personalizada */
    ::-webkit-scrollbar {{
        width: 8px;
    }}
    ::-webkit-scrollbar-track {{
        background: #121214;
    }}
    ::-webkit-scrollbar-thumb {{
        background: #3e3e42;
        border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: #FF5733;
    }}

    /* Botões com área de toque confortável */
    div.stButton > button,
    div.stFormSubmitButton > button {{
        min-height: 48px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        width: 100%;
    }}

    div.stFormSubmitButton > button {{
        background: linear-gradient(135deg, #FF5733 0%, #E65100 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
    }}

    /* Inputs legíveis em telas pequenas */
    div[data-testid="stTextInput"] input,
    div[data-baseweb="select"] div,
    div[data-baseweb="input"] input,
    textarea {{
        font-size: 16px !important;
    }}

    /* Sidebar mais confortável no celular */
    section[data-testid="stSidebar"] > div {{
        width: min(20rem, 88vw) !important;
    }}

    section[data-testid="stSidebar"] .stButton > button {{
        min-height: 44px !important;
    }}

    /* Tabelas/admin com rolagem horizontal no mobile */
    div[data-testid="stDataFrame"] {{
        overflow-x: auto;
    }}

    div[data-testid="stTabs"] button {{
        min-height: 44px;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }}

    /* Estilo para inputs e selectbox */
    div[data-baseweb="input"], div[data-baseweb="select"], textarea {{
        background-color: #1A1A1E !important;
        border: 1px solid #2A2A30 !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        transition: all 0.3s ease;
    }}
    
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {{
        border-color: #FF5733 !important;
        box-shadow: 0 0 0 1px #FF5733 !important;
    }}

    /* Estilização dos painéis/containers (Cards) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: linear-gradient(135deg, #16161a 0%, #1c1c22 100%);
        border-color: #2a2a32 !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
        margin-bottom: 20px;
    }}

    .event-card-banner-wrapper {{
        margin: 0 0 1rem 0;
        width: 100%;
        overflow: hidden;
        background-color: #121214;
        border: 1px solid #2a2a32;
        border-radius: 12px;
        line-height: 0;
    }}

    .event-card-banner {{
        width: 100%;
        height: auto;
        display: block;
        border-radius: 12px;
    }}

    .registration-summary {{
        background: linear-gradient(135deg, #16161a 0%, #1c1c22 100%);
        border: 1px solid #2a2a32;
        border-radius: 16px;
        padding: 24px;
        margin: 1rem 0 1.5rem 0;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.35);
    }}

    .registration-summary h3 {{
        margin: 0 0 16px 0;
        color: #FFFFFF;
        font-size: 1.25rem;
    }}

    .registration-summary ul {{
        list-style: none;
        margin: 0;
        padding: 0;
    }}

    .registration-summary li {{
        padding: 10px 0;
        border-bottom: 1px solid #2a2a32;
        color: #F3F4F6;
        line-height: 1.5;
    }}

    .registration-summary li:last-child {{
        border-bottom: none;
        padding-bottom: 0;
    }}

    .summary-label {{
        display: block;
        color: #9CA3AF;
        font-size: 0.82rem;
        margin-bottom: 4px;
    }}

    .summary-value {{
        display: block;
        color: #FFFFFF;
        font-size: 0.98rem;
        font-weight: 600;
    }}

    .event-meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 12px;
        font-size: 0.85rem;
        color: #9CA3AF;
    }}

    .event-meta span {{
        display: inline-flex;
        align-items: center;
        background-color: #24242B;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #32323D;
    }}

    /* Cabeçalho Premium */
    .header-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 20px;
        border-bottom: 1px solid #1F1F23;
        margin-bottom: 30px;
        gap: 20px;
    }}
    
    .logo-left {{
        height: 70px;
        object-fit: contain;
    }}
    
    .logo-right {{
        height: 70px;
        object-fit: contain;
    }}

    .header-title-wrapper {{
        text-align: center;
        flex-grow: 1;
    }}

    .header-title {{
        font-size: 2.2rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 0 !important;
        line-height: 1.2;
        letter-spacing: -0.5px;
    }}

    .header-subtitle {{
        color: #9CA3AF;
        margin: 6px 0 0 0 !important;
        font-size: 0.95rem;
    }}

    @media (max-width: 768px) {{
        div.block-container {{
            padding-top: 1rem;
            padding-left: max(0.85rem, env(safe-area-inset-left));
            padding-right: max(0.85rem, env(safe-area-inset-right));
            padding-bottom: calc(4rem + env(safe-area-inset-bottom));
            max-width: 100%;
        }}

        .header-container {{
            flex-direction: column;
            gap: 12px;
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
        }}

        .logo-left, .logo-right {{
            height: 52px;
        }}

        .header-title {{
            font-size: 1.55rem;
            letter-spacing: -0.3px;
        }}

        .header-subtitle {{
            font-size: 0.88rem;
            line-height: 1.45;
            padding: 0 0.25rem;
        }}

        .event-meta {{
            flex-direction: column;
            gap: 8px;
        }}

        .event-meta span {{
            width: 100%;
            justify-content: center;
            text-align: center;
        }}

        .registration-summary {{
            padding: 18px 16px;
            margin: 0.75rem 0 1.25rem 0;
        }}

        .registration-summary h3 {{
            font-size: 1.1rem;
        }}

        .summary-value {{
            font-size: 0.92rem;
            word-break: break-word;
        }}

        .event-banner {{
            max-width: 100%;
            max-height: 180px;
        }}

        .footer-container {{
            margin-top: 32px;
            padding-top: 24px;
            font-size: 0.8rem;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            margin-bottom: 16px;
        }}

        div[data-testid="stAlert"] {{
            font-size: 0.92rem;
        }}

        /* Formulários admin: colunas empilham no celular */
        div[data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            gap: 0.35rem;
        }}

        div[data-testid="column"] {{
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }}
    }}

    @media (max-width: 600px) {{
        .header-container {{
            flex-direction: column;
            gap: 15px;
            text-align: center;
        }}
        .logo-left, .logo-right {{
            height: 55px;
        }}
    }}

    @media (hover: none) and (pointer: coarse) {{
        div.stButton > button:hover {{
            transform: none !important;
        }}
    }}

    /* Estilo de Rodapé */
    .footer-container {{
        text-align: center;
        padding: 30px 10px 15px 10px;
        margin-top: 50px;
        border-top: 1px solid #1F1F23;
        color: #9CA3AF;
        font-size: 0.85rem;
    }}

    .bible-verse {{
        font-style: italic;
        margin-top: 8px;
        color: #9CA3AF;
        letter-spacing: 0.5px;
    }}

    .event-banner-wrapper {{
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }}

    .event-banner {{
        max-width: min(100%, 420px);
        max-height: 200px;
        width: auto;
        height: auto;
        object-fit: contain;
        border-radius: 12px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
    }}

    .whatsapp-cta-card {{
        background: linear-gradient(135deg, #0b6e59 0%, #128c7e 45%, #25d366 100%);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 18px;
        padding: 1.35rem 1.1rem;
        margin: 1.35rem 0 0.75rem 0;
        text-align: center;
        box-shadow: 0 14px 28px rgba(37, 211, 102, 0.28);
    }}

    .whatsapp-cta-card h4 {{
        color: #ffffff;
        margin: 0 0 0.55rem 0;
        font-size: 1.2rem;
        font-weight: 800;
        letter-spacing: -0.2px;
    }}

    .whatsapp-cta-card p {{
        color: #ecfdf3;
        margin: 0 0 1rem 0;
        font-size: 0.95rem;
        line-height: 1.45;
    }}

    .whatsapp-cta-button {{
        display: inline-block;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        background: #ffffff;
        color: #0b6e59 !important;
        font-weight: 800;
        font-size: 1.05rem;
        text-decoration: none !important;
        padding: 0.95rem 1rem;
        border-radius: 12px;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}

    .whatsapp-cta-button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.22);
    }}

    @media (max-width: 768px) {{
        .whatsapp-cta-card {{
            padding: 1.15rem 0.95rem;
            margin-top: 1.1rem;
        }}

        .whatsapp-cta-card h4 {{
            font-size: 1.08rem;
        }}

        .whatsapp-cta-button {{
            font-size: 1rem;
            min-height: 48px;
            line-height: 1.2;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
    }}
    </style>
    """
    st.markdown(global_css, unsafe_allow_html=True)

def apply_admin_layout():
    """Layout mais largo no painel admin (desktop), mantendo mobile centralizado."""
    admin_css = """
    <style>
    @media (min-width: 769px) {
        div.block-container {
            max-width: min(1200px, 96vw) !important;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        div[data-testid="stDataFrame"] {
            font-size: 0.92rem;
        }

        div[data-testid="stTabs"] {
            margin-bottom: 0.5rem;
        }
    }
    </style>
    """
    st.markdown(admin_css, unsafe_allow_html=True)


def apply_admin_workshops_styles():
    """Estilos compactos para a gestão de oficinas no admin."""
    workshops_css = """
    <style>
    .workshop-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0 0 0.15rem 0;
    }

    .workshop-card-subtitle {
        font-size: 0.88rem;
        color: #a1a1aa;
        margin: 0 0 0.65rem 0;
    }

    .workshop-card-meta {
        font-size: 0.82rem;
        color: #71717a;
        margin-top: 0.35rem;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #16161a 0%, #1c1c22 100%);
        border: 1px solid #2a2a32;
        border-radius: 12px;
        padding: 0.65rem 0.85rem;
    }

    div[data-testid="stMetric"] label {
        color: #a1a1aa !important;
        font-size: 0.78rem !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
    }
    </style>
    """
    st.markdown(workshops_css, unsafe_allow_html=True)

def apply_event_styles(cor_primaria, cor_secundaria):
    """Injeta regras de estilo customizadas dinamicamente de acordo com o tema do evento selecionado."""
    event_css = f"""
    <style>
    /* Sobrescrever cor de botões Streamlit */
    div.stButton > button {{
        background: linear-gradient(135deg, {cor_primaria} 0%, {cor_secundaria} 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 20px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3) !important;
        width: 100%;
        min-height: 48px !important;
    }}
    
    div.stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px {cor_primaria}4D !important;
        filter: brightness(1.1) !important;
    }}
    
    div.stButton > button:active {{
        transform: translateY(0) !important;
    }}
    
    /* Foco dos inputs baseado na cor primária do evento */
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {{
        border-color: {cor_primaria} !important;
        box-shadow: 0 0 0 1px {cor_primaria} !important;
    }}
    
    .event-card:hover {{
        border-color: {cor_primaria} !important;
        box-shadow: 0 12px 24px {cor_primaria}26 !important;
    }}
    
    /* Destaques de texto */
    .highlight {{
        color: {cor_primaria};
        font-weight: bold;
    }}
    </style>
    """
    st.markdown(event_css, unsafe_allow_html=True)

def render_header(title=None, subtitle=None):
    """Renderiza a logo do NextGen e a logo do NextStep no topo, alinhadas ao título central se fornecido."""
    image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image")
    logo_nextgen_path = os.path.join(image_dir, "LogoNextGen_nobg.png")
    logo_nextstep_path = os.path.join(image_dir, "NextStep_nobg.png")
    
    nextgen_b64 = get_image_base64(logo_nextgen_path)
    nextstep_b64 = get_image_base64(logo_nextstep_path)
    
    if title:
        header_html = f"""
        <div class="header-container">
            <img class="logo-left" src="data:image/png;base64,{nextgen_b64}" alt="NextGen Logo">
            <div class="header-title-wrapper">
                <h1 class="header-title">{title}</h1>
                {f'<p class="header-subtitle">{subtitle}</p>' if subtitle else ''}
            </div>
            <img class="logo-right" src="data:image/png;base64,{nextstep_b64}" alt="NextStep Logo">
        </div>
        """
    else:
        header_html = f"""
        <div class="header-container">
            <img class="logo-left" src="data:image/png;base64,{nextgen_b64}" alt="NextGen Logo">
            <img class="logo-right" src="data:image/png;base64,{nextstep_b64}" alt="NextStep Logo">
        </div>
        """
    st.markdown(header_html, unsafe_allow_html=True)

def resolve_banner_path(banner_path):
    """Resolve o caminho do banner cadastrado para o evento."""
    if not banner_path:
        return ""

    resolved_path = resolve_asset_path(banner_path)
    if resolved_path and os.path.exists(resolved_path):
        return resolved_path

    return ""

def save_uploaded_banner(uploaded_file, event_name=""):
    """Salva o banner enviado no cadastro e retorna o caminho relativo."""
    if uploaded_file is None:
        return ""

    image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image")
    os.makedirs(image_dir, exist_ok=True)

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        ext = ".jpg"

    slug = re.sub(r"[^a-z0-9]+", "_", event_name.lower()).strip("_")[:30] or "evento"
    filename = f"banner_{slug}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(image_dir, filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return f"image/{filename}"

def remove_banner_file(banner_path):
    """Remove do disco banners enviados pelo cadastro de eventos."""
    if not banner_path:
        return

    resolved_path = resolve_asset_path(banner_path)
    if not resolved_path or not os.path.exists(resolved_path):
        return

    filename = os.path.basename(resolved_path)
    if filename.startswith("banner_"):
        os.remove(resolved_path)

def render_registration_summary(summary):
    """Renderiza o resumo da inscrição em um card uniforme."""
    items = [
        ("Participante", summary["nome"]),
        ("Data de Nascimento", summary["data_nascimento"]),
        ("Evento", summary["evento"]),
    ]

    for workshop in summary.get("workshops", []):
        items.append((
            workshop["label"],
            f"{workshop['nome']} — Preletor: {workshop['preletor']}",
        ))

    if summary.get("responsavel_nome"):
        items.append(("Responsável", summary["responsavel_nome"]))
    if summary.get("responsavel_telefone"):
        items.append(("Telefone do Responsável", summary["responsavel_telefone"]))

    items_html = "".join(
        f'<li><span class="summary-label">{html.escape(label)}</span>'
        f'<span class="summary-value">{html.escape(value)}</span></li>'
        for label, value in items
    )

    summary_html = (
        f'<div class="registration-summary">'
        f'<h3>Resumo da sua Inscrição</h3>'
        f'<ul>{items_html}</ul>'
        f'</div>'
    )
    st.markdown(summary_html, unsafe_allow_html=True)


def render_whatsapp_group_cta(group_url, highlighted=True):
    """Botão para entrar no grupo oficial do evento no WhatsApp."""
    if not group_url:
        return

    safe_url = html.escape(group_url, quote=True)
    if highlighted:
        cta_html = f"""
        <div class="whatsapp-cta-card">
            <h4>📱 Entre no Grupo do WhatsApp do Congresso</h4>
            <p>Não perca avisos, novidades e informações importantes. Toque no botão abaixo para entrar.</p>
            <a class="whatsapp-cta-button" href="{safe_url}" target="_blank" rel="noopener noreferrer">
                Entrar no Grupo do WhatsApp
            </a>
        </div>
        """
        st.markdown(cta_html, unsafe_allow_html=True)
        return

    st.markdown("---")
    st.markdown("#### 📱 Grupo oficial do congresso")
    st.caption(
        "Entre no grupo do WhatsApp para receber avisos e novidades. "
        "Você precisa tocar no botão e confirmar a entrada no app."
    )
    st.link_button(
        "Entrar no Grupo do WhatsApp",
        group_url,
        use_container_width=True,
        type="primary",
    )

def render_card_banner(banner_path):
    """Renderiza o banner no topo do card da home."""
    resolved_path = resolve_banner_path(banner_path)
    if not resolved_path:
        return

    ext = os.path.splitext(resolved_path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    banner_b64 = get_image_base64(resolved_path)

    banner_html = f"""
    <div class="event-card-banner-wrapper">
        <img class="event-card-banner" src="data:{mime};base64,{banner_b64}" alt="Banner do evento">
    </div>
    """
    st.markdown(banner_html, unsafe_allow_html=True)

def render_clickable_event_card(event, data_ev, data_fim_ins):
    """Renderiza o card do evento e retorna True se o usuário clicou para inscrever."""
    banner_path = event.get("banner_path", "")

    with st.container(border=True):
        render_card_banner(banner_path)

        st.markdown(f"### 🔥 {event['nome']}")
        if event.get("descricao"):
            st.markdown(event["descricao"])

        st.markdown(
            f"<div class='event-meta'>"
            f"<span>📅 Data do Evento: {data_ev}</span>"
            f"<span>⏳ Inscrições até: {data_fim_ins}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        clicked = st.button(
            "Clique para se inscrever →",
            key=f"btn_ins_{event['id']}",
            use_container_width=True,
            type="primary",
        )

    return clicked

def render_event_banner(banner_path):
    """Renderiza o banner do evento com tamanho limitado."""
    resolved_path = resolve_banner_path(banner_path)
    if not resolved_path:
        return

    ext = os.path.splitext(resolved_path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    banner_b64 = get_image_base64(resolved_path)

    banner_html = f"""
    <div class="event-banner-wrapper">
        <img class="event-banner" src="data:{mime};base64,{banner_b64}" alt="Banner do evento">
    </div>
    """
    st.markdown(banner_html, unsafe_allow_html=True)

def render_footer():
    """Renderiza o rodapé com copyright e versículo."""
    footer_html = """
    <div class="footer-container">
        <span>&copy; 2026 Ministério NextGen. Todos os direitos reservados.</span>
        <div class="bible-verse">"Como o Pai me enviou, eu também vos envio." &mdash; João 20:21</div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)
