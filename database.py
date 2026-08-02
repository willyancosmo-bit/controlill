"""
database.py — Control.ILL v3.4
Banco: Supabase PostgreSQL (não pausa, dados persistentes)
"""
import hashlib
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "controlill.db"

# ── Credenciais Supabase ──────────────────────────────────────────────────────
_SUPA = dict(
    host="db.ghaedvzvmwsmqeurqtoi.supabase.co",
    database="postgres",
    user="postgres",
    password="YJrXPxkr.M?65a?",
    port=5432,
    sslmode="require",
    connect_timeout=15,
)


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()


def _conn():
    try:
        import psycopg2, psycopg2.extras
        con = psycopg2.connect(**_SUPA,
                               cursor_factory=psycopg2.extras.RealDictCursor)
        return con, "pg"
    except Exception:
        import sqlite3
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con, "sq"


def _q(sql: str, modo: str) -> str:
    return sql if modo == "pg" else sql.replace("%s", "?")


def _run(sql: str, params=(), fetch="all"):
    con, modo = _conn()
    try:
        if modo == "pg":
            cur = con.cursor()
            s = _q(sql, modo)
            if fetch == "id" and "RETURNING" not in s.upper():
                s = s.rstrip(";") + " RETURNING id"
            cur.execute(s, params)
            con.commit()
            if fetch == "all":
                rows = cur.fetchall()
                return [dict(r) for r in rows] if rows else []
            elif fetch == "one":
                r = cur.fetchone()
                return dict(r) if r else None
            elif fetch == "id":
                r = cur.fetchone()
                return r["id"] if r else 0
            return None
        else:
            cur = con.execute(_q(sql, modo), params)
            con.commit()
            if fetch == "all":
                rows = cur.fetchall()
                return [dict(r) for r in rows] if rows else []
            elif fetch == "one":
                r = cur.fetchone()
                return dict(r) if r else None
            elif fetch == "id":
                return cur.lastrowid
            return None
    finally:
        con.close()


def _insert(sql: str, params=()):
    return _run(sql, params, fetch="id")


# ── Keep-alive ────────────────────────────────────────────────────────────────
_keepalive_started = False

def _keepalive_loop():
    while True:
        time.sleep(240)
        try:
            _run("SELECT 1", fetch="one")
        except Exception:
            pass

def _start_keepalive():
    global _keepalive_started
    if not _keepalive_started:
        _keepalive_started = True
        t = threading.Thread(target=_keepalive_loop, daemon=True)
        t.start()


# ── INIT ──────────────────────────────────────────────────────────────────────
def init_db():
    con, modo = _conn()
    try:
        if modo == "pg":
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    login TEXT NOT NULL UNIQUE,
                    senha_hash TEXT NOT NULL,
                    perfil TEXT NOT NULL DEFAULT 'analista',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT DEFAULT to_char(now(),'DD/MM/YYYY HH24:MI:SS')
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS lotes (
                    id SERIAL PRIMARY KEY,
                    setor TEXT NOT NULL,
                    nome_exame TEXT, fabricante TEXT, lote_reagente TEXT,
                    validade TEXT, cod_validacao TEXT, responsavel TEXT,
                    aberto_por TEXT, fechado_por TEXT,
                    dt_abertura TEXT DEFAULT to_char(now(),'DD/MM/YYYY HH24:MI:SS'),
                    dt_fechamento TEXT,
                    status TEXT DEFAULT 'aberto',
                    criado_em TEXT DEFAULT to_char(now(),'DD/MM/YYYY HH24:MI:SS')
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS amostras (
                    id SERIAL PRIMARY KEY,
                    lote_id INTEGER NOT NULL REFERENCES lotes(id),
                    amostra TEXT NOT NULL,
                    inserido_por TEXT,
                    inserido_em TEXT DEFAULT to_char(now(),'DD/MM/YYYY HH24:MI:SS'),
                    UNIQUE(lote_id, amostra)
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS log_atividades (
                    id SERIAL PRIMARY KEY,
                    usuario TEXT, acao TEXT, detalhe TEXT,
                    criado_em TEXT DEFAULT to_char(now(),'DD/MM/YYYY HH24:MI:SS')
                )""")
            con.commit()
            cur.execute("SELECT COUNT(*) as n FROM usuarios")
            if cur.fetchone()["n"] == 0:
                cur.execute(
                    "INSERT INTO usuarios (nome,login,senha_hash,perfil) "
                    "VALUES (%s,%s,%s,%s)",
                    ("Administrador", "admin", _hash("admin123"), "admin"))
                con.commit()
        else:
            con.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL, login TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL, perfil TEXT NOT NULL DEFAULT 'analista',
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now','localtime')));
            CREATE TABLE IF NOT EXISTS lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, setor TEXT NOT NULL,
                nome_exame TEXT, fabricante TEXT, lote_reagente TEXT,
                validade TEXT, cod_validacao TEXT, responsavel TEXT,
                aberto_por TEXT, fechado_por TEXT,
                dt_abertura TEXT DEFAULT (strftime('%d/%m/%Y %H:%M:%S','now','localtime')),
                dt_fechamento TEXT, status TEXT DEFAULT 'aberto',
                criado_em TEXT DEFAULT (datetime('now','localtime')));
            CREATE TABLE IF NOT EXISTS amostras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER NOT NULL REFERENCES lotes(id),
                amostra TEXT NOT NULL, inserido_por TEXT,
                inserido_em TEXT DEFAULT (strftime('%d/%m/%Y %H:%M:%S','now','localtime')),
                UNIQUE(lote_id, amostra));
            CREATE TABLE IF NOT EXISTS log_atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT, acao TEXT, detalhe TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime')));
            """)
            con.commit()
            n = con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
            if n == 0:
                con.execute(
                    "INSERT INTO usuarios (nome,login,senha_hash,perfil) VALUES (?,?,?,?)",
                    ("Administrador", "admin", _hash("admin123"), "admin"))
                con.commit()
            existing = {r[1] for r in con.execute("PRAGMA table_info(lotes)").fetchall()}
            for col in ["aberto_por", "fechado_por"]:
                if col not in existing:
                    con.execute(f"ALTER TABLE lotes ADD COLUMN {col} TEXT")
            existing_am = {r[1] for r in con.execute("PRAGMA table_info(amostras)").fetchall()}
            if "inserido_por" not in existing_am:
                con.execute("ALTER TABLE amostras ADD COLUMN inserido_por TEXT")
            con.commit()
    finally:
        con.close()
    _start_keepalive()


# ── USUÁRIOS ──────────────────────────────────────────────────────────────────
def autenticar(login, senha):
    return _run(
        "SELECT * FROM usuarios WHERE login=%s AND senha_hash=%s AND ativo=1",
        (login.strip().lower(), _hash(senha)), fetch="one")

def get_todos_usuarios():
    return _run("SELECT id,nome,login,perfil,ativo,criado_em FROM usuarios ORDER BY nome")

def criar_usuario(nome, login, senha, perfil="analista"):
    try:
        _insert("INSERT INTO usuarios (nome,login,senha_hash,perfil) VALUES (%s,%s,%s,%s)",
                (nome.strip(), login.strip().lower(), _hash(senha), perfil))
        return True, "Usuário criado com sucesso."
    except Exception:
        return False, f"Login '{login}' já existe."

def alterar_senha_usuario(login, senha_nova):
    _run("UPDATE usuarios SET senha_hash=%s WHERE login=%s",
         (_hash(senha_nova), login.strip().lower()), fetch="none")

def toggle_usuario(usuario_id, ativo):
    _run("UPDATE usuarios SET ativo=%s WHERE id=%s",
         (1 if ativo else 0, usuario_id), fetch="none")


# ── LOG ───────────────────────────────────────────────────────────────────────
def registrar_log(usuario, acao, detalhe=""):
    try:
        _insert("INSERT INTO log_atividades (usuario,acao,detalhe) VALUES (%s,%s,%s)",
                (usuario, acao, detalhe))
    except Exception:
        pass

def get_log(limite=200):
    return _run(
        "SELECT criado_em,usuario,acao,detalhe FROM log_atividades ORDER BY id DESC LIMIT %s",
        (limite,))


# ── LOTES ─────────────────────────────────────────────────────────────────────
def criar_lote(setor, usuario=""):
    return _insert("INSERT INTO lotes (setor,aberto_por) VALUES (%s,%s)", (setor, usuario))

def get_lote(lote_id):
    r = _run("SELECT * FROM lotes WHERE id=%s", (lote_id,), fetch="one")
    if r:
        cnt = _run("SELECT COUNT(*) as n FROM amostras WHERE lote_id=%s", (lote_id,), fetch="one")
        r["total_amostras"] = cnt["n"] if cnt else 0
    return r

def get_lotes_por_setor(setor, apenas_abertos=True):
    if apenas_abertos:
        rows = _run("SELECT * FROM lotes WHERE setor=%s AND status='aberto' ORDER BY criado_em DESC", (setor,))
    else:
        rows = _run("SELECT * FROM lotes WHERE setor=%s ORDER BY criado_em DESC", (setor,))
    for r in rows:
        cnt = _run("SELECT COUNT(*) as n FROM amostras WHERE lote_id=%s", (r["id"],), fetch="one")
        r["total_amostras"] = cnt["n"] if cnt else 0
    return rows

def contar_lotes_fechados_setor(setor):
    r = _run("SELECT COUNT(*) as n FROM lotes WHERE setor=%s AND status='fechado'", (setor,), fetch="one")
    return r["n"] if r else 0

def reabrir_lote(lote_id, usuario=""):
    _run("UPDATE lotes SET status='aberto',dt_fechamento=NULL,fechado_por=NULL WHERE id=%s",
         (lote_id,), fetch="none")

def get_todos_lotes_abertos():
    return _run("SELECT * FROM lotes WHERE status='aberto'")

def atualizar_lote(lote_id, nome_exame=None, fabricante=None, lote_reagente=None,
                   validade=None, cod_validacao=None, responsavel=None):
    _run("""UPDATE lotes SET nome_exame=%s,fabricante=%s,lote_reagente=%s,
            validade=%s,cod_validacao=%s,responsavel=%s WHERE id=%s""",
         (nome_exame,fabricante,lote_reagente,validade,cod_validacao,responsavel,lote_id),
         fetch="none")

def fechar_lote(lote_id, dt_fechamento, usuario=""):
    _run("UPDATE lotes SET status='fechado',dt_fechamento=%s,fechado_por=%s WHERE id=%s",
         (dt_fechamento, usuario, lote_id), fetch="none")


# ── AMOSTRAS ──────────────────────────────────────────────────────────────────
def inserir_amostra(lote_id, amostra, usuario=""):
    try:
        _insert("INSERT INTO amostras (lote_id,amostra,inserido_por) VALUES (%s,%s,%s)",
                (lote_id, amostra.strip(), usuario))
        return True
    except Exception:
        return False

def get_amostras(lote_id):
    rows = _run(
        "SELECT amostra,inserido_em,inserido_por FROM amostras WHERE lote_id=%s ORDER BY inserido_em",
        (lote_id,))
    return [(r["amostra"], r.get("inserido_em",""), r.get("inserido_por","")) for r in rows]
