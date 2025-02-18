import sqlite3
import json
import os

DB_FILE = "reports.db"

# ✅ データベース初期化
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
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

# ✅ 日報を保存（修正済み）
def save_report(report):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        print(f"📌 保存データ: {report}")  # デバッグ用
        cursor.execute("""
            INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.get("投稿者", "不明"),
            report.get("実行日", "未設定"),
            report.get("カテゴリ", ""),
            report.get("場所", ""),
            report.get("実施内容", ""),
            report.get("所感", ""),
            0,  # 初期値
            0,  # 初期値
            json.dumps(report.get("コメント", []))
        ))
        conn.commit()
        print("✅ 日報が正常に保存されました。")
    except Exception as e:
        print(f"❌ 日報の保存中にエラー: {e}")
    finally:
        conn.close()

# ✅ 日報を取得（修正済み）
def load_reports():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM reports ORDER BY 実行日 DESC")
        rows = cursor.fetchall()
        reports = []
        for row in rows:
            reports.append({
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
            })
        return reports
    except Exception as e:
        print(f"❌ レポート取得エラー: {e}")
        return []
    finally:
        conn.close()

# ✅ コメントを追加
def add_comment(report_id, comment):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT コメント FROM reports WHERE id = ?", (report_id,))
        current_comments = cursor.fetchone()
        current_comments = json.loads(current_comments[0]) if current_comments and current_comments[0] else []
        current_comments.append(comment)
        cursor.execute("UPDATE reports SET コメント = ? WHERE id = ?", (json.dumps(current_comments), report_id))
        conn.commit()
        print("✅ コメント追加成功")
    except Exception as e:
        print(f"❌ コメント追加エラー: {e}")
    finally:
        conn.close()

# ✅ いいね！とナイスファイト！を更新
def update_likes(report_id, action):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        if action == "like":
            cursor.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = ?", (report_id,))
        elif action == "nice":
            cursor.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = ?", (report_id,))
        conn.commit()
        print(f"✅ {action} が更新されました。")
    except Exception as e:
        print(f"❌ いいね/ナイスファイト更新エラー: {e}")
    finally:
        conn.close()

# ✅ お知らせを取得
def load_notices():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM notices ORDER BY 日付 DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ お知らせ取得エラー: {e}")
        return []
    finally:
        conn.close()

# ✅ お知らせを既読にする
def mark_notice_as_read(notice_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,))
        conn.commit()
        print(f"✅ お知らせ (ID: {notice_id}) を既読にしました。")
    except Exception as e:
        print(f"❌ お知らせ既読エラー: {e}")
    finally:
        conn.close()
