import sqlite3
import json
from datetime import datetime

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

# ✅ 投稿を保存
def save_report(report):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report["投稿者"], report["実行日"], report["カテゴリ"], report["場所"],
          report["実施内容"], report["所感"], 0, 0, json.dumps(report["コメント"])))

    conn.commit()
    conn.close()

# ✅ 投稿データを取得
def load_reports():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
