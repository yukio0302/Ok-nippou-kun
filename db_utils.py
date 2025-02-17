import sqlite3
import json
from datetime import datetime

# JSONファイルのパス
USER_DATA_FILE = "users_data.json"
DB_FILE = "reports.db"

# ✅ SQLite 初期化
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 📜 投稿データ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT,
            実行日 TEXT,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT
        )
    """)

    # 🔔 お知らせデータ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT,
            内容 TEXT,
            既読 INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

# ✅ ユーザーデータを読み込む（`users_data.json`）
def load_users():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# ✅ ユーザー認証（ログイン）
def authenticate_user(employee_code, password):
    users = load_users()
    for user in users:
        if user["code"] == employee_code and user["password"] == password:
            return user  # ユーザー情報を返す（ログイン成功）
    return None  # ログイン失敗

# ✅ お知らせデータを取得
def load_notices():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notices ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
