import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "controlill.db"


def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    with _conn() as con:
        con.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            login       TEXT NOT NULL UNIQUE,
            senha_hash  TEXT NOT NULL,
            perfil      TEXT NOT NULL DEFAULT 'analista',
            ativo       INTEGER NOT NULL DEFAULT 1,
            criado_em   TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS lotes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            setor           TEXT NOT NULL,
            nome_exame      TEXT,
            fabricante      TEXT,
            lote_reagente   TEXT,
            validade        TEXT,
            cod_validacao   TEXT,
            responsavel     TEXT,
            aberto_por      TEXT,
            fechado_por     TEXT,
            dt_abertura     TEXT DEFAULT (strftime('%d/%m/%Y %H:%M:%S','now','localtime')),
            dt_fechamento   TEXT,
            status          TEXT DEFAULT 'aberto',
            criado_em       TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS amostras (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id         INTEGER NOT NULL REFERENCES lotes(id),
            amostra         TEXT NOT NULL,
            inserido_por    TEXT,
            inserido_em     TEXT DEFAULT (strftime('%d/%m/%Y %H:%M:%S','now','localtime')),
            UNIQUE(lote_id, amostra)
        );

        CREATE TABLE IF NOT EXISTS log_atividades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario     TEXT,
            acao        TEXT,
            detalhe     TEXT,
            criado_em   TEXT DEFAULT (datetime('now','localtime'))
        );
        """)
        con.commit()

        # Criar admin padrão se não existir nenhum usuário
        n = con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if n == 0:
            con.execute(
                "INSERT INTO usuarios (nome, login, senha_hash, perfil) VALUES (?,?,?,?)",
                ("Administrador", "admin", _hash("admin123"), "admin")
            )
            con.commit()

        # Migrar banco antigo: adicionar colunas novas se não existirem
        existing = {r[1] for r in con.execute("PRAGMA table_info(lotes)").fetchall()}
        for col, definition in [("aberto_por", "TEXT"), ("fechado_por", "TEXT")]:
            if col not in existing:
                con.execute(f"ALTER TABLE lotes ADD COLUMN {col} {definition}")
        existing_am = {r[1] for r in con.execute("PRAGMA table_info(amostras)").fetchall()}
        if "inserido_por" not in existing_am:
            con.execute("ALTER TABLE amostras ADD COLUMN inserido_por TEXT")
        con.commit()


# ─────────────────────────────────────────────────────────────────────────────
# USUÁRIOS
# ─────────────────────────────────────────────────────────────────────────────
def autenticar(login: str, senha: str):
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM usuarios WHERE login=? AND senha_hash=? AND ativo=1",
            (login.strip().lower(), _hash(senha))
        ).fetchone()
    return dict(row) if row else None


def get_todos_usuarios():
    with _conn() as con:
        rows = con.execute(
            "SELECT id, nome, login, perfil, ativo, criado_em FROM usuarios ORDER BY nome"
        ).fetchall()
    return [dict(r) for r in rows]


def criar_usuario(nome: str, login: str, senha: str, perfil: str = "analista") -> tuple:
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO usuarios (nome, login, senha_hash, perfil) VALUES (?,?,?,?)",
                (nome.strip(), login.strip().lower(), _hash(senha), perfil)
            )
            con.commit()
        return True, "Usuário criado com sucesso."
    except sqlite3.IntegrityError:
        return False, f"Login '{login}' já existe."


def alterar_senha_usuario(login: str, senha_nova: str):
    with _conn() as con:
        con.execute(
            "UPDATE usuarios SET senha_hash=? WHERE login=?",
            (_hash(senha_nova), login.strip().lower())
        )
        con.commit()


def toggle_usuario(usuario_id: int, ativo: bool):
    with _conn() as con:
        con.execute("UPDATE usuarios SET ativo=? WHERE id=?", (1 if ativo else 0, usuario_id))
        con.commit()


def alterar_perfil(usuario_id: int, perfil: str):
    with _conn() as con:
        con.execute("UPDATE usuarios SET perfil=? WHERE id=?", (perfil, usuario_id))
        con.commit()


# ─────────────────────────────────────────────────────────────────────────────
# LOG
# ─────────────────────────────────────────────────────────────────────────────
def registrar_log(usuario: str, acao: str, detalhe: str = ""):
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO log_atividades (usuario, acao, detalhe) VALUES (?,?,?)",
                (usuario, acao, detalhe)
            )
            con.commit()
    except Exception:
        pass


def get_log(limite: int = 200):
    with _conn() as con:
        rows = con.execute(
            "SELECT criado_em, usuario, acao, detalhe FROM log_atividades ORDER BY id DESC LIMIT ?",
            (limite,)
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# LOTES
# ─────────────────────────────────────────────────────────────────────────────
def criar_lote(setor: str, usuario: str = "") -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO lotes (setor, aberto_por) VALUES (?,?)", (setor, usuario)
        )
        con.commit()
        return cur.lastrowid


def get_lote(lote_id: int):
    with _conn() as con:
        row = con.execute("SELECT * FROM lotes WHERE id=?", (lote_id,)).fetchone()
        if row:
            d = dict(row)
            d["total_amostras"] = con.execute(
                "SELECT COUNT(*) FROM amostras WHERE lote_id=?", (lote_id,)
            ).fetchone()[0]
            return d
    return None


def get_lotes_por_setor(setor: str, apenas_abertos: bool = True):
    with _conn() as con:
        if apenas_abertos:
            rows = con.execute(
                "SELECT * FROM lotes WHERE setor=? AND status='aberto' ORDER BY criado_em DESC",
                (setor,)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM lotes WHERE setor=? ORDER BY criado_em DESC", (setor,)
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["total_amostras"] = con.execute(
                "SELECT COUNT(*) FROM amostras WHERE lote_id=?", (d["id"],)
            ).fetchone()[0]
            result.append(d)
        return result


def contar_lotes_fechados_setor(setor: str) -> int:
    with _conn() as con:
        return con.execute(
            "SELECT COUNT(*) FROM lotes WHERE setor=? AND status='fechado'", (setor,)
        ).fetchone()[0]


def reabrir_lote(lote_id: int, usuario: str = ""):
    with _conn() as con:
        con.execute(
            "UPDATE lotes SET status='aberto', dt_fechamento=NULL, fechado_por=NULL WHERE id=?",
            (lote_id,)
        )
        con.commit()


def get_todos_lotes_abertos():
    with _conn() as con:
        rows = con.execute("SELECT * FROM lotes WHERE status='aberto'").fetchall()
        return [dict(r) for r in rows]


def atualizar_lote(lote_id, nome_exame=None, fabricante=None, lote_reagente=None,
                   validade=None, cod_validacao=None, responsavel=None):
    with _conn() as con:
        con.execute("""
            UPDATE lotes SET
                nome_exame=?, fabricante=?, lote_reagente=?,
                validade=?, cod_validacao=?, responsavel=?
            WHERE id=?
        """, (nome_exame, fabricante, lote_reagente,
              validade, cod_validacao, responsavel, lote_id))
        con.commit()


def fechar_lote(lote_id: int, dt_fechamento: str, usuario: str = ""):
    with _conn() as con:
        con.execute(
            "UPDATE lotes SET status='fechado', dt_fechamento=?, fechado_por=? WHERE id=?",
            (dt_fechamento, usuario, lote_id)
        )
        con.commit()


# ─────────────────────────────────────────────────────────────────────────────
# AMOSTRAS
# ─────────────────────────────────────────────────────────────────────────────
def inserir_amostra(lote_id: int, amostra: str, usuario: str = "") -> bool:
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO amostras (lote_id, amostra, inserido_por) VALUES (?,?,?)",
                (lote_id, amostra.strip(), usuario)
            )
            con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_amostras(lote_id: int):
    with _conn() as con:
        rows = con.execute(
            "SELECT amostra, inserido_em, inserido_por FROM amostras WHERE lote_id=? ORDER BY inserido_em",
            (lote_id,)
        ).fetchall()
    return [tuple(r) for r in rows]
