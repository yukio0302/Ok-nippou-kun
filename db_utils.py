import json
import sqlite3
import shutil
from datetime import datetime

# ファイルパス
USER_DATA_FILE = "users_data.json"
REPORTS_FILE = "reports.json"
REPORTS_BACKUP_FILE = "reports_backup.json"
NOTICE_FILE = "notices.json"
DB_FILE = "reports.db"

# ✅ SQLite 初期化
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT,
            投稿者部署 TEXT,
            投稿日時 TEXT,
            カテゴリ TEXT,
            タグ TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# ✅ データの読み込み（JSON用）
def load_json(file_path, default_data):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data.copy()

# ✅ データの保存（JSON用・バックアップあり）
def save_json(file_path, data):
    if not data:
        return

    # ⏪ バックアップ作成
    shutil.copy(file_path, REPORTS_BACKUP_FILE)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ✅ SQLite に投稿を保存
def save_to_db(report):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (投稿者, 投稿者部署, 投稿日時, カテゴリ, タグ, 実施内容, 所感, いいね, ナイスファイト)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report["投稿者"], ", ".join(report["投稿者部署"]), report["投稿日時"], report["カテゴリ"], 
          ", ".join(report["タグ"]), report["実施内容"], report["所感・備考"], 0, 0))
    conn.commit()
    conn.close()

# ✅ SQLite から投稿を取得
def load_from_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
