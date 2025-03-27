import sqlite3
from datetime import datetime
import json
import os
import base64
import streamlit as st

DB_PATH = "/mount/src/ok-nippou-kun/data/reports.db"
IMAGE_DIR = "/mount/src/ok-nippou-kun/images"  # 画像保存ディレクトリ

def init_db(keep_existing=True):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # users テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        社員コード TEXT UNIQUE,
        パスワード TEXT,
        名前 TEXT,
        部署 TEXT
    )
    """)

    # posts テーブル (共通フィールド)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        投稿者ID INTEGER,
        投稿日時 TEXT,
        FOREIGN KEY (投稿者ID) REFERENCES users (id)
    )
    """)

    # reports テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        postId INTEGER,
        実行日 TEXT,
        カテゴリ TEXT,
        場所 TEXT,
        実施内容 TEXT,
        所感 TEXT,
        いいね INTEGER DEFAULT 0,
        ナイスファイト INTEGER DEFAULT 0,
        画像パス TEXT,
        FOREIGN KEY (postId) REFERENCES posts (id)
    )
    """)

    # notices テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        タイトル TEXT,
        内容 TEXT,
        日付 TEXT,
        対象ユーザーID INTEGER,
        既読 INTEGER DEFAULT 0,
        FOREIGN KEY (対象ユーザーID) REFERENCES users (id)
    )
    """)

    # weekly_schedules テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS weekly_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        postId INTEGER,
        開始日 TEXT,
        終了日 TEXT,
        月曜日 TEXT,
        火曜日 TEXT,
        水曜日 TEXT,
        木曜日 TEXT,
        金曜日 TEXT,
        土曜日 TEXT,
        日曜日 TEXT,
        FOREIGN KEY (postId) REFERENCES posts (id)
    )
    """)

    # comments テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        postId INTEGER,
        投稿者ID INTEGER,
        コメント内容 TEXT,
        投稿日時 TEXT,
        FOREIGN KEY (postId) REFERENCES posts (id),
        FOREIGN KEY (投稿者ID) REFERENCES users (id)
    )
    """)

    conn.commit()
    conn.close()

def authenticate_user(employee_code, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE 社員コード = ? AND パスワード = ?", (employee_code, password))
    user = cur.fetchone()
    conn.close()
    if user:
        return {
            "id": user[0],
            "employee_code": user[1],
            "password": user[2],
            "name": user[3],
            "depart": json.loads(user[4])
        }
    return None

def save_report(report):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        # posts テーブルに投稿情報を追加
        cur.execute("INSERT INTO posts (投稿者ID, 投稿日時) VALUES (?, ?)",
                    (report["投稿者ID"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        postId = cur.lastrowid

        # 画像をファイルに保存
        image_path = None
        if report["image"]:
            image_filename = f"report_{postId}.png"
            image_path = os.path.join(IMAGE_DIR, image_filename)
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(report["image"]))

        # reports テーブルに日報情報を追加
        cur.execute("""
            INSERT INTO reports (postId, 実行日, カテゴリ, 場所, 実施内容, 所感, 画像パス)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (postId, report["実行日"], report["カテゴリ"], report["場所"], report["実施内容"], report["所感"], image_path))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"日報保存エラー: {e}")
    finally:
        conn.close()

def load_reports():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT reports.*, posts.投稿者ID, posts.投稿日時, users.名前
        FROM reports
        JOIN posts ON reports.postId = posts.id
        JOIN users ON posts.投稿者ID = users.id
        ORDER BY posts.投稿日時 DESC
    """)
    reports = []
    for row in cur.fetchall():
        reports.append({
            "id": row[0],
            "postId": row[1],
            "実行日": row[2],
            "カテゴリ": row[3],
            "場所": row[4],
            "実施内容": row[5],
            "所感": row[6],
            "いいね": row[7],
            "ナイスファイト": row[8],
            "画像パス": row[9],
            "投稿者ID": row[10],
            "投稿日時": row[11],
            "投稿者": row[12],
            "コメント": load_comments(row[0])  # コメントも取得
        })
    conn.close()
    return reports

def load_comments(report_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT comments.*, users.名前
        FROM comments
        JOIN users ON comments.投稿者ID = users.id
        WHERE comments.postId = ?
        ORDER BY comments.投稿日時 ASC
    """, (report_id,))
    comments = []
    for row in cur.fetchall():
        comments.append({
            "id": row[0],
            "postId": row[1],
            "投稿者ID": row[2],
            "コメント内容": row[3],
            "投稿日時": row[4],
            "投稿者": row[5]
        })
    conn.close()
    return comments

def load_notices(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT notices.*, users.名前
        FROM notices
        JOIN users ON notices.対象ユーザーID = users.id
        WHERE notices.対象ユーザーID = ?
        ORDER BY notices.日付 DESC
    """, (user_id,))
    notices = []
    for row in cur.fetchall():
        notices.append({
            "id": row[0],
            "タイトル": row[1],
            "内容": row[2],
            "日付": row[3],
            "対象ユーザーID": row[4],
            "既読": row[5],
            "投稿者": row[6]
        })
    conn.close()
    return notices

def mark_notice_as_read(notice_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id)
    except Exception as e:
        conn.rollback()
        print(f"お知らせ既読処理エラー: {e}")
    finally:
        conn.close()

def edit_report(report):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE reports SET 実行日 = ?, カテゴリ = ?, 場所 = ?, 実施内容 = ?, 所感 = ?
            WHERE id = ?
        """, (report["実行日"], report["カテゴリ"], report["場所"], report["実施内容"], report["所感"], report["id"]))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"日報編集エラー: {e}")
    finally:
        conn.close()

def delete_report(report_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"日報削除エラー: {e}")
    finally:
        conn.close()

def update_reaction(report_id, reaction_type):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        if reaction_type == "いいね":
            cur.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = ?", (report_id,))
        elif reaction_type == "ナイスファイト":
            cur.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = ?", (report_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"リアクション更新エラー: {e}")
    finally:
        conn.close()

def save_comment(report_id, user_id, comment_text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO comments (postId, 投稿者ID, コメント内容, 投稿日時) VALUES (?, ?, ?, ?)",
                    (report_id, user_id, comment_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"コメント保存エラー: {e}")
    finally:
        conn.close()

def load_commented_reports(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT reports.*, posts.投稿者ID, posts.投稿日時, users.名前
        FROM reports
        JOIN posts ON reports.postId = posts.id
        JOIN users ON posts.投稿者ID = users.id
        WHERE reports.id IN (SELECT postId FROM comments WHERE 投稿者ID = ?)
        ORDER BY posts.投稿日時 DESC
    """, (user_id,))
    reports = []
    for row in cur.fetchall():
        reports.append({
            "id": row[0],
            "postId": row[1],
            "実行日": row[2],
            "カテゴリ": row[3],
            "場所": row[4],
            "実施内容": row[5],
            "所感": row[6],
            "いいね": row[7],
            "ナイスファイト": row[8],
            "画像パス": row[9],
            "投稿者ID": row[10],
            "投稿日時": row[11],
            "投稿者": row[12],
            "コメント": load_comments(row[0])  # コメントも取得
        })
    conn.close()
    return reports

def save_weekly_schedule_comment(schedule_id, user_id, comment_text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO comments (postId, 投稿者ID, コメント内容, 投稿日時) VALUES (?, ?, ?, ?)",
                    (schedule_id, user_id, comment_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"週間予定コメント保存エラー: {e}")
    finally:
        conn.close()

def add_comments_column():
    """weekly_schedules テーブルにコメントカラムを追加 (既存のテーブルにカラムを追加する場合は ALTER TABLE を使用)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント TEXT DEFAULT '[]'")
        conn.commit()
        print("コメントカラムを追加しました！")
    except sqlite3.OperationalError:
        print("コメントカラムは既に追加されています。") # テーブルが存在しない場合のエラーをキャッチ
    except Exception as e:
        print(f"コメントカラム追加エラー: {e}")
    finally:
        conn.close()
