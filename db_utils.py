import json
import hashlib
import psycopg2
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ユーザーデータ設定
USER_DATA_PATH = Path(__file__).parent / "data" / "users_data.json"

# ユーザー認証関連関数
def load_users():
    try:
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ユーザーデータ読み込みエラー: {e}")
        return []

def authenticate_user(employee_code, password):
    users = load_users()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    for user in users:
        if (str(user["code"]) == str(employee_code) and 
            user["password"] == hashed_pw):
            return {
                "id": user["code"],
                "employee_code": user["code"],
                "name": user["name"],
                "depart": user["depart"],
                "admin": user.get("admin", False)
            }
    return None

# データベース接続設定
DB_HOST = os.getenv("DB_HOST", "ep-dawn-credit-a16vhe5b-pooler.ap-southeast-1.aws.neon.tech")
DB_NAME = os.getenv("DB_NAME", "neondb")
DB_USER = os.getenv("DB_USER", "neondb_owner")
DB_PASSWORD = os.getenv("DB_PASSWORD", "npg_E63kPJglOeih")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    投稿者ID VARCHAR(255),
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
                    report_id INTEGER,
                    投稿者ID VARCHAR(255),
                    コメント内容 TEXT,
                    投稿日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS notices (
                    id SERIAL PRIMARY KEY,
                    タイトル VARCHAR(255),
                    内容 TEXT,
                    日付 DATE,
                    対象ユーザーID VARCHAR(255),
                    既読 INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS weekly_schedules (
                    id SERIAL PRIMARY KEY,
                    投稿者ID VARCHAR(255),
                    開始日 DATE,
                    終了日 DATE,
                    月曜日 TEXT,
                    火曜日 TEXT,
                    水曜日 TEXT,
                    木曜日 TEXT,
                    金曜日 TEXT,
                    土曜日 TEXT,
                    日曜日 TEXT,
                    投稿日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS weekly_schedule_comments (
                    id SERIAL PRIMARY KEY,
                    weekly_schedule_id INTEGER,
                    投稿者ID VARCHAR(255),
                    コメント内容 TEXT,
                    投稿日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# 日報関連関数
def save_report(report):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reports (
                    投稿者ID, 実行日, カテゴリ, 場所, 
                    実施内容, 所感, 画像パス
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                report["投稿者ID"],
                report["実行日"],
                report["カテゴリ"],
                report["場所"],
                report["実施内容"],
                report["所感"],
                report.get("image_path")
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def load_reports():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.*, c.id AS comment_id, c.コメント内容, 
                       c.投稿日時 AS comment_date, c.投稿者ID AS comment_author
                FROM reports r
                LEFT JOIN comments c ON r.id = c.report_id
                ORDER BY r.投稿日時 DESC
            """)
            rows = cur.fetchall()
            
            reports = {}
            users = {user["code"]: user["name"] for user in load_users()}
            
            for row in rows:
                report_id = row[0]
                if report_id not in reports:
                    reports[report_id] = {
                        "id": report_id,
                        "投稿者ID": row[1],
                        "投稿者名": users.get(row[1], "不明"),
                        "実行日": str(row[2]),
                        "カテゴリ": row[3],
                        "場所": row[4],
                        "実施内容": row[5],
                        "所感": row[6],
                        "画像パス": row[7],
                        "投稿日時": row[8].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
                        "いいね": row[9],
                        "ナイスファイト": row[10],
                        "コメント": []
                    }
                
                if row[11]:  # コメントがある場合
                    reports[report_id]["コメント"].append({
                        "id": row[11],
                        "内容": row[12],
                        "投稿日時": row[13].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
                        "投稿者名": users.get(row[14], "不明")
                    })
            
            return list(reports.values())
    finally:
        conn.close()

def edit_report(report):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE reports SET
                    実行日 = %s,
                    場所 = %s,
                    カテゴリ = %s,
                    実施内容 = %s,
                    所感 = %s
                WHERE id = %s
            """, (
                report["実行日"],
                report["場所"],
                report["カテゴリ"],
                report["実施内容"],
                report["所感"],
                report["id"]
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_report(report_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_reaction(report_id, reaction_type):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if reaction_type == "いいね":
                cur.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = %s", (report_id,))
            elif reaction_type == "ナイスファイト":
                cur.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = %s", (report_id,))
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# コメント関連関数
def save_comment(report_id, user_id, comment_content):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO comments (
                    report_id, 投稿者ID, コメント内容
                ) VALUES (%s, %s, %s)
            """, (report_id, user_id, comment_content))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def load_commented_reports(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT r.* 
                FROM reports r
                JOIN comments c ON r.id = c.report_id
                WHERE c.投稿者ID = %s
                ORDER BY r.投稿日時 DESC
            """, (user_id,))
            
            users = {user["code"]: user["name"] for user in load_users()}
            return [{
                "id": row[0],
                "投稿者ID": row[1],
                "投稿者名": users.get(row[1], "不明"),
                "実行日": str(row[2]),
                "カテゴリ": row[3],
                "場所": row[4],
                "実施内容": row[5],
                "所感": row[6],
                "投稿日時": row[8].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
            } for row in cur.fetchall()]
    finally:
        conn.close()

# 週間予定関連関数
def save_weekly_schedule(schedule):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO weekly_schedules (
                    投稿者ID, 開始日, 終了日, 
                    月曜日, 火曜日, 水曜日, 
                    木曜日, 金曜日, 土曜日, 日曜日
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                schedule["投稿者ID"],
                schedule["開始日"],
                schedule["終了日"],
                schedule["月曜日"],
                schedule["火曜日"],
                schedule["水曜日"],
                schedule["木曜日"],
                schedule["金曜日"],
                schedule["土曜日"],
                schedule["日曜日"]
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def load_weekly_schedules():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM weekly_schedules
                ORDER BY 投稿日時 DESC
            """)
            
            users = {user["code"]: user["name"] for user in load_users()}
            return [{
                "id": row[0],
                "投稿者ID": row[1],
                "投稿者名": users.get(row[1], "不明"),
                "開始日": str(row[2]),
                "終了日": str(row[3]),
                "月曜日": row[4],
                "火曜日": row[5],
                "水曜日": row[6],
                "木曜日": row[7],
                "金曜日": row[8],
                "土曜日": row[9],
                "日曜日": row[10],
                "投稿日時": row[11].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
            } for row in cur.fetchall()]
    finally:
        conn.close()

def save_weekly_schedule_comment(weekly_schedule_id, user_id, comment_content):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO weekly_schedule_comments (
                    weekly_schedule_id, 投稿者ID, コメント内容
                ) VALUES (%s, %s, %s)
            """, (weekly_schedule_id, user_id, comment_content))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# お知らせ関連関数
def load_notices(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM notices
                WHERE 対象ユーザーID = %s
                ORDER BY 日付 DESC
            """, (user_id,))
            return [{
                "id": row[0],
                "タイトル": row[1],
                "内容": row[2],
                "日付": str(row[3]),
                "対象ユーザーID": row[4],
                "既読": row[5]
            } for row in cur.fetchall()]
    finally:
        conn.close()

def mark_notice_as_read(notice_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE notices SET 既読 = 1
                WHERE id = %s
            """, (notice_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
