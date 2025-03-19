import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = "/mount/src/ok-nippou-kun/Ok-nippou-kun/data/reports.db"

class DBManager:
    def __enter__(self):
        self.conn = sqlite3.connect(DB_PATH)
        return self.conn.cursor()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

def init_db(keep_existing=True):
    with DBManager() as cur:
        if not keep_existing:
            for table in ["reports", "notices", "weekly_schedules"]:
                cur.execute(f"DROP TABLE IF EXISTS {table}")
        
        tables = {
            "reports": """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    投稿者 TEXT, 実行日 TEXT, カテゴリ TEXT, 場所 TEXT,
                    実施内容 TEXT, 所感 TEXT, いいね INTEGER DEFAULT 0,
                    ナイスファイト INTEGER DEFAULT 0, コメント TEXT DEFAULT '[]',
                    画像 TEXT, 投稿日時 TEXT
                )""",
            "notices": """
                CREATE TABLE IF NOT EXISTS notices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    タイトル TEXT, 内容 TEXT, 日付 TEXT,
                    既読 INTEGER DEFAULT 0, 対象ユーザー TEXT
                )""",
            "weekly_schedules": """
                CREATE TABLE IF NOT EXISTS weekly_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    投稿者 TEXT, 開始日 TEXT, 終了日 TEXT,
                    月曜日 TEXT, 火曜日 TEXT, 水曜日 TEXT,
                    木曜日 TEXT, 金曜日 TEXT, 土曜日 TEXT,
                    日曜日 TEXT, 投稿日時 TEXT, コメント TEXT DEFAULT '[]'
                )"""
        }
        
        for table, schema in tables.items():
            cur.execute(schema)

def with_db(func):
    def wrapper(*args, **kwargs):
        with DBManager() as cur:
            return func(cur, *args, **kwargs)
    return wrapper

@with_db
def save_report(cur, report):
    report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, 画像, 投稿日時)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (report["投稿者"], report["実行日"], report["カテゴリ"], report["場所"],
          report["実施内容"], report["所感"], report.get("image"), report["投稿日時"]))

# 他のデータベース関数も同様にデコレータを使用して整理

def authenticate_user(employee_code, password):
    try:
        with open("data/users_data.json", "r", encoding="utf-8-sig") as f:
            users = json.load(f)
        return next((u for u in users if u["code"] == employee_code and u["password"] == password), None)
    except Exception as e:
        print(f"認証エラー: {e}")
        return None

# 他のヘルパー関数も同様に整理
