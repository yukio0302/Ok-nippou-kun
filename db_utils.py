import psycopg2
import os
from datetime import datetime, timezone, timedelta

# ユーザーデータ管理関数群
def load_users():
    """JSONファイルからユーザーデータを読み込む"""
    try:
        with open('data/users_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def hash_password(password):
    """パスワードをSHA-256でハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(employee_code, password):
    """JSONファイルからユーザーを認証"""
    users = load_users()
    hashed_pw = hash_password(password)
    
    for user in users:
        if user['社員コード'] == employee_code and user['パスワード'] == hashed_pw:
            return {
                "id": user['id'],
                "employee_code": user['社員コード'],
                "name": user['名前'],
                "depart": user['部署'].split(',') if user.get('部署') else []
            }
    return None
    
# 環境変数から取得
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
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def authenticate_user(employee_code, password):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE 社員コード = %s AND パスワード = %s", (employee_code, password))
            user = cur.fetchone()
            if user:
                return {
                    "id": user[0],
                    "employee_code": user[1],
                    "name": user[3],
                    "depart": user[4].split(",") if user[4] else []
                }
            return None
    finally:
        conn.close()

def save_report(report):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reports (投稿者ID, 実行日, カテゴリ, 場所, 実施内容, 所感, 画像パス)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                report["投稿者ID"], report["実行日"], report["カテゴリ"],
                report["場所"], report["実施内容"], report["所感"],
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
                SELECT reports.*, users.名前, comments.コメント内容,
                       comments.投稿日時 AS コメント投稿日時,
                       comments.投稿者ID AS コメント投稿者ID,
                       comment_users.名前 AS コメント投稿者名
                FROM reports
                JOIN users ON reports.投稿者ID = users.id
                LEFT JOIN comments ON reports.id = comments.report_id
                LEFT JOIN users AS comment_users ON comments.投稿者ID = comment_users.id
                ORDER BY reports.投稿日時 DESC
            """)
            rows = cur.fetchall()
            
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
                        "投稿日時": row[8].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
                        "いいね": row[9],
                        "ナイスファイト": row[10],
                        "投稿者": row[11],
                        "コメント": []
                    }
                if row[12]:
                    reports[report_id]["コメント"].append({
                        "コメント内容": row[12],
                        "投稿日時": row[13].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
                        "投稿者": row[15]
                    })
            return list(reports.values())
    finally:
        conn.close()

def load_notices(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM notices WHERE 対象ユーザーID = %s ORDER BY 日付 DESC", (user_id,))
            rows = cur.fetchall()
            return [{
                "id": row[0],
                "タイトル": row[1],
                "内容": row[2],
                "日付": str(row[3]),
                "対象ユーザーID": row[4],
                "既読": row[5]
            } for row in rows]
    finally:
        conn.close()

def mark_notice_as_read(notice_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE notices SET 既読 = 1 WHERE id = %s", (notice_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
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
                report["実行日"], report["場所"], report["カテゴリ"],
                report["実施内容"], report["所感"], report["id"]
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

def save_comment(report_id, user_id, comment_content):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO comments (report_id, 投稿者ID, コメント内容, 投稿日時)
                VALUES (%s, %s, %s, NOW())
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
                SELECT DISTINCT reports.*, users.名前
                FROM reports
                JOIN comments ON reports.id = comments.report_id
                JOIN users ON reports.投稿者ID = users.id
                WHERE comments.投稿者ID = %s
                ORDER BY reports.投稿日時 DESC
            """, (user_id,))
            rows = cur.fetchall()
            return [{
                "id": row[0],
                "投稿者ID": row[1],
                "実行日": str(row[2]),
                "カテゴリ": row[3],
                "場所": row[4],
                "実施内容": row[5],
                "所感": row[6],
                "画像パス": row[7],
                "投稿日時": row[8].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
                "いいね": row[9],
                "ナイスファイト": row[10],
                "投稿者": row[11]
            } for row in rows]
    finally:
        conn.close()

def save_weekly_schedule(schedule):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO posts (投稿者ID) VALUES (%s) RETURNING id
            """, (schedule["投稿者ID"],))
            post_id = cur.fetchone()[0]
            
            cur.execute("""
                INSERT INTO weekly_schedules (
                    postId, 開始日, 終了日,
                    月曜日, 火曜日, 水曜日,
                    木曜日, 金曜日, 土曜日, 日曜日
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                post_id, schedule["開始日"], schedule["終了日"],
                schedule["月曜日"], schedule["火曜日"], schedule["水曜日"],
                schedule["木曜日"], schedule["金曜日"], schedule["土曜日"], schedule["日曜日"]
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
                SELECT 
                    ws.*, p.投稿者ID, p.投稿日時,
                    u.名前
                FROM weekly_schedules ws
                JOIN posts p ON ws.postId = p.id
                JOIN users u ON p.投稿者ID = u.id
                ORDER BY p.投稿日時 DESC
            """)
            rows = cur.fetchall()
            return [{
                "id": row[0],
                "postId": row[1],
                "開始日": str(row[2]),
                "終了日": str(row[3]),
                "月曜日": row[4],
                "火曜日": row[5],
                "水曜日": row[6],
                "木曜日": row[7],
                "金曜日": row[8],
                "土曜日": row[9],
                "日曜日": row[10],
                "投稿者ID": row[11],
                "投稿日時": row[12].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
                "投稿者": row[13]
            } for row in rows]
    finally:
        conn.close()

def save_weekly_schedule_comment(weekly_schedule_id, user_id, comment_content):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO weekly_schedule_comments (
                    weekly_schedule_id, 投稿者ID, コメント内容, 投稿日時
                ) VALUES (%s, %s, %s, NOW())
            """, (weekly_schedule_id, user_id, comment_content))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def load_comments(report_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.*, u.名前
                FROM comments c
                JOIN users u ON c.投稿者ID = u.id
                WHERE c.report_id = %s
                ORDER BY c.投稿日時 ASC
            """, (report_id,))
            rows = cur.fetchall()
            return [{
                "id": row[0],
                "投稿者": row[5],
                "投稿日時": row[4].astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
                "コメント内容": row[3]
            } for row in rows]
    finally:
        conn.close()
