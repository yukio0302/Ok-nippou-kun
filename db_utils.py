import sqlite3
import json
import os

DB_FILE = "reports.db"

# ✅ データベース初期化
def init_db(keep_existing=False):
    """
    データベースを初期化する関数。
    keep_existing: True の場合、既存のデータを保持する。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if not keep_existing:
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
                コメント TEXT,
                画像 BLOB
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
    print("✅ データベースの初期化が完了しました（既存データ保持：", keep_existing, "）")

# ✅ ユーザー認証
def authenticate_user(employee_code, password):
    """
    ユーザーを認証する関数。
    """
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
    """
    日報を保存する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, コメント, 画像)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["投稿者"],
            report["実行日"],
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            json.dumps(report.get("コメント", [])),
            report.get("画像")
        ))
        conn.commit()
        print("✅ 日報が正常に保存されました。")
    except Exception as e:
        print(f"❌ 日報の保存中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 日報を取得
def load_reports():
    """
    日報を取得する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM reports ORDER BY 実行日 DESC")
        rows = cursor.fetchall()
        return [
            (
                row[0], row[1], row[2], row[3], row[4],
                row[5], row[6], row[7], row[8], json.loads(row[9]) if row[9] else [],
                row[10]  # 画像データ
            )
            for row in rows
        ]
    except Exception as e:
        print(f"❌ レポートの取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()

# ✅ 投稿を編集
def edit_report(report):
    """
    投稿を編集する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE reports
            SET カテゴリ = ?, 場所 = ?, 実施内容 = ?, 所感 = ?, 画像 = ?
            WHERE id = ?
        """, (
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            report["画像"],
            report["id"]
        ))
        conn.commit()
        print(f"✅ 日報 (ID: {report['id']}) を編集しました。")
    except Exception as e:
        print(f"❌ 日報編集中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 投稿を削除
def delete_report(report_id):
    """
    投稿を削除する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
        print(f"✅ 日報 (ID: {report_id}) を削除しました。")
    except Exception as e:
        print(f"❌ 日報削除中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ コメントを追加
def add_comment(report_id, comment):
    """
    コメントを追加する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT コメント FROM reports WHERE id = ?", (report_id,))
        current_comments = cursor.fetchone()
        current_comments = json.loads(current_comments[0]) if current_comments and current_comments[0] else []
        
        current_comments.append(comment)
        cursor.execute("UPDATE reports SET コメント = ? WHERE id = ?", (json.dumps(current_comments), report_id))
        conn.commit()
    except Exception as e:
        print(f"❌ コメント追加エラー: {e}")
    finally:
        conn.close()

# ✅ お知らせを取得
def load_notices():
    """
    お知らせを取得する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM notices ORDER BY 日付 DESC")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print(f"❌ お知らせの取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()

# ✅ お知らせを既読にする
def mark_notice_as_read(notice_id):
    """
    お知らせを既読にする関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,))
        conn.commit()
        print(f"✅ お知らせ (ID: {notice_id}) を既読にしました。")
    except Exception as e:
        print(f"❌ お知らせの既読処理中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ いいね！とナイスファイト！を更新
def update_likes(report_id, action):
    """
    いいね！やナイスファイトを更新する関数。
    """
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
