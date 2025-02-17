import sqlite3
import json
import os

DB_FILE = "reports.db"

# ✅ データベース初期化
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # reports テーブル作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT NOT NULL,
            実行日 TEXT NOT NULL,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT
        )
    """)

    # notices テーブル作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            内容 TEXT NOT NULL,
            タイトル TEXT,
            日付 TEXT,
            既読 INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("✅ データベースの初期化が完了しました。")

# ✅ ユーザー認証
def authenticate_user(employee_code, password):
    try:
        with open("users_data.json", "r", encoding="utf-8-sig") as file:
            users = json.load(file)
        
        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user  # ログイン成功

        return None  # ログイン失敗
    except Exception as e:
        print(f"❌ ユーザー認証エラー: {e}")
        return None

# ✅ 日報を保存
def save_report(report):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, コメント)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            report["投稿者"],
            report["実行日"],
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            json.dumps(report.get("コメント", []))
        ))
        conn.commit()
    except Exception as e:
        print(f"❌ 日報の保存中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 日報を取得（辞書形式に修正）
def load_reports():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM reports ORDER BY 実行日 DESC")
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "投稿者": row[1],
                "実行日": row[2],
                "カテゴリ": row[3],
                "場所": row[4],
                "実施内容": row[5],
                "所感": row[6],
                "いいね": row[7],
                "ナイスファイト": row[8],
                "コメント": json.loads(row[9]) if row[9] else []
            }
            for row in rows
        ]
    except Exception as e:
        print(f"❌ レポートの取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()

# ✅ いいね！とナイスファイト！のカウント更新
def update_likes(report_id, action):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        if action == "like":
            cursor.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = ?", (report_id,))
        elif action == "nice":
            cursor.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = ?", (report_id,))
        conn.commit()
    except Exception as e:
        print(f"❌ いいね/ナイスファイトの更新エラー: {e}")
    finally:
        conn.close()
