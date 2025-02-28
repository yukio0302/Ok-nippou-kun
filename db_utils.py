import sqlite3
import json
from datetime import datetime, timedelta

# ヘルパー関数: 現在時刻に9時間を加算する
def get_current_time():
    return datetime.now() + timedelta(hours=9)

DB_FILE = "reports.db"  # データベースファイル名

# ✅ データベース初期化（投稿日時カラムを含む）
def init_db(keep_existing=True):
    """データベースを初期化する。既存データを維持するか選択可能。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT NOT NULL,
            実行日 TEXT NOT NULL,
            実施日 TEXT NOT NULL,
            投稿日時 TEXT NOT NULL,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT DEFAULT '[]'
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
    """社員コードとパスワードを照合し、認証されたユーザー情報を返す。"""
    try:
        with open("users_data.json", "r", encoding="utf-8-sig") as file:
            users = json.load(file)

        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user  # ログイン成功
        return None  # ログイン失敗
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ ユーザー認証エラー: {e}")
        return None

# ✅ 日報を保存
def save_report(report):
    """新しい日報をデータベースに保存する。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reports (投稿者, 実行日, 実施日, 投稿日時, カテゴリ, 場所, 実施内容, 所感, コメント)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["投稿者"],
            report["実行日"],
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),  # 投稿日時（UTC）
            report["実施日"],  # ✅ 実施日を追加
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            json.dumps(report.get("コメント", []))
        ))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ 日報保存エラー: {e}")
    finally:
        conn.close()

# ✅ 日報を取得
def load_reports():
    """全日報を取得し、投稿日時順（降順）で返す。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, 投稿者, 実行日, 投稿日時, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント
            FROM reports
            ORDER BY 投稿日時 DESC
        """)
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "投稿者": row[1],
                "実行日": row[2],
                "投稿日時": row[3],
                "カテゴリ": row[4],
                "場所": row[5],
                "実施内容": row[6],
                "所感": row[7],
                "いいね": row[8],
                "ナイスファイト": row[9],
                "コメント": json.loads(row[10]) if row[10] else []
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"❌ 日報取得エラー: {e}")
        return []
    finally:
        conn.close()

# ✅ 日報を編集（新規追加）
def edit_report(report_id, updated_report):
    """指定された日報を更新する。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE reports
            SET カテゴリ = ?, 場所 = ?, 実施内容 = ?, 所感 = ?
            WHERE id = ?
        """, (
            updated_report["カテゴリ"],
            updated_report["場所"],
            updated_report["実施内容"],
            updated_report["所感"],
            report_id
        ))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ 日報編集エラー: {e}")
    finally:
        conn.close()
# ✅ リアクション（いいね！ or ナイスファイト！）を更新
def update_reaction(report_id, reaction_type):
    """指定した投稿の「いいね！」または「ナイスファイト！」を1増やす"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        if reaction_type == "いいね":
            cursor.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = ?", (report_id,))
        elif reaction_type == "ナイスファイト":
            cursor.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = ?", (report_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ リアクション更新エラー: {e}")
    finally:
        conn.close()

# ✅ コメントを保存（日本時間に修正）
def save_comment(report_id, commenter, comment):
    """指定した投稿にコメントを追加（NULL対策 & エラーチェック強化）"""
    if not report_id or not commenter or not comment.strip():
        print(f"⚠️ コメント保存スキップ: report_id={report_id}, commenter={commenter}, comment={comment}")
        return  # 不正なデータなら保存しない

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT コメント FROM reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()

        # ✅ `None` の場合は空リストで初期化
        comments = json.loads(row[0]) if row and row[0] else []

        # ✅ 新しいコメントを追加（+9時間）
        comments.append({
            "投稿者": commenter,
            "コメント": comment.strip(),
            "日時": (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")  # ✅ 日本時間に修正！
        })

        cursor.execute("UPDATE reports SET コメント = ? WHERE id = ?", (json.dumps(comments), report_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ コメント保存エラー: {e}")
    finally:
        conn.close()


# ✅ お知らせを取得
def load_notices():
    """お知らせを取得し、新しい順に返す。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM notices ORDER BY 日付 DESC")
        rows = cursor.fetchall()
        return [
            {"id": row[0], "内容": row[1], "タイトル": row[2], "日付": row[3], "既読": row[4]}
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"❌ お知らせ取得エラー: {e}")
        return []
    finally:
        conn.close()

# ✅ お知らせを既読にする
def mark_notice_as_read(notice_id):
    """指定されたお知らせを既読にする。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ お知らせ既読処理エラー: {e}")
    finally:
        conn.close()

# ✅ 日報を削除
def delete_report(report_id):
    """指定された日報を削除する。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ 日報削除エラー: {e}")
    finally:
        conn.close()
