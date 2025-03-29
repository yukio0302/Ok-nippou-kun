import os
import json
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta
from dotenv import load_dotenv

# データベース接続情報（Neon.tech の情報に更新）
DB_HOST = "ep-dawn-credit-a16vhe5b-pooler.ap-southeast-1.aws.neon.tech"
DB_NAME = "neondb"
DB_USER = "neondb_owner"
DB_PASSWORD = "npg_E63kPJglOeih"
DB_PORT = "5432"

# データベース接続関数
def get_db_connection():
    conn = psycopg2.connect(
        host="ep-dawn-credit-a16vhe5b-pooler.ap-southeast-1.aws.neon.tech",
        database="neondb",
        user="neondb_owner",
        password="npg_E63kPJglOeih",
        port=5432
    )
    return conn

# テーブル作成関数（PostgreSQL に合わせて修正）
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            社員コード VARCHAR(255) UNIQUE,
            パスワード VARCHAR(255),
            名前 VARCHAR(255),
            部署 VARCHAR(255)
        );

        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            投稿者ID INTEGER REFERENCES users(id),
            投稿日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            投稿者ID INTEGER REFERENCES users(id),
            実行日 DATE,
            カテゴリ VARCHAR(255),
            場所 VARCHAR(255),
            実施内容 TEXT,
            所感 TEXT,
            画像パス VARCHAR(255),
            投稿日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            report_id INTEGER REFERENCES reports(id),
            投稿者ID INTEGER REFERENCES users(id),
            コメント内容 TEXT,
            投稿日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            タイトル VARCHAR(255),
            内容 TEXT,
            日付 DATE,
            対象ユーザーID INTEGER REFERENCES users(id),
            既読 INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS weekly_schedules (
            id SERIAL PRIMARY KEY,
            postId INTEGER REFERENCES posts(id),
            開始日 DATE,
            終了日 DATE,
            月曜日 TEXT,
            火曜日 TEXT,
            水曜日 TEXT,
            木曜日 TEXT,
            金曜日 TEXT,
            土曜日 TEXT,
            日曜日 TEXT
        );

        CREATE TABLE IF NOT EXISTS weekly_schedule_comments (
            id SERIAL PRIMARY KEY,
            weekly_schedule_id INTEGER REFERENCES weekly_schedules(id),
            投稿者ID INTEGER REFERENCES users(id),
            コメント内容 TEXT,
            投稿日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

# ユーザー認証関数
def authenticate_user(employee_code, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE 社員コード = %s AND パスワード = %s", (employee_code, password))
    user = cur.fetchone()
    conn.close()
    if user:
        return {
            "id": user[0],
            "employee_code": user[1],
            "name": user[3],
            "depart": user[4].split(",") if user[4] else []
        }
    return None

# 日報保存関数
def save_report(report):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports (投稿者ID, 実行日, カテゴリ, 場所, 実施内容, 所感, 画像パス)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        report["投稿者ID"], report["実行日"], report["カテゴリ"], report["場所"], report["実施内容"], report["所感"], report.get("image")
    ))
    conn.commit()
    conn.close()

# 日報読み込み関数
def load_reports():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT reports.*, users.名前, comments.コメント内容, comments.投稿日時 AS コメント投稿日時, comments.投稿者ID AS コメント投稿者ID, comment_users.名前 AS コメント投稿者名
        FROM reports
        JOIN users ON reports.投稿者ID = users.id
        LEFT JOIN comments ON reports.id = comments.report_id
        LEFT JOIN users AS comment_users ON comments.投稿者ID = comment_users.id
        ORDER BY reports.投稿日時 DESC
    """)
    rows = cur.fetchall()
    conn.close()
    reports = {}
    for row in rows:
        report_id = row[0]
        if report_id not in reports:
            reports[report_id] = {
                "id": report_id,
                "投稿者ID": row[1],
                "実行日": str(row[2]),
                "カテゴリ": row[3],
                "場所": row[4],
                "実施内容": row[5],
                "所感": row[6],
                "画像パス": row[7],
                "投稿日時": str(row[8]),
                "いいね": row[9],
                "ナイスファイト": row[10],
                "投稿者": row[11],
                "コメント": []
            }
        if row[12]:
            reports[report_id]["コメント"].append({
                "コメント内容": row[12],
                "投稿日時": str(row[13]),
                "投稿者": row[14]
            })
    return list(reports.values())

# お知らせ読み込み関数
def load_notices(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices WHERE 対象ユーザーID = %s ORDER BY 日付 DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{
        "id": row[0],
        "タイトル": row[1],
        "内容": row[2],
        "日付": str(row[3]),
        "対象ユーザーID": row[4],
        "既読": row[5]
    } for row in rows]

# お知らせ既読関数
def mark_notice_as_read(notice_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE notices SET 既読 = 1 WHERE id = %s", (notice_id,))
    conn.commit()
    conn.close()

# 日報編集関数
def edit_report(report):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE reports SET 実行日 = %s, 場所 = %s, カテゴリ = %s, 実施内容 = %s, 所感 = %s
        WHERE id = %s
    """, (report["実行日"], report["場所"], report["カテゴリ"], report["実施内容"], report["所感"], report["id"]))
    conn.commit()
    conn.close()

# 日報削除関数
def delete_report(report_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
    conn.commit()
    conn.close()

# リアクション更新関数
def update_reaction(report_id, reaction_type):
    conn = get_db_connection()
    cur = conn.cursor()
    if reaction_type == "いいね":
        cur.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = %s", (report_id,))
    elif reaction_type == "ナイスファイト":
        cur.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = %s", (report_id,))
    conn.commit()
    conn.close()

# コメント保存関数
def save_comment(report_id, user_id, comment_content):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO comments (report_id, 投稿者ID, コメント内容, 投稿ID, コメント内容, 投稿日時)
        VALUES (%s, %s, %s, NOW())
    """, (report_id, user_id, comment_content))
    conn.commit()
    conn.close()

# コメント投稿された日報読み込み関数
def load_commented_reports(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT reports.*, users.名前
        FROM reports
        JOIN comments ON reports.id = comments.report_id
        JOIN users ON reports.投稿者ID = users.id
        WHERE comments.投稿者ID = %s
        ORDER BY comments.投稿日時 DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{
        "id": row[0],
        "投稿者ID": row[1],
        "実行日": str(row[2]),
        "カテゴリ": row[3],
        "場所": row[4],
        "実施内容": row[5],
        "所感": row[6],
        "画像パス": row[7],
        "投稿日時": str(row[8]),
        "いいね": row[9],
        "ナイスファイト": row[10],
        "投稿者": row[11],
        "コメント": []
    } for row in rows]

# 週間予定コメント保存関数
def save_weekly_schedule_comment(weekly_schedule_id, user_id, comment_content):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO weekly_schedule_comments (weekly_schedule_id, 投稿者ID, コメント内容, 投稿日時) VALUES (%s, %s, %s, NOW())", (weekly_schedule_id, user_id, comment_content))
    conn.commit()
    conn.close()

# 週間予定読み込み関数
def load_weekly_schedules():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT weekly_schedules.*, posts.投稿者ID, posts.投稿日時, users.名前
        FROM weekly_schedules
        JOIN posts ON weekly_schedules.postId = posts.id
        JOIN users ON posts.投稿者ID = users.id
        ORDER BY posts.投稿日時 DESC
    """)
    rows = cur.fetchall()
    conn.close()
    schedules = []
    for row in rows:
        schedules.append({
            "id": row[0], "postId": row[1], "開始日": str(row[2]), "終了日": str(row[3]), 
            "月曜日": row[4], "火曜日": row[5], "水曜日": row[6], 
            "木曜日": row[7], "金曜日": row[8], "土曜日": row[9], 
            "日曜日": row[10], "投稿者ID": row[11], "投稿日時": str(row[12]), "投稿者": row[13],
            "コメント": load_comments(row[0])  # コメントも取得
        })
    return schedules

# コメント読み込み関数
def load_comments(report_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT comments.*, users.名前
        FROM comments
        JOIN users ON comments.投稿者ID = users.id
        WHERE comments.report_id = %s
        ORDER BY comments.投稿日時 ASC
    """, (report_id,))
    rows = cur.fetchall()
    conn.close()
    return [{
        "投稿者": row[4],
        "投稿日時": str(row[3]),
        "コメント内容": row[2]
    } for row in rows]
