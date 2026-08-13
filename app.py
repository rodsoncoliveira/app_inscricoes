import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import database as db
import styles

# Configuração da página Streamlit (deve ser a primeira chamada)
st.set_page_config(
    page_title="Portal de Inscrições - NextGen",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Inicializar estados de navegação na sessão
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'selected_event_id' not in st.session_state:
    st.session_state.selected_event_id = None
if 'editing_event_id' not in st.session_state:
    st.session_state.editing_event_id = None
if 'editing_workshop_id' not in st.session_state:
    st.session_state.editing_workshop_id = None
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'registration_summary' not in st.session_state:
    st.session_state.registration_summary = None

def get_admin_password():
    """Senha do admin via secrets (produção) ou fallback local."""
    try:
        return st.secrets["admin_password"]
    except (KeyError, FileNotFoundError, AttributeError):
        return os.environ.get("ADMIN_PASSWORD", "admin123")

def render_admin_area(key_prefix="sidebar"):
    """Renderiza login e atalhos do painel administrativo."""
    st.markdown("### 🔐 Área Restrita")

    if st.session_state.admin_logged_in:
        st.success("Administrador autenticado")
        if st.button("Painel Administrativo", use_container_width=True, key=f"{key_prefix}_admin_panel"):
            st.session_state.page = "admin"
            st.rerun()
        if st.button("Sair da Administração", use_container_width=True, key=f"{key_prefix}_admin_logout"):
            st.session_state.admin_logged_in = False
            st.session_state.page = "home"
            st.rerun()
    else:
        if key_prefix == "sidebar":
            st.caption("Toque em ☰ no canto superior para abrir este menu.")
        admin_password = st.text_input(
            "Senha Admin",
            type="password",
            key=f"{key_prefix}_admin_pwd_input",
        )
        if st.button("Entrar", use_container_width=True, key=f"{key_prefix}_admin_login"):
            if admin_password == get_admin_password():
                st.session_state.admin_logged_in = True
                st.session_state.page = "admin"
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Senha incorreta!")

def render_admin_footer_access():
    """Acesso administrativo visível no rodapé (fallback quando a sidebar está fechada)."""
    with st.expander("🔐 Área administrativa"):
        render_admin_area(key_prefix="footer")

# Função para cadastrar dados iniciais (seeding) caso o banco esteja vazio
def seed_initial_data():
    events = db.get_all_events()
    if len(events) == 0:
        # Cadastrar o evento principal do Congresso Forjados
        banner_rel_path = styles.DEFAULT_BANNER_PATH
        
        event_id = db.create_event(
            nome="Congresso Forjados - The Sent",
            descricao="Forjados para ir. Enviados para cumprir. Como o Pai me enviou, eu também vos envio. João 20:21",
            data_inicio="2026-10-24",
            data_fim="2026-10-26",
            inicio_inscricoes="2026-08-01",
            fim_inscricoes="2026-10-23",
            banner_path=banner_rel_path,
            cor_primaria="#E65100",  # Laranja queimado premium
            cor_secundaria="#1A1A1E", # Cinza escuro profundo
            ativo=1
        )
        
        # Cadastrar oficinas iniciais associadas a este evento
        db.create_workshop(event_id, "Liderança de Impacto", "Pr. Eduardo Santos", 40)
        db.create_workshop(event_id, "Adoração e Adoradores", "Ministério Hope", 30)
        db.create_workshop(event_id, "Evangelismo na Era Digital", "Felipe Neto (Missionário)", 25)
        db.create_workshop(event_id, "Maturidade Cristã e Caráter", "Dra. Helena Souza", 35)

# Executar semeadura inicial
seed_initial_data()

# Aplicar estilos CSS globais
styles.apply_global_styles()

# Menu lateral para acessar o painel administrativo de forma limpa
with st.sidebar:
    render_admin_area(key_prefix="sidebar")

# Navegação principal do Portal

if st.session_state.page == 'home':
    # Cabeçalho Geral Alinhado
    styles.render_header(
        title="PORTAL DE INSCRIÇÕES", 
        subtitle="Clique no evento desejado para realizar sua inscrição"
    )
    st.write("")
    
    # Buscar eventos ativos
    active_events = db.get_active_events()
    
    if len(active_events) == 0:
        st.info("No momento não há eventos com inscrições abertas. Volte em breve!")
    else:
        for event in active_events:
            data_ini_str = db.format_date_br(event["data_inicio"])
            data_fim_str = db.format_date_br(event["data_fim"])
            data_ev = f"{data_ini_str} a {data_fim_str}"
            data_fim_ins = db.format_date_br(event["fim_inscricoes"])
            
            if styles.render_clickable_event_card(event, data_ev, data_fim_ins):
                st.session_state.selected_event_id = event['id']
                st.session_state.registration_summary = None
                st.session_state.page = 'register'
                st.rerun()
                
    render_admin_footer_access()
    styles.render_footer()

elif st.session_state.page == 'register':
    # Pegar dados do evento selecionado
    event = db.get_event(st.session_state.selected_event_id)
    
    if not event:
        st.error("Evento não encontrado.")
        if st.button("Voltar ao Início"):
            st.session_state.page = 'home'
            st.rerun()
    else:
        # Aplicar as cores dinâmicas do evento
        styles.apply_event_styles(event['cor_primaria'], event['cor_secundaria'])
        
        # Renderizar banner
        if styles.resolve_banner_path(event['banner_path']):
            styles.render_event_banner(event['banner_path'])
        else:
            st.markdown(f"<h1 style='color: {event['cor_primaria']}; text-align: center;'>{event['nome']}</h1>", unsafe_allow_html=True)
            
        st.write("")
        data_ini_str = db.format_date_br(event["data_inicio"])
        data_fim_str = db.format_date_br(event["data_fim"])
        st.markdown(f"**Data do Evento:** {data_ini_str} a {data_fim_str}")
        st.write(event['descricao'])
        st.markdown("---")

        if st.session_state.registration_summary:
            summary = st.session_state.registration_summary
            if summary.get("action") == "updated":
                st.success("✅ Inscrição atualizada com sucesso! Seus dados foram sobrescritos.")
            else:
                st.success("🎉 Inscrição confirmada com sucesso! Nos vemos lá!")

            if not summary.get("celebration_shown"):
                st.balloons()
                summary["celebration_shown"] = True
                st.session_state.registration_summary = summary

            styles.render_registration_summary(summary)

            if st.button("Voltar ao Início", key="btn_back_after_register", use_container_width=True):
                st.session_state.registration_summary = None
                st.session_state.page = 'home'
                st.rerun()
        else:
            st.markdown("### 📝 Formulário de Inscrição")

            workshops = db.get_workshop_vagas_info(event['id'])

            with st.form(key="form_inscricao"):
                nome = st.text_input("Nome Completo *", placeholder="Digite seu nome completo")
                data_nascimento = st.date_input(
                    "Data de Nascimento *",
                    value=date(2000, 1, 1),
                    min_value=date(1920, 1, 1),
                    max_value=date.today(),
                    format="DD/MM/YYYY"
                )
                whatsapp = st.text_input("WhatsApp / Celular *", placeholder="(00) 90000-0000")
                igreja = st.text_input("Igreja / Congregação *", placeholder="Ex: Comunidade Batista Hope")

                st.write("")
                st.markdown("#### 👨‍👩‍👧 Dados do Responsável")
                st.caption("Obrigatório para participantes menores de 18 anos.")
                responsavel_nome = st.text_input(
                    "Nome do Responsável",
                    placeholder="Digite o nome completo do responsável",
                )
                responsavel_telefone = st.text_input(
                    "Telefone do Responsável",
                    placeholder="(00) 90000-0000",
                )

                chosen_workshop_1 = None
                chosen_workshop_2 = None
                if len(workshops) > 0:
                    st.write("")
                    st.markdown("#### 🎯 Escolha suas Oficinas")
                    st.info("Você pode escolher até 2 oficinas. As vagas são limitadas por oficina.")

                    options_dict = {}
                    options_labels = []

                    for w in workshops:
                        label = f"{w['nome']} — Preletor: {w['preletor']} ({w['vagas_restantes']} vagas)"
                        if w['vagas_restantes'] <= 0:
                            label = f"🔴 {w['nome']} — Preletor: {w['preletor']} (ESGOTADO)"

                        options_dict[label] = w
                        options_labels.append(label)

                    selected_label_1 = st.selectbox("Oficina 1 *", options_labels)
                    chosen_workshop_1 = options_dict[selected_label_1]

                    options_labels_2 = ["Nenhuma"] + options_labels
                    options_dict_2 = {"Nenhuma": None}
                    options_dict_2.update(options_dict)

                    selected_label_2 = st.selectbox("Oficina 2 (opcional)", options_labels_2)
                    chosen_workshop_2 = options_dict_2[selected_label_2]

                st.write("")
                submit_button = st.form_submit_button("Confirmar Minha Inscrição")

            if submit_button:
                existing_registration = db.find_matching_registration(
                    event['id'], nome, data_nascimento
                )

                def workshop_is_blocked(workshop, slot_field):
                    if not workshop or workshop['vagas_restantes'] > 0:
                        return False
                    if not existing_registration:
                        return True
                    return existing_registration.get(slot_field) != workshop['id']

                blocked_1 = workshop_is_blocked(chosen_workshop_1, "oficina_id")
                blocked_2 = workshop_is_blocked(chosen_workshop_2, "oficina_id_2")

                if not nome or not whatsapp or not igreja:
                    st.error("Por favor, preencha todos os campos obrigatórios (*).")
                elif db.is_minor(data_nascimento) and (not responsavel_nome or not responsavel_telefone):
                    st.error("Menores de 18 anos devem informar nome e telefone do responsável.")
                elif chosen_workshop_1 and chosen_workshop_2 and chosen_workshop_1['id'] == chosen_workshop_2['id']:
                    st.error("Selecione duas oficinas diferentes.")
                elif blocked_1:
                    st.error(f"A oficina '{chosen_workshop_1['nome']}' já está lotada! Por favor, escolha outra.")
                elif blocked_2:
                    st.error(f"A oficina '{chosen_workshop_2['nome']}' já está lotada! Por favor, escolha outra.")
                else:
                    oficina_id = chosen_workshop_1['id'] if chosen_workshop_1 else None
                    oficina_id_2 = chosen_workshop_2['id'] if chosen_workshop_2 else None
                    data_nasc_str = data_nascimento.isoformat()

                    success, result, action = db.create_registration(
                        evento_id=event['id'],
                        nome=nome,
                        data_nascimento=data_nasc_str,
                        whatsapp=whatsapp,
                        igreja=igreja,
                        oficina_id=oficina_id,
                        oficina_id_2=oficina_id_2,
                        responsavel_nome=responsavel_nome.strip() if responsavel_nome else None,
                        responsavel_telefone=responsavel_telefone.strip() if responsavel_telefone else None,
                    )

                    if success:
                        workshops_summary = []
                        if chosen_workshop_1:
                            workshops_summary.append({
                                "label": "Oficina 1",
                                "nome": chosen_workshop_1["nome"],
                                "preletor": chosen_workshop_1["preletor"],
                            })
                        if chosen_workshop_2:
                            workshops_summary.append({
                                "label": "Oficina 2",
                                "nome": chosen_workshop_2["nome"],
                                "preletor": chosen_workshop_2["preletor"],
                            })

                        summary_data = {
                            "action": action,
                            "nome": nome,
                            "data_nascimento": db.format_date_br(data_nascimento),
                            "evento": event["nome"],
                            "workshops": workshops_summary,
                            "celebration_shown": False,
                        }
                        if db.is_minor(data_nascimento):
                            summary_data["responsavel_nome"] = responsavel_nome.strip()
                            summary_data["responsavel_telefone"] = responsavel_telefone.strip()

                        st.session_state.registration_summary = summary_data

                        st.rerun()
                    else:
                        st.error(f"Erro ao realizar inscrição: {result}")

            if st.button("Voltar ao Início", key="btn_back_home", use_container_width=True):
                st.session_state.page = 'home'
                st.rerun()
            
        render_admin_footer_access()
        styles.render_footer()

elif st.session_state.page == 'admin':
    # Garantir autenticação
    if not st.session_state.admin_logged_in:
        st.session_state.page = 'home'
        st.rerun()

    styles.apply_admin_layout()
        
    st.markdown("<h1 style='color:#FF5733;'>🛠️ Painel Administrativo</h1>", unsafe_allow_html=True)
    st.markdown("Gerencie eventos, oficinas e visualize relatórios de inscritos.")
    
    tab_eventos, tab_oficinas, tab_inscricoes = st.tabs(["📅 Eventos", "🎯 Oficinas", "👥 Inscrições"])
    
    # ----------------------------------------------------
    # TAB: EVENTOS
    # ----------------------------------------------------
    with tab_eventos:
        st.subheader("Configurar Eventos")
        
        # Verificar se está editando algum evento
        if st.session_state.editing_event_id is not None:
            ev_to_edit = db.get_event(st.session_state.editing_event_id)
            if ev_to_edit:
                st.write(f"### ✏️ Editar Evento: {ev_to_edit['nome']}")
                
                with st.form(key="form_edit_event"):
                    edit_nome = st.text_input("Nome do Evento", value=ev_to_edit['nome'])
                    edit_descricao = st.text_area("Descrição", value=ev_to_edit['descricao'])
                    col1, col2 = st.columns(2)
                    
                    try:
                        ev_date_ini_val = db.coerce_to_date(ev_to_edit["data_inicio"]) or date.today()
                    except ValueError:
                        ev_date_ini_val = date.today()

                    try:
                        ev_date_fim_val = db.coerce_to_date(ev_to_edit["data_fim"]) or date.today()
                    except ValueError:
                        ev_date_fim_val = date.today()

                    try:
                        ins_ini_val = db.coerce_to_date(ev_to_edit["inicio_inscricoes"]) or date.today()
                    except ValueError:
                        ins_ini_val = date.today()

                    try:
                        ins_fim_val = db.coerce_to_date(ev_to_edit["fim_inscricoes"]) or date.today()
                    except ValueError:
                        ins_fim_val = date.today()
                    
                    edit_data_inicio = col1.date_input("Data de Início", value=ev_date_ini_val, format="DD/MM/YYYY")
                    edit_data_fim = col2.date_input("Data de Fim", value=ev_date_fim_val, format="DD/MM/YYYY")
                    
                    col3, col4 = st.columns(2)
                    edit_inicio_inscricoes = col3.date_input("Início das Inscrições", value=ins_ini_val, format="DD/MM/YYYY")
                    edit_fim_inscricoes = col4.date_input("Fim das Inscrições", value=ins_fim_val, format="DD/MM/YYYY")

                    has_current_banner = bool(ev_to_edit.get("banner_path") and styles.resolve_banner_path(ev_to_edit["banner_path"]))
                    edit_remove_banner = False

                    if has_current_banner:
                        st.caption("Banner atual:")
                        styles.render_event_banner(ev_to_edit["banner_path"])
                        edit_remove_banner = st.checkbox(
                            "Remover banner atual",
                            key=f"remove_banner_{ev_to_edit['id']}",
                        )

                    edit_banner_upload = st.file_uploader(
                        "Enviar novo banner",
                        type=["jpg", "jpeg", "png"],
                        key="edit_banner_upload",
                    )
                    
                    col5, col6 = st.columns(2)
                    edit_cor_primaria = col5.color_picker("Cor Primária", value=ev_to_edit['cor_primaria'])
                    edit_cor_secundaria = col6.color_picker("Cor Secundária", value=ev_to_edit['cor_secundaria'])
                    edit_ativo = st.checkbox("Evento Ativo?", value=True if ev_to_edit['ativo'] == 1 else False)
                    
                    col_btn1, col_btn2 = st.columns(2)
                    btn_save_edit = col_btn1.form_submit_button("Salvar Alterações")
                    btn_cancel_edit = col_btn2.form_submit_button("Cancelar")
                    
                if btn_save_edit:
                    if not edit_nome:
                        st.error("O nome do evento é obrigatório.")
                    else:
                        date_errors = db.validate_event_dates(
                            edit_data_inicio,
                            edit_data_fim,
                            edit_inicio_inscricoes,
                            edit_fim_inscricoes,
                        )
                        if date_errors:
                            for error in date_errors:
                                st.error(error)
                        else:
                            banner_path = ev_to_edit["banner_path"]
                            if edit_banner_upload is not None:
                                styles.remove_banner_file(banner_path)
                                banner_path = styles.save_uploaded_banner(edit_banner_upload, edit_nome)
                            elif edit_remove_banner:
                                styles.remove_banner_file(banner_path)
                                banner_path = ""

                            db.update_event(
                                event_id=ev_to_edit['id'],
                                nome=edit_nome,
                                descricao=edit_descricao,
                                data_inicio=edit_data_inicio.isoformat(),
                                data_fim=edit_data_fim.isoformat(),
                                inicio_inscricoes=edit_inicio_inscricoes.isoformat(),
                                fim_inscricoes=edit_fim_inscricoes.isoformat(),
                                banner_path=banner_path,
                                cor_primaria=edit_cor_primaria,
                                cor_secundaria=edit_cor_secundaria,
                                ativo=1 if edit_ativo else 0
                            )
                            st.success("Evento atualizado com sucesso!")
                            st.session_state.editing_event_id = None
                            st.rerun()
                
                if btn_cancel_edit:
                    st.session_state.editing_event_id = None
                    st.rerun()
            else:
                st.session_state.editing_event_id = None
                st.rerun()
        else:
            # Formulário para criar novo evento
            with st.expander("➕ Adicionar Novo Evento"):
                with st.form(key="form_create_event"):
                    nome = st.text_input("Nome do Evento")
                    descricao = st.text_area("Descrição")
                    col1, col2 = st.columns(2)
                    data_inicio = col1.date_input("Data de Início", value=date.today(), format="DD/MM/YYYY")
                    data_fim = col2.date_input("Data de Fim", value=date.today(), format="DD/MM/YYYY")
                    
                    col3, col4 = st.columns(2)
                    inicio_inscricoes = col3.date_input("Início das Inscrições", value=date.today(), format="DD/MM/YYYY")
                    fim_inscricoes = col4.date_input("Fim das Inscrições", value=date.today(), format="DD/MM/YYYY")

                    banner_upload = st.file_uploader(
                        "Banner do Evento",
                        type=["jpg", "jpeg", "png"],
                        key="create_banner_upload",
                    )
                    
                    col5, col6 = st.columns(2)
                    cor_primaria = col5.color_picker("Cor Primária", value="#FF5733")
                    cor_secundaria = col6.color_picker("Cor Secundária", value="#1A1A1E")
                    ativo = st.checkbox("Evento Ativo?", value=True)
                    
                    btn_salvar_evento = st.form_submit_button("Salvar Evento")
                    
                if btn_salvar_evento:
                    if not nome:
                        st.error("O nome do evento é obrigatório.")
                    else:
                        date_errors = db.validate_event_dates(
                            data_inicio,
                            data_fim,
                            inicio_inscricoes,
                            fim_inscricoes,
                        )
                        if date_errors:
                            for error in date_errors:
                                st.error(error)
                        elif banner_upload is None:
                            st.error("Envie uma imagem de banner para o evento.")
                        else:
                            banner_path = styles.save_uploaded_banner(banner_upload, nome)
                            db.create_event(
                                nome=nome,
                                descricao=descricao,
                                data_inicio=data_inicio.isoformat(),
                                data_fim=data_fim.isoformat(),
                                inicio_inscricoes=inicio_inscricoes.isoformat(),
                                fim_inscricoes=fim_inscricoes.isoformat(),
                                banner_path=banner_path,
                                cor_primaria=cor_primaria,
                                cor_secundaria=cor_secundaria,
                                ativo=1 if ativo else 0
                            )
                            st.success("Evento cadastrado com sucesso!")
                            st.rerun()
                        
            # Listar eventos existentes
            st.write("### Eventos Cadastrados")
            all_events = db.get_all_events()
            if len(all_events) == 0:
                st.info("Nenhum evento cadastrado ainda.")
            else:
                for ev in all_events:
                    status_str = "🟢 Ativo" if ev['ativo'] == 1 else "🔴 Inativo"
                    visible, visibility_reason = db.get_registration_visibility(ev)
                    portal_status = "🌐 Visível no portal" if visible else f"🚫 Fora do portal: {visibility_reason}"
                    with st.container():
                        st.markdown(f"#### {ev['nome']} ({status_str})")
                        st.caption(portal_status)
                        
                        data_ini_str = db.format_date_br(ev["data_inicio"])
                        data_fim_str = db.format_date_br(ev["data_fim"])
                        ins_ini_str = db.format_date_br(ev["inicio_inscricoes"])
                        ins_fim_str = db.format_date_br(ev["fim_inscricoes"])
                        st.markdown(f"**Data:** {data_ini_str} a {data_fim_str} | **Inscrições:** {ins_ini_str} até {ins_fim_str}")
                        st.markdown(f"**Cores:** Primária: `{ev['cor_primaria']}` | Secundária: `{ev['cor_secundaria']}`")
                        
                        col_btns_ev1, col_btns_ev2 = st.columns(2)
                        if col_btns_ev1.button("Editar Evento", key=f"edit_ev_{ev['id']}"):
                            st.session_state.editing_event_id = ev['id']
                            st.rerun()
                            
                        if col_btns_ev2.button("Excluir Evento", key=f"del_ev_{ev['id']}"):
                            db.delete_event(ev['id'])
                            st.success("Evento excluído com sucesso!")
                            st.rerun()
                        st.markdown("---")

    # ----------------------------------------------------
    # TAB: OFICINAS
    # ----------------------------------------------------
    with tab_oficinas:
        st.subheader("Configurar Oficinas")
        
        events = db.get_all_events()
        if len(events) == 0:
            st.warning("Cadastre um evento primeiro para poder adicionar oficinas.")
        else:
            # Verificar se está editando alguma oficina
            if st.session_state.editing_workshop_id is not None:
                w_to_edit = db.get_workshop(st.session_state.editing_workshop_id)
                if w_to_edit:
                    st.write(f"### ✏️ Editar Oficina: {w_to_edit['nome']}")
                    
                    with st.form(key="form_edit_workshop"):
                        edit_nome_oficina = st.text_input("Nome da Oficina", value=w_to_edit['nome'])
                        edit_preletor = st.text_input("Preletor / Responsável", value=w_to_edit['preletor'])
                        edit_vagas = st.number_input("Quantidade de Vagas", min_value=1, value=int(w_to_edit['vagas']), step=1)
                        
                        col_btn_w1, col_btn_w2 = st.columns(2)
                        btn_save_edit_w = col_btn_w1.form_submit_button("Salvar Alterações")
                        btn_cancel_edit_w = col_btn_w2.form_submit_button("Cancelar")
                        
                    if btn_save_edit_w:
                        if not edit_nome_oficina or not edit_preletor:
                            st.error("Preencha todos os campos da oficina.")
                        else:
                            db.update_workshop(w_to_edit['id'], edit_nome_oficina, edit_preletor, int(edit_vagas))
                            st.success("Oficina atualizada com sucesso!")
                            st.session_state.editing_workshop_id = None
                            st.rerun()
                            
                    if btn_cancel_edit_w:
                        st.session_state.editing_workshop_id = None
                        st.rerun()
                else:
                    st.session_state.editing_workshop_id = None
                    st.rerun()
            else:
                event_options = {ev['nome']: ev['id'] for ev in events}
                selected_event_name = st.selectbox("Selecione o Evento para a Oficina:", list(event_options.keys()))
                selected_event_id = event_options[selected_event_name]
                
                with st.form(key="form_create_workshop"):
                    nome_oficina = st.text_input("Nome da Oficina")
                    preletor = st.text_input("Preletor / Responsável")
                    vagas = st.number_input("Quantidade de Vagas", min_value=1, value=30, step=1)
                    
                    btn_salvar_oficina = st.form_submit_button("Salvar Oficina")
                    
                if btn_salvar_oficina:
                    if not nome_oficina or not preletor:
                        st.error("Preencha todos os campos da oficina.")
                    else:
                        db.create_workshop(selected_event_id, nome_oficina, preletor, int(vagas))
                        st.success("Oficina cadastrada com sucesso!")
                        st.rerun()
                        
                # Listar oficinas do evento selecionado
                st.write(f"### Oficinas de: {selected_event_name}")
                workshops_info = db.get_workshop_vagas_info(selected_event_id)
                
                if len(workshops_info) == 0:
                    st.info("Nenhuma oficina cadastrada para este evento.")
                else:
                    # Mostrar DataFrame para visão geral
                    df_workshops = pd.DataFrame(workshops_info)
                    df_workshops.columns = ["ID", "Nome da Oficina", "Preletor", "Vagas Totais", "Vagas Ocupadas", "Vagas Restantes"]
                    st.dataframe(df_workshops, use_container_width=True)
                    
                    # Ações de linha para gerenciar individualmente
                    st.write("#### Gerenciar Oficinas")
                    for w in workshops_info:
                        col_info, col_act1, col_act2 = st.columns([3, 1, 1])
                        col_info.markdown(f"**{w['nome']}** ({w['preletor']}) — *{w['vagas_restantes']} vagas rest.*")
                        
                        if col_act1.button("Editar", key=f"edit_w_{w['id']}"):
                            st.session_state.editing_workshop_id = w['id']
                            st.rerun()
                            
                        if col_act2.button("Excluir", key=f"del_w_{w['id']}"):
                            db.delete_workshop(w['id'])
                            st.success(f"Oficina '{w['nome']}' excluída com sucesso!")
                            st.rerun()

    # ----------------------------------------------------
    # TAB: INSCRIÇÕES
    # ----------------------------------------------------
    with tab_inscricoes:
        st.subheader("Gerenciar Inscrições")
        
        events = db.get_all_events()
        if len(events) == 0:
            st.warning("Nenhum evento disponível.")
        else:
            event_options = {ev['nome']: ev['id'] for ev in events}
            selected_event_name_ins = st.selectbox("Filtrar Inscrições por Evento:", list(event_options.keys()), key="select_event_ins")
            selected_event_id_ins = event_options[selected_event_name_ins]
            
            # Buscar inscrições
            registrations = db.get_registrations_by_event(selected_event_id_ins)
            
            # Métricas rápidas
            st.write("")
            col_met1, col_met2 = st.columns(2)
            col_met1.metric("Total de Inscritos", len(registrations))
            
            # Oficinas vagas info para ver a lotação geral
            workshops_info = db.get_workshop_vagas_info(selected_event_id_ins)
            vagas_totais_evento = sum([w['vagas_totais'] for w in workshops_info])
            col_met2.metric("Capacidade Total Oficinas", vagas_totais_evento)
            
            if len(registrations) == 0:
                st.info("Nenhuma inscrição realizada para este evento ainda.")
            else:
                # Exibir DataFrame de inscrições
                df_reg = pd.DataFrame(registrations)
                
                # Limpar e traduzir colunas para exibição
                df_display = df_reg[[
                    "id", "nome", "data_nascimento", "whatsapp", "igreja",
                    "responsavel_nome", "responsavel_telefone",
                    "oficina_nome", "oficina_nome_2", "data_inscricao"
                ]].copy()
                df_display["responsavel_nome"] = df_display["responsavel_nome"].fillna("")
                df_display["responsavel_telefone"] = df_display["responsavel_telefone"].fillna("")
                df_display["data_nascimento"] = df_display["data_nascimento"].apply(db.format_date_br)
                df_display["data_inscricao"] = df_display["data_inscricao"].apply(db.format_datetime_br)

                def format_workshops(row):
                    workshops_list = []
                    if row.get("oficina_nome"):
                        workshops_list.append(row["oficina_nome"])
                    if row.get("oficina_nome_2"):
                        workshops_list.append(row["oficina_nome_2"])
                    return " / ".join(workshops_list)

                df_display["oficinas"] = df_display.apply(format_workshops, axis=1)
                df_display = df_display[[
                    "id", "nome", "data_nascimento", "whatsapp", "igreja",
                    "responsavel_nome", "responsavel_telefone", "oficinas", "data_inscricao"
                ]]
                df_display.columns = [
                    "ID", "Nome Completo", "Data Nascimento",
                    "WhatsApp", "Igreja", "Responsável", "Tel. Responsável",
                    "Oficinas", "Data Inscrição"
                ]
                
                st.dataframe(df_display, use_container_width=True)
                
                # Exportar dados
                csv = df_display.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Planilha (CSV)",
                    data=csv,
                    file_name=f"inscricoes_{selected_event_name_ins.lower().replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Excluir inscrição específica
                st.write("#### Cancelar Inscrição")
                id_to_delete = st.number_input("Digite o ID da inscrição a excluir:", min_value=1, step=1)
                if st.button("Excluir Inscrição"):
                    # Verificar se o ID existe
                    if id_to_delete in df_display["ID"].values:
                        db.delete_registration(id_to_delete)
                        st.success(f"Inscrição ID {id_to_delete} excluída com sucesso!")
                        st.rerun()
                    else:
                        st.error("ID de inscrição não encontrado neste evento.")

    # Botão de voltar ao portal geral
    st.write("")
    if st.button("Voltar ao Portal Público", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
