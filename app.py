import streamlit as st
import pandas as pd
from datetime import date, datetime
import database as db
import pdf_utils
import matrix_parser
import re

st.set_page_config(
    page_title="Control.ILL",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family:'Inter','Segoe UI',sans-serif; background:#F4F6F8; color:#263238; }
section[data-testid="stSidebar"] { background:#0F3D3E !important; }
section[data-testid="stSidebar"] * { color:#FFFFFF !important; }
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] div { color:#263238 !important; background:#FFFFFF !important; }
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] span { color:#263238 !important; }
section[data-testid="stSidebar"] input { color:#263238 !important; background:#FFFFFF !important; }
section[data-testid="stSidebar"] [data-baseweb="popover"] * { color:#263238 !important; background:#FFFFFF !important; }
section[data-testid="stSidebar"] hr { border-color:#1F4E5F !important; }
.ctrl-header { background:#FFFFFF; border-bottom:3px solid #0F3D3E; padding:0.9rem 1.5rem;
    margin:-1rem -1rem 1.5rem -1rem; display:flex; align-items:baseline; gap:0.75rem; }
.ctrl-header h1 { font-size:1.6rem; font-weight:700; color:#0F3D3E; margin:0; }
.ctrl-header span { font-size:0.78rem; color:#607D8B; }
.ctrl-header .user-badge { font-size:0.78rem; color:#0F3D3E; background:#D9EAF2;
    padding:3px 10px; border-radius:12px; font-weight:600; margin-left:auto; }
.sec-title { font-size:0.68rem; text-transform:uppercase; letter-spacing:0.12em; color:#0F3D3E;
    font-weight:600; border-bottom:1px solid #E0E6EA; padding-bottom:0.35rem; margin-bottom:0.9rem; margin-top:0.5rem; }
.alert-danger  { background:#FFEBEE; border-left:4px solid #C62828; padding:0.6rem 1rem; border-radius:4px; color:#B71C1C; margin:0.5rem 0; font-size:0.85rem; }
.alert-success { background:#E8F5E9; border-left:4px solid #2E7D32; padding:0.6rem 1rem; border-radius:4px; color:#1B5E20; margin:0.5rem 0; font-size:0.85rem; }
.alert-warn    { background:#FFF8E1; border-left:4px solid #F9A825; padding:0.6rem 1rem; border-radius:4px; color:#E65100; margin:0.5rem 0; font-size:0.85rem; }
.alert-info    { background:#E3F2FD; border-left:4px solid #1565C0; padding:0.6rem 1rem; border-radius:4px; color:#1565C0; margin:0.5rem 0; font-size:0.85rem; }
div[data-testid="stButton"] > button { background:#0F3D3E; color:#FFFFFF; border:none; border-radius:6px; font-weight:500; transition:background 0.2s; }
div[data-testid="stButton"] > button:hover { background:#1F4E5F; color:#FFFFFF; }
.dataframe thead th { background:#263238 !important; color:#FFFFFF !important; font-size:0.75rem; text-transform:uppercase; }
.dataframe tbody tr:nth-child(even) td { background:#F4F6F8 !important; }
.login-box { max-width:420px; margin:60px auto; background:#FFFFFF; border:1px solid #E0E6EA;
    border-radius:10px; padding:2.5rem; box-shadow:0 2px 12px rgba(15,61,62,0.08); }
.login-box h2 { color:#0F3D3E; font-size:1.4rem; font-weight:700; margin-bottom:0.2rem; text-align:center; }
.login-box p  { color:#607D8B; font-size:0.82rem; text-align:center; margin-bottom:1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Init DB ───────────────────────────────────────────────────────────────────
db.init_db()

# ── Session state ─────────────────────────────────────────────────────────────
for key, val in [
    ("usuario", None),
    ("lote_selecionado", None),
    ("setor_atual", "Hematologia"),
    ("pagina_admin", "Usuários"),
]:
    if key not in st.session_state:
        st.session_state[key] = val

# ═══════════════════════════════════════════════════════════════════════════════
# TELA DE LOGIN
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.usuario is None:
    st.markdown("""
    <div class="login-box">
        <h2>🔬 Control.ILL</h2>
        <p>Sistema de Registro, Validação e Rastreabilidade de Lotes Laboratoriais</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_login"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Acesso ao sistema")
            login_input = st.text_input("Login", placeholder="seu.login")
            senha_input = st.text_input("Senha", type="password", placeholder="••••••••")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

    if entrar:
        usuario = db.autenticar(login_input, senha_input)
        if usuario:
            st.session_state.usuario = usuario
            db.registrar_log(usuario["nome"], "Login", f"Acesso via {login_input}")
            st.rerun()
        else:
            st.error("Login ou senha incorretos.")

    st.stop()

# ── Usuário logado ────────────────────────────────────────────────────────────
U = st.session_state.usuario
NOME_U = U["nome"]
PERFIL_U = U["perfil"]   # 'admin' ou 'analista'
IS_ADMIN = PERFIL_U == "admin"

# ── Constantes ────────────────────────────────────────────────────────────────
SETORES = [
    "Hematologia", "Urinálise", "Parasitologia",
    "Microbiologia", "Imunobioquímica", "Gasometria",
    "Agência Transfusional",
]

EXAMES_POR_SETOR = {
    "Hematologia": [
        "Cellpack DCL", "Cellpack DFL", "Lysercell WNR", "Lysercell WDF",
        "Sulfolyser", "Fluorocell WDF", "Fluorocell WNR", "Fluorocell RET",
        "VHS", "Reticulócitos", "TAP", "KPTT",
    ],
    "Urinálise": [
        "Tira Reagente (Meditape UC-11A)", "UF - CellSheath",
        "UF - CellPack SF", "UF - CellPack CR",
        "UF - Fluorocell SF", "UF - Fluorocell CR",
        "Salina", "Bacterioscopia de Urina",
    ],
    "Parasitologia": ["Sangue Oculto", "Clostridium", "Rotavírus"],
    "Microbiologia": [
        "Meio Cromogênico de Urina", "Ágar Sangue", "Ágar Chocolate",
        "MacConkey", "Ágar Sangue/MacConkey", "Sabouraud c/ Clorafenicol",
        "Mueller-Hinton 90x15", "Ágar Strepto", "Ágar Mycosel",
        "Ágar Mueller-Hinton Grande", "Ágar Cromogênico Cândida",
        "Ágar Salmonella e Shigella", "Hemocultura Adulto Aerobic PLUS", "NG Carba",
    ],
    "Imunobioquímica": [
        "Ácido Úrico", "Albumina", "ALT", "Amilase", "AST",
        "Bilirrubina Direta", "Bilirrubina Total", "Bilirrubina Indireta",
        "Cálcio", "Cloro", "Colesterol Total", "CPK", "Creatinina",
        "Ferro", "Fosfatase Alcalina (ALKP)", "Fósforo", "GGT", "Glicose",
        "HDL Colesterol", "LDH", "Lipase", "Magnésio", "Potássio",
        "Proteínas Totais", "Proteína C - Reativa", "Sódio", "Triglicerídeos",
        "Ureia", "VDRL", "H1N1", "COVIDAg", "B-hCG Qualitativo",
        "B-hCG Quantitativo", "PTHi", "Vancomicina", "Troponina Qualitativa",
        "Gasometria", "NS1", "Procalcitonina", "PRO-BNP-NT",
        "Dímero-D", "HIV Teste Rápido",
    ],
    "Gasometria": ["Gasometria Arterial", "Gasometria Venosa", "Eletrodos de Gasometria"],
    "Agência Transfusional": [
        "Bolsa de Sangue Total", "Concentrado de Hemácias",
        "Plasma Fresco Congelado", "Plaquetas", "Soluções de Uso Transfusional",
    ],
}


def _label_lote(lote):
    nome  = lote.get("nome_exame") or ""
    num   = lote.get("lote_reagente") or ""
    total = lote.get("total_amostras", 0)
    if nome and num:
        return f"{nome} - {num} ({total})"
    return f"{nome or num or 'Lote sem número'} ({total})"


def _is_validado(cod):
    return bool(cod and re.match(r"^VL_\d{4}_\w+$", cod))


def _is_vencido(val_str):
    if not val_str:
        return False
    try:
        return datetime.strptime(val_str, "%d/%m/%Y").date() < date.today()
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="ctrl-header">'
    f'<h1>Control.ILL</h1>'
    f'<span>Sistema de Registro, Validação e Rastreabilidade de Lotes Laboratoriais</span>'
    f'<span class="user-badge">👤 {NOME_U}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"### 🔬 Control.ILL")
    st.markdown(f"**{NOME_U}**")
    st.markdown(f"<small>{'🔑 Administrador' if IS_ADMIN else '🧪 Analista'}</small>", unsafe_allow_html=True)
    st.markdown("---")

    nav_opcoes = ["📋 Lotes"]
    if IS_ADMIN:
        nav_opcoes += ["👥 Usuários", "📜 Log de Atividades"]
    nav_opcoes += ["🔒 Minha Conta"]

    pagina_nav = st.radio("Menu", nav_opcoes, label_visibility="collapsed")
    st.markdown("---")

    if pagina_nav == "📋 Lotes":
        setor = st.selectbox("Setor", SETORES, index=SETORES.index(st.session_state.setor_atual))
        st.session_state.setor_atual = setor

        qtd_fechados = db.contar_lotes_fechados_setor(setor)
        mostrar_fechados = st.checkbox(
            f"Mostrar fechados ({qtd_fechados})" if qtd_fechados else "Mostrar fechados",
            value=False, disabled=(qtd_fechados == 0),
        )
        lotes_setor = db.get_lotes_por_setor(setor, apenas_abertos=not mostrar_fechados)

        if st.button("➕ Novo Lote", use_container_width=True):
            novo_id = db.criar_lote(setor, usuario=NOME_U)
            db.registrar_log(NOME_U, "Novo lote", f"Setor: {setor}")
            st.session_state.lote_selecionado = novo_id
            st.rerun()

        abertos  = [l for l in lotes_setor if l.get("status") == "aberto"]
        fechados = [l for l in lotes_setor if l.get("status") == "fechado"]

        if abertos:
            st.markdown(f"**🟢 Abertos — {setor}**")
            for lote in abertos:
                sel = st.session_state.lote_selecionado == lote["id"]
                prefix = "✓ " if sel else ""
                if st.button(f"{prefix}{_label_lote(lote)}", key=f"btn_{lote['id']}", use_container_width=True):
                    st.session_state.lote_selecionado = lote["id"]
                    st.rerun()
        else:
            st.markdown("<small style='color:#90CAF9'>Nenhum lote aberto.</small>", unsafe_allow_html=True)

        if mostrar_fechados and fechados:
            st.markdown("---")
            st.markdown(f"**🔒 Fechados — {setor}**")
            for lote in fechados:
                sel = st.session_state.lote_selecionado == lote["id"]
                prefix = "✓ " if sel else ""
                if st.button(f"{prefix}🔒 {_label_lote(lote)}", key=f"btn_{lote['id']}", use_container_width=True):
                    st.session_state.lote_selecionado = lote["id"]
                    st.rerun()

    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        db.registrar_log(NOME_U, "Logout", "")
        st.session_state.usuario = None
        st.session_state.lote_selecionado = None
        st.rerun()
    st.markdown(f"<small style='color:#90CAF9'>Control.ILL v3.0</small>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA: GERENCIAR USUÁRIOS (só admin)
# ═══════════════════════════════════════════════════════════════════════════════
if pagina_nav == "👥 Usuários" and IS_ADMIN:
    st.markdown('<div class="sec-title">Gerenciar Analistas e Usuários</div>', unsafe_allow_html=True)

    tab_lista, tab_novo = st.tabs(["📋 Usuários Cadastrados", "➕ Novo Usuário"])

    with tab_lista:
        usuarios = db.get_todos_usuarios()
        for u in usuarios:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            ativo = bool(u["ativo"])
            with col1:
                st.markdown(f"**{u['nome']}** — `{u['login']}`")
            with col2:
                st.markdown(f"{'🔑 Admin' if u['perfil']=='admin' else '🧪 Analista'}")
            with col3:
                st.markdown(f"{'🟢 Ativo' if ativo else '🔴 Inativo'}")
            with col4:
                # Não deixar desativar a si mesmo nem o único admin
                eh_eu = u["login"] == U["login"]
                if not eh_eu:
                    if ativo:
                        if st.button("Desativar", key=f"des_{u['id']}"):
                            db.toggle_usuario(u["id"], False)
                            db.registrar_log(NOME_U, "Desativar usuário", u["login"])
                            st.rerun()
                    else:
                        if st.button("Ativar", key=f"at_{u['id']}"):
                            db.toggle_usuario(u["id"], True)
                            db.registrar_log(NOME_U, "Ativar usuário", u["login"])
                            st.rerun()
            st.markdown("---")

        # Alterar perfil / resetar senha
        st.markdown("#### Redefinir senha de um usuário")
        with st.form("form_reset_senha"):
            logins = [u["login"] for u in usuarios]
            sel_login = st.selectbox("Usuário", logins)
            nova_senha = st.text_input("Nova senha", type="password")
            if st.form_submit_button("Redefinir senha"):
                if nova_senha:
                    db.alterar_senha_usuario(sel_login, nova_senha)
                    db.registrar_log(NOME_U, "Redefinir senha", sel_login)
                    st.success(f"Senha de '{sel_login}' redefinida.")
                else:
                    st.error("Digite a nova senha.")

    with tab_novo:
        st.markdown("#### Cadastrar novo usuário")
        with st.form("form_novo_usuario"):
            c1, c2 = st.columns(2)
            with c1:
                novo_nome  = st.text_input("Nome completo *")
                novo_login = st.text_input("Login *", placeholder="primeiro.sobrenome")
            with c2:
                novo_senha  = st.text_input("Senha *", type="password")
                novo_perfil = st.selectbox("Perfil", ["analista", "admin"])
            if st.form_submit_button("✅ Criar usuário", use_container_width=True):
                if not novo_nome or not novo_login or not novo_senha:
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    ok, msg = db.criar_usuario(novo_nome, novo_login, novo_senha, novo_perfil)
                    if ok:
                        db.registrar_log(NOME_U, "Criar usuário", f"{novo_login} ({novo_perfil})")
                        st.success(f"✅ {msg}")
                    else:
                        st.error(msg)
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA: LOG DE ATIVIDADES (só admin)
# ═══════════════════════════════════════════════════════════════════════════════
if pagina_nav == "📜 Log de Atividades" and IS_ADMIN:
    st.markdown('<div class="sec-title">Log de Atividades</div>', unsafe_allow_html=True)
    logs = db.get_log(200)
    if logs:
        df_log = pd.DataFrame(logs)
        df_log.columns = ["Data/Hora", "Usuário", "Ação", "Detalhe"]
        st.dataframe(df_log, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma atividade registrada.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA: MINHA CONTA
# ═══════════════════════════════════════════════════════════════════════════════
if pagina_nav == "🔒 Minha Conta":
    st.markdown('<div class="sec-title">Minha Conta</div>', unsafe_allow_html=True)
    st.markdown(f"**Nome:** {NOME_U}")
    st.markdown(f"**Login:** `{U['login']}`")
    st.markdown(f"**Perfil:** {'Administrador' if IS_ADMIN else 'Analista'}")
    st.markdown("---")
    st.markdown("#### Alterar minha senha")
    with st.form("form_minha_senha"):
        senha_atual = st.text_input("Senha atual", type="password")
        senha_nova  = st.text_input("Nova senha", type="password")
        senha_conf  = st.text_input("Confirmar nova senha", type="password")
        if st.form_submit_button("💾 Alterar senha", use_container_width=True):
            usuario_check = db.autenticar(U["login"], senha_atual)
            if not usuario_check:
                st.error("Senha atual incorreta.")
            elif senha_nova != senha_conf:
                st.error("A nova senha e a confirmação não conferem.")
            elif len(senha_nova) < 6:
                st.error("A nova senha deve ter ao menos 6 caracteres.")
            else:
                db.alterar_senha_usuario(U["login"], senha_nova)
                db.registrar_log(NOME_U, "Alterou própria senha", "")
                st.success("Senha alterada com sucesso!")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA PRINCIPAL: LOTES
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.lote_selecionado:
    st.info("Selecione um lote na barra lateral ou crie um novo.")
    st.stop()

lote_id = st.session_state.lote_selecionado
lote = db.get_lote(lote_id)
if lote is None:
    st.error("Lote não encontrado.")
    st.session_state.lote_selecionado = None
    st.stop()

# ── BLOCO 1: Dados do Lote ────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Dados do Lote</div>', unsafe_allow_html=True)

# Info de quem abriu / fechou
info_partes = []
if lote.get("aberto_por"):
    info_partes.append(f"Aberto por: **{lote['aberto_por']}**")
if lote.get("fechado_por"):
    info_partes.append(f"Fechado por: **{lote['fechado_por']}**")
if info_partes:
    st.markdown("  ·  ".join(info_partes))

with st.form("form_dados_lote"):
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Setor", value=lote["setor"], disabled=True)

        opcoes = EXAMES_POR_SETOR.get(lote["setor"], [])
        exame_atual = lote.get("nome_exame") or ""
        lista_exame = ([exame_atual] + [o for o in opcoes if o != exame_atual]
                       if exame_atual and exame_atual not in opcoes else opcoes)
        idx_exame   = lista_exame.index(exame_atual) if exame_atual in lista_exame else 0

        exame_sel  = st.selectbox("Exame/Teste *", options=[""] + lista_exame,
                                   index=idx_exame + 1 if exame_atual else 0)
        exame_livre = st.text_input("Ou digite manualmente (reagente não listado)",
                                    value="" if exame_sel else exame_atual,
                                    placeholder="Ex.: Ágar CLED")
        nome_exame_final = exame_livre.strip() if exame_livre.strip() else exame_sel
        fabricante = st.text_input("Fabricante", value=lote.get("fabricante") or "")

    with c2:
        lote_reagente = st.text_input("Lote do Reagente", value=lote.get("lote_reagente") or "")

        val_str  = lote.get("validade") or ""
        val_date = None
        if val_str:
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    val_date = datetime.strptime(val_str, fmt).date(); break
                except ValueError:
                    pass
        validade_input = st.date_input("Validade do Lote (DD/MM/AAAA)",
                                        value=val_date or date.today(), format="DD/MM/YYYY")
        cod_validacao = st.text_input("Código de Validação (VL_AAAA_XXXX)",
                                       value=lote.get("cod_validacao") or "",
                                       placeholder="VL_2024_0001")
        # Responsável pre-preenchido com o analista logado
        responsavel = st.text_input("Responsável pela Validação",
                                     value=lote.get("responsavel") or NOME_U)

    submitted = st.form_submit_button("💾 Atualizar Dados do Lote", use_container_width=True)
    if submitted:
        db.atualizar_lote(lote_id,
            nome_exame=nome_exame_final, fabricante=fabricante,
            lote_reagente=lote_reagente, validade=validade_input.strftime("%d/%m/%Y"),
            cod_validacao=cod_validacao if _is_validado(cod_validacao) else "",
            responsavel=responsavel)
        db.registrar_log(NOME_U, "Atualizar lote", f"ID {lote_id} — {nome_exame_final}")
        st.success("Dados atualizados!")
        st.rerun()

# Alertas
lote = db.get_lote(lote_id)
if _is_vencido(lote.get("validade")):
    st.markdown('<div class="alert-danger">⚠️ Validade expirada! Este lote está vencido.</div>', unsafe_allow_html=True)
if not _is_validado(lote.get("cod_validacao")):
    st.markdown('<div class="alert-warn">🔴 Lote ainda não validado para uso.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-success">✅ Teste validado.</div>', unsafe_allow_html=True)


# ── BLOCO 2: Importação Matrix ────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="sec-title">Importação Matrix</div>', unsafe_allow_html=True)
st.markdown("Selecione o PDF da listagem de amostras emitido pelo Matrix Connect.")

uploader_key = f"pdf_{lote_id}"
try:
    pdf_file = st.file_uploader("Selecionar PDF Matrix", type=["pdf"], key=uploader_key)
except Exception:
    # Estado do upload ficou inconsistente (ex.: arquivo em cache do navegador
    # com extensão não permitida após uma atualização do app). Reseta o campo
    # em vez de derrubar a página inteira.
    if uploader_key in st.session_state:
        del st.session_state[uploader_key]
    st.warning("⚠️ O seletor de arquivo foi reiniciado. Selecione o PDF novamente.")
    pdf_file = None

if pdf_file:
    pdf_bytes = pdf_file.read()
    col_imp1, col_imp2 = st.columns(2)

    with col_imp1:
        if st.button("📥 Importar PDF Matrix para lotes abertos", use_container_width=True):
            with st.spinner("Lendo PDF e aplicando regras..."):
                try:
                    parsed    = matrix_parser.parse_matrix_pdf(pdf_bytes)
                    lotes_ab  = db.get_todos_lotes_abertos()
                    resultado = matrix_parser.aplicar_regras(parsed, lotes_ab)

                    total_inserido = 0; total_dup = 0; detalhes = []
                    for lt_id_imp, amostras_set in resultado.items():
                        lt_info  = next((l for l in lotes_ab if l['id'] == lt_id_imp), None)
                        nome_lt  = lt_info.get('nome_exame', '?') if lt_info else '?'
                        setor_lt = lt_info.get('setor', '?') if lt_info else '?'
                        novos = 0
                        for am in sorted(amostras_set):
                            ok = db.inserir_amostra(lt_id_imp, am, usuario=NOME_U)
                            if ok: novos += 1; total_inserido += 1
                            else: total_dup += 1
                        detalhes.append(f"**[{setor_lt}] {nome_lt}**: {novos} nova(s)")

                    if total_inserido:
                        db.registrar_log(NOME_U, "Importação Matrix",
                            f"{total_inserido} amostras em {len(resultado)} lote(s)")
                        st.success(
                            f"✅ **{total_inserido}** amostra(s) importada(s) | "
                            f"{total_dup} já existiam | PDF: {len(parsed)} registros")
                        for d in detalhes:
                            st.markdown(f"  • {d}")
                    else:
                        st.warning(
                            f"⚠️ Nenhuma amostra importada. "
                            f"PDF: {len(parsed)} registros | Lotes abertos: {len(lotes_ab)}. "
                            "Use o **Diagnóstico** ao lado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
                    import traceback; st.code(traceback.format_exc())

    with col_imp2:
        if st.button("🔍 Diagnóstico (ver o que será importado)", use_container_width=True):
            try:
                parsed    = matrix_parser.parse_matrix_pdf(pdf_bytes)
                lotes_ab  = db.get_todos_lotes_abertos()
                resultado = matrix_parser.aplicar_regras(parsed, lotes_ab)

                st.markdown(f"**PDF:** {len(parsed)} amostras | **Lotes abertos:** {len(lotes_ab)}")
                if lotes_ab:
                    for l in lotes_ab:
                        qtd = len(resultado.get(l['id'], set()))
                        ic  = "✅" if qtd > 0 else "⬜"
                        st.markdown(f"  {ic} [{l.get('setor','')}] **{l.get('nome_exame','(sem nome)')}** → {qtd} amostras")
                else:
                    st.error("Nenhum lote aberto no banco!")

                st.markdown("---")
                st.markdown("**Primeiras 30 amostras do PDF:**")
                st.dataframe(
                    pd.DataFrame([(a, e) for a, e in parsed[:30]], columns=["Amostra","Exames"]),
                    use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Erro: {e}")


# ── BLOCO 3: Amostras ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="sec-title">Testes do Lote — Amostra/Etiqueta</div>', unsafe_allow_html=True)

amostras = db.get_amostras(lote_id)
total_am = len(amostras)

col_i1, col_i2 = st.columns([3, 1])
with col_i1:
    nova_am = st.text_input(
        "Amostra/Etiqueta (10 dígitos — bipar ou digitar)",
        key=f"nova_{lote_id}", placeholder="Ex.: 1077247703")
with col_i2:
    ins_btn = st.button("Inserir", key=f"ins_{lote_id}", use_container_width=True)

if ins_btn and nova_am:
    am_clean = nova_am.strip()
    if not re.match(r"^\d{10}$", am_clean):
        st.error("A amostra deve ter exatamente 10 dígitos numéricos.")
    else:
        ok = db.inserir_amostra(lote_id, am_clean, usuario=NOME_U)
        if ok:
            db.registrar_log(NOME_U, "Inserir amostra", f"Lote {lote_id} — {am_clean}")
            st.success(f"Amostra {am_clean} inserida.")
        else:
            st.warning(f"Amostra {am_clean} já existe neste lote.")
        st.rerun()

st.markdown(f"**Amostras inseridas: {total_am}**")
if amostras:
    df_am = pd.DataFrame(amostras, columns=["Amostra/Etiqueta", "Inserido em", "Por"])
    st.dataframe(df_am, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma amostra inserida ainda.")


# ── BLOCO 4: Relatório ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="sec-title">Relatório</div>', unsafe_allow_html=True)

if lote.get("status") == "fechado":
    st.markdown(
        f'<div class="alert-info">🔒 Fechado em <b>{lote.get("dt_fechamento","—")}</b>'
        f' por <b>{lote.get("fechado_por","—")}</b></div>',
        unsafe_allow_html=True)
    if st.button("🔓 Reabrir este Lote", use_container_width=False):
        db.reabrir_lote(lote_id, usuario=NOME_U)
        db.registrar_log(NOME_U, "Reabrir lote", f"ID {lote_id}")
        st.success("Lote reaberto!")
        st.rerun()

col_r1, col_r2 = st.columns(2)
with col_r1:
    if st.button("🔒 Fechar Lote e Gerar Relatório PDF", use_container_width=True):
        lote_at = db.get_lote(lote_id)
        if not lote_at.get("nome_exame") or not lote_at.get("lote_reagente") or not lote_at.get("validade") or total_am == 0:
            st.error("Preencha nome do exame/teste, lote, validade e ao menos uma amostra.")
        else:
            dt_fec = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            db.fechar_lote(lote_id, dt_fec, usuario=NOME_U)
            db.registrar_log(NOME_U, "Fechar lote", f"ID {lote_id} — {lote_at.get('nome_exame')}")
            lote_final = db.get_lote(lote_id)
            am_final   = db.get_amostras(lote_id)
            termo      = "processadas" if lote_final.get("setor") == "Microbiologia" else "dosadas"
            pdf_bytes_out = pdf_utils.gerar_pdf(lote_final, am_final, termo)
            lt_num = lote_final.get("lote_reagente", "lote")
            ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button("⬇️ Baixar PDF", data=pdf_bytes_out,
                               file_name=f"relatorio_{lt_num}_{ts}.pdf",
                               mime="application/pdf", use_container_width=True)

with col_r2:
    if st.button("📄 Pré-visualizar (sem fechar lote)", use_container_width=True):
        lote_at   = db.get_lote(lote_id)
        am_final  = db.get_amostras(lote_id)
        termo     = "processadas" if lote_at.get("setor") == "Microbiologia" else "dosadas"
        pdf_bytes_out = pdf_utils.gerar_pdf(lote_at, am_final, termo)
        nome_ex = (lote_at.get("nome_exame") or "lote").replace(" ", "_")
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button("⬇️ Baixar Pré-visualização", data=pdf_bytes_out,
                           file_name=f"preview_{nome_ex}_{ts}.pdf",
                           mime="application/pdf", use_container_width=True)
