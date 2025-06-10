import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"

def init_db():
    """Inicializa o banco de dados e a tabela de usuários."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

def hash_password(password: str) -> str:
    """Gera o hash de uma senha usando SHA256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def register_user(email: str, password: str) -> bool:
    """Registra um novo usuário no banco de dados."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Email já existe
    except Exception as e:
        print(f"Erro ao registrar usuário: {e}")
        return False
    finally:
        if conn:
            conn.close()

def authenticate_user(email: str, password: str) -> bool:
    """Autentica um usuário comparando o hash da senha."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        return row is not None and row[0] == hash_password(password)
    except Exception as e:
        print(f"Erro ao autenticar usuário: {e}")
        return False
    finally:
        if conn:
            conn.close()