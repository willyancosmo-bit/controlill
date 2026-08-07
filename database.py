"""
database.py — Control.ILL v4.1
Banco de dados: Google Sheets via Service Account
A chave é lida dos Secrets do Streamlit — nunca fica no código!
"""
import hashlib
from datetime import datetime

SHEET_ID = "1GSCfw5Ct9o1lXuptSuCoL4vxS4xbLqf5MbyWWALInEA"

ABA_USUARIOS = "usuarios"
ABA_LOTES    = "lotes"
ABA_AMOSTRAS = "amostras"
ABA_LOG      = "log"

HEADER_USUARIOS = ["id","nome","login","senha_hash","perfil","ativo","criado_em"]
HEADER_LOTES    = ["id","setor","nome_exame","fabricante","lote_reagente","validade",
                   "cod_validacao","responsavel","aberto_por","fechado_por",
                   "dt_abertura","dt_fechamento","status","criado_em"]
HEADER_AMOSTRAS = ["id","lote_id","amostra","inserido_por","inserido_em"]
HEADER_LOG      = ["id","usuario","acao","detalhe","criado_em"]

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()


def _agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _get_creds_dict():
    """Lê as credenciais dos Secrets do Streamlit."""
    import streamlit as st
    import json
    raw = st.secrets.get("GOOGLE_CREDENTIALS", "")
    if not raw:
        raise Exception("Secret GOOGLE_CREDENTIALS não encontrado no Streamlit!")
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw)


_sh = None
_ws_cache = {}   # nome_aba -> objeto Worksheet (evita fetch_sheet_metadata repetido)


def _get_sheet():
    global _sh
    if _sh is None:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = _get_creds_dict()
        creds = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)
        gc = gspread.authorize(creds)
        _sh = gc.open_by_key(SHEET_ID)
    return _sh


def _with_retry(func, tentativas=4, espera_base=1.5):
    """
    Executa func() com retentativas (backoff exponencial) para absorver
    erros transitórios da API do Google (429 quota exceeded, 500, 503).
    Não faz retry de erros que não são transitórios (ex.: "already exists").
    """
    import time
    import gspread

    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            return func()
        except gspread.exceptions.APIError as e:
            ultimo_erro = e
            msg = str(e)
            if "already exists" in msg:
                raise
            if tentativa < tentativas - 1:
                time.sleep(espera_base * (2 ** tentativa))
            else:
                raise
    raise ultimo_erro


def _get_aba(nome):
    if nome in _ws_cache:
        return _ws_cache[nome]
    try:
        ws = _with_retry(lambda: _get_sheet().worksheet(nome))
        _ws_cache[nome] = ws
        return ws
    except Exception:
        return None


def _garantir_aba(nome, header):
    import gspread

    if nome in _ws_cache:
        return _ws_cache[nome]

    sh = _get_sheet()
    try:
        ws = _with_retry(lambda: sh.worksheet(nome))
    except gspread.exceptions.WorksheetNotFound:
        try:
            ws = _with_retry(lambda: sh.add_worksheet(title=nome, rows=2000, cols=len(header)))
            _with_retry(lambda: ws.append_row(header))
            _ws_cache[nome] = ws
            return ws
        except gspread.exceptions.APIError as e:
            # Outra sessão/rerun do Streamlit criou a aba entre a checagem
            # acima e esta tentativa de criação (condição de corrida).
            if "already exists" in str(e):
                ws = _with_retry(lambda: sh.worksheet(nome))
            else:
                raise

    # Aba já existia: garante que o cabeçalho está presente.
    try:
        if not _with_retry(lambda: ws.row_values(1)):
            _with_retry(lambda: ws.append_row(header))
    except gspread.exceptions.APIError:
        # Falha transitória persistente ao checar/gravar cabeçalho não deve
        # derrubar o fluxo nem disparar recriação indevida da aba.
        pass

    _ws_cache[nome] = ws
    return ws


def _proximo_id(ws) -> int:
    vals = ws.col_values(1)
    ids = [int(v) for v in vals[1:] if str(v).isdigit()]
    return max(ids) + 1 if ids else 1


def _todas_linhas(ws, header) -> list:
    try:
        return ws.get_all_records(expected_headers=header)
    except Exception:
        return []


def init_db():
    try:
        ws_u = _garantir_aba(ABA_USUARIOS, HEADER_USUARIOS)
        _garantir_aba(ABA_LOTES,    HEADER_LOTES)
        _garantir_aba(ABA_AMOSTRAS, HEADER_AMOSTRAS)
        _garantir_aba(ABA_LOG,      HEADER_LOG)
        rows = _todas_linhas(ws_u, HEADER_USUARIOS)
        if not rows:
            ws_u.append_row([1,"Administrador","admin",_hash("admin123"),"admin",1,_agora()])
    except Exception as e:
        import streamlit as st
        st.error(f"Erro ao conectar ao Google Sheets: {e}")


# ── USUÁRIOS ──────────────────────────────────────────────────────────────────
def autenticar(login, senha):
    ws = _get_aba(ABA_USUARIOS)
    if not ws: return None
    for r in _todas_linhas(ws, HEADER_USUARIOS):
        if (str(r.get("login","")).lower() == login.strip().lower()
                and str(r.get("senha_hash","")) == _hash(senha)
                and str(r.get("ativo","")) in ("1","True","true")):
            return r
    return None


def get_todos_usuarios():
    ws = _get_aba(ABA_USUARIOS)
    return _todas_linhas(ws, HEADER_USUARIOS) if ws else []


def criar_usuario(nome, login, senha, perfil="analista"):
    ws = _garantir_aba(ABA_USUARIOS, HEADER_USUARIOS)
    for r in _todas_linhas(ws, HEADER_USUARIOS):
        if str(r.get("login","")).lower() == login.strip().lower():
            return False, f"Login '{login}' já existe."
    ws.append_row([_proximo_id(ws), nome.strip(), login.strip().lower(),
                   _hash(senha), perfil, 1, _agora()])
    return True, "Usuário criado com sucesso."


def alterar_senha_usuario(login, senha_nova):
    ws = _garantir_aba(ABA_USUARIOS, HEADER_USUARIOS)
    for i, row in enumerate(ws.get_all_values()[1:], start=2):
        if row[2].lower() == login.strip().lower():
            ws.update_cell(i, 4, _hash(senha_nova)); break


def toggle_usuario(usuario_id, ativo):
    ws = _garantir_aba(ABA_USUARIOS, HEADER_USUARIOS)
    for i, row in enumerate(ws.get_all_values()[1:], start=2):
        if str(row[0]) == str(usuario_id):
            ws.update_cell(i, 6, 1 if ativo else 0); break


# ── LOG ───────────────────────────────────────────────────────────────────────
def registrar_log(usuario, acao, detalhe=""):
    try:
        ws = _garantir_aba(ABA_LOG, HEADER_LOG)
        ws.append_row([_proximo_id(ws), usuario, acao, detalhe, _agora()])
    except Exception:
        pass


def get_log(limite=200):
    ws = _get_aba(ABA_LOG)
    if not ws: return []
    return list(reversed(_todas_linhas(ws, HEADER_LOG)))[:limite]


# ── LOTES ─────────────────────────────────────────────────────────────────────
def _n_amostras(lote_id):
    ws = _get_aba(ABA_AMOSTRAS)
    if not ws: return 0
    return sum(1 for r in ws.get_all_values()[1:] if str(r[1]) == str(lote_id))


def criar_lote(setor, usuario=""):
    ws = _garantir_aba(ABA_LOTES, HEADER_LOTES)
    novo_id = _proximo_id(ws)
    ws.append_row([novo_id,setor,"","","","","","",usuario,"",_agora(),"","aberto",_agora()])
    return novo_id


def get_lote(lote_id):
    ws = _get_aba(ABA_LOTES)
    if not ws: return None
    for r in _todas_linhas(ws, HEADER_LOTES):
        if str(r.get("id","")) == str(lote_id):
            r["total_amostras"] = _n_amostras(lote_id)
            return r
    return None


def get_lotes_por_setor(setor, apenas_abertos=True):
    ws = _get_aba(ABA_LOTES)
    if not ws: return []
    result = []
    for r in _todas_linhas(ws, HEADER_LOTES):
        if r.get("setor","") != setor: continue
        if apenas_abertos and r.get("status","") != "aberto": continue
        r["total_amostras"] = _n_amostras(r["id"])
        result.append(r)
    result.sort(key=lambda x: int(x.get("id",0)), reverse=True)
    return result


def contar_lotes_fechados_setor(setor):
    ws = _get_aba(ABA_LOTES)
    if not ws: return 0
    return sum(1 for r in _todas_linhas(ws, HEADER_LOTES)
               if r.get("setor","") == setor and r.get("status","") == "fechado")


def reabrir_lote(lote_id, usuario=""):
    ws = _garantir_aba(ABA_LOTES, HEADER_LOTES)
    for i, row in enumerate(ws.get_all_values()[1:], start=2):
        if str(row[0]) == str(lote_id):
            ws.update_cell(i, 13, "aberto")
            ws.update_cell(i, 12, "")
            ws.update_cell(i, 10, ""); break


def get_todos_lotes_abertos():
    ws = _get_aba(ABA_LOTES)
    if not ws: return []
    return [r for r in _todas_linhas(ws, HEADER_LOTES) if r.get("status","") == "aberto"]


def atualizar_lote(lote_id, nome_exame=None, fabricante=None, lote_reagente=None,
                   validade=None, cod_validacao=None, responsavel=None):
    ws = _garantir_aba(ABA_LOTES, HEADER_LOTES)
    for i, row in enumerate(ws.get_all_values()[1:], start=2):
        if str(row[0]) == str(lote_id):
            for col, val in [(3,nome_exame),(4,fabricante),(5,lote_reagente),
                             (6,validade),(7,cod_validacao),(8,responsavel)]:
                ws.update_cell(i, col, val or "")
            break


def fechar_lote(lote_id, dt_fechamento, usuario=""):
    ws = _garantir_aba(ABA_LOTES, HEADER_LOTES)
    for i, row in enumerate(ws.get_all_values()[1:], start=2):
        if str(row[0]) == str(lote_id):
            ws.update_cell(i, 13, "fechado")
            ws.update_cell(i, 12, dt_fechamento)
            ws.update_cell(i, 10, usuario); break


# ── AMOSTRAS ──────────────────────────────────────────────────────────────────
def inserir_amostra(lote_id, amostra, usuario=""):
    try:
        ws = _garantir_aba(ABA_AMOSTRAS, HEADER_AMOSTRAS)
        for row in ws.get_all_values()[1:]:
            if str(row[1]) == str(lote_id) and str(row[2]) == amostra.strip():
                return False
        ws.append_row([_proximo_id(ws), lote_id, amostra.strip(), usuario, _agora()])
        return True
    except Exception:
        return False


def get_amostras(lote_id):
    ws = _get_aba(ABA_AMOSTRAS)
    if not ws: return []
    result = []
    for row in ws.get_all_values()[1:]:
        if len(row) >= 5 and str(row[1]) == str(lote_id):
            result.append((row[2], row[4], row[3]))
    return result
