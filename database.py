"""
database.py — Control.ILL v4.0
Banco de dados: Google Sheets via Service Account
- Dados NUNCA somem (Google Drive é permanente)
- Gratuito para sempre
- Sem pausas ou suspensões
"""
import hashlib
from datetime import datetime

SHEET_ID = "1GSCfw5Ct9o1lXuptSuCoL4vxS4xbLqf5MbyWWALInEA"

_CREDS_DICT = {
    "type": "service_account",
    "project_id": "controlill",
    "private_key_id": "72a6b2903b73b3d12ff54fd932676df66a8fa0e6",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCi1BGD6fwY5RCl\nLblFCP2RoJILdLhHb6SMAkUw6pksybXrRXV6CBdCA6FHPY6RN6PJ4p1m220xyzIU\n8MWqtZci5Ke4gHKEz3Jp9zTLRwa8+HDAKPEZQGaKbgxI89JFY75FfxCsC18Z4V4Q\nx/2kVN7b8tTUcn/GqdVPbYvriOUd/dawwIi4kp1sQek5weuH27nRsF8kzofckDHt\nKRSIWbkpskm9dBTIdEQU59VyYrRUUtRhh6srVwbCrEwlQ/loSHL6UZtqCpgTW1a1\nJqEYV+6W1sVbJPCL4K/eiqtecdC6kwa4/zYJ2gHUqvxqi1p5bhS85BD9vGCeASyZ\nf1MuOSrbAgMBAAECggEADdbylNYVdv7j7EuM8hYyiecuTUpNbhz0zRsASzPAHd4Y\ngqJzuryR+tVuJtek6iji2Kz/Q0J77yiIiDPIHptdTjpFxdknuAFzMG3c5I4+lLSV\nI3AXa1Wy9tR7DNRUgftZV8orXkQqgCZMpXvUzjE8g/te0EkvHRv1pSZNfJE1JYL5\nadwzUlZlw9uztIiGmqr0koMqlIVDTaKlYQMYzWxD4D40Mv7Xxjb3R2wJY4D0YOfP\nRW2vNlBlQPlZ+Zha+oHd4cQeP9Aoj3eWnpViWvjsNMw3KPUyA7yfhptCut2KcrJz\nAZ+N6QNQvBOjmrYMULbaFD/jtTuY6nhwX/U/SRz10QKBgQDPuuLtrjZa5FzHPhxY\n4K7t8bzk0p72PaCxxdS5VEzUQfNCn+k/x8mKJNMQHYH8fDQNdG+ra5KYf4OaoMPO\nTPHFE8umBcvYNjZn/EQwf0AytIsbVb9VD2iliJmiZwE1uJpo2wr2RNRIRi3/3k+t\nfggBepoH/7vDArwaySaJXWsnQwKBgQDIqiUfc18W2AoKpBYtqN1ya2YfckGXpV85\nJjhQs3kIykyG1pD4Zxp1IvUJvOE2uYTfKmNbCV0bXkLz9aoCcMQOYfc+ZBaoOmap\n1sWwO62vlIQCoo5bm6kE7sqhKFOTkSJgENl6J+XTkOQ456TLkfbGabUC648vYaNG\nVzRJZKO4iQKBgQCUJMHFo6Jb+9Q2u5LXx5S5WNbPkW2QSq8ZWO62JOqNzWLAtu5P\ncBnJDS4ApiqXd7RfjBQ/ef4YB4hBdDlwHOunEtD/W87eKPtv+TZgJ8AO6TbzjZlf\n/hcxRlPav/7a4wYrlVsh+kAyMuqHOXI1VlY7R8YlwjmTf5XKvH1hJWBPpQKBgDmU\nyW5K9wBhIhCHoW2cxV7t/rILYVMYu0h09TgDKDojgu42aAc/3tG6JEKVFrNTbRN0\n4GnhN/yAggnrdsuYfEn8Rqx6oB3KFGesH7JAjciSf4caCmuzMT8fHro8Di+MOCcE\n7sMk68hYDYVew2U/D2dEMhMScVYRWH74yyI8ZNaxAoGBAIBgTWETy3ySSVENfH0s\nbPMm6YPMAFTc6NqjFsoLQfe06ZmeN3UvmaZ6MEP6W9UBL85vY5xKBO5fbuDqU0L0\npZmkW+VLTf7WtxKJVKp3iwVZDjJJvVfzBbmNfaenQbJhX5cNJGp9C2sBLwJEViQ8\n4KdX/ruQ3W3hf19ctVryWMUf\n-----END PRIVATE KEY-----\n",
    "client_email": "controlill-app@controlill.iam.gserviceaccount.com",
    "client_id": "109675994830086481265",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/controlill-app%40controlill.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

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


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()


def _agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


_sh = None

def _get_sheet():
    global _sh
    if _sh is None:
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(_CREDS_DICT, scopes=_SCOPES)
        gc = gspread.authorize(creds)
        _sh = gc.open_by_key(SHEET_ID)
    return _sh


def _get_aba(nome):
    try:
        return _get_sheet().worksheet(nome)
    except Exception:
        return None


def _garantir_aba(nome, header):
    sh = _get_sheet()
    try:
        ws = sh.worksheet(nome)
        if not ws.row_values(1):
            ws.append_row(header)
        return ws
    except Exception:
        ws = sh.add_worksheet(title=nome, rows=2000, cols=len(header))
        ws.append_row(header)
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
    ws.append_row([novo_id, setor,"","","","","","",usuario,"",_agora(),"","aberto",_agora()])
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
            ws.update_cell(i, 10, "")
            break


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
            ws.update_cell(i, 10, usuario)
            break


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
