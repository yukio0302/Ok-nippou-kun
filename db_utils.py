import sqlite3
import json
from datetime import datetime

DB_FILE = "reports.db"  # データベースファイル名

# ✅ データベース初期化（画像カラム削除 & 投稿日時追加）
def init_db(keep_existing=True):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT NOT NULL,
            実行日 TEXT NOT NULL,
            投稿日時 TEXT NOT NULL,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT DEFAULT '[]'  -- JSON文字列として初期化
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

# ✅ ユーザー認証
def authenticate_user(employee_code, password):
    try:
        with open("users_data.json", "r", encoding="utf-8-sig") as file:
            users = json.load(file)
        
        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user  # ログイン成功
        return None  # ログイン失敗
    except FileNotFoundError:
        print("❌ ユーザーデータファイルが見つかりません。")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ ユーザーデータのJSON解析エラー: {e}")
        return None
    except Exception as e:
        print(f"❌ ユーザー認証エラー: {e}")
        return None

# ✅ 日報を保存（投稿日時を追加）
def save_report(report):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reports (投稿者, 実行日, 投稿日時, カテゴリ, 場所, 実施内容, 所感, コメント)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["投稿者"],
            report["実行日"],
            report["投稿日時"],  # 新しく追加
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            json.dumps(report.get("コメント", []))  # コメントを JSON 形式で保存
        ))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ 日報の保存中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 日報を取得（投稿日時も取得）
def load_reports():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, 投稿者, 実行日, 投稿日時, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント FROM reports ORDER BY 投稿日時 DESC")
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "投稿者": row[1],
                "実行日": row[2],
                "投稿日時": row[3],  # 投稿日時を追加
                "カテゴリ": row[4],
                "場所": row[5],
                "実施内容": row[6],
                "所感": row[7],
                "いいね": row[8],
                "ナイスファイト": row[9],
                "コメント": json.loads(row[10]) if row[10] else []  # JSON 形式のコメントをリストに変換
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"❌ 日報の取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()

# ✅ コメントを保存
def save_comment(report_id, comment):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # 既存のコメントを取得
        cursor.execute("SELECT コメント FROM reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        if row:
            comments = json.loads(row[0]) if row[0] else []
            comments.append(comment)

            # 更新
            cursor.execute("UPDATE reports SET コメント = ? WHERE id = ?", (json.dumps(comments), report_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"❌ コメントの保存中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ お知らせを取得
def load_notices():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM notices ORDER BY 日付 DESC")
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "内容": row[1],
                "タイトル": row[2],
                "日付": row[3],
                "既読": row[4]
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"❌ お知らせ取得中にエラーが発生しました: {e}")
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
    except sqlite3.Error as e:
        print(f"❌ お知らせ既読処理中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 日報を削除
def delete_report(report_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ 日報削除中にエラーが発生しました: {e}")
    finally:
        conn.close()
