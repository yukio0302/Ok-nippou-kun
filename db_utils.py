import os
import json
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ✅ Neonデータベース接続
def get_db_connection():
    return psycopg2.connect(os.getenv("NEON_DB_URL"))

# ✅ ユーザー認証（変更なし）
def authenticate_user(employee_code, password):
    USER_FILE = "data/users_data.json"

    if not os.path.exists(USER_FILE):
        return None

    try:
        with open(USER_FILE, "r", encoding="utf-8-sig") as file:
            users = json.load(file)

        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return None

# ✅ テーブル初期化
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 日報テーブル
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            投稿者 TEXT NOT NULL,
            実行日 DATE NOT NULL,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT NOT NULL,
            所感 TEXT NOT NULL,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント JSONB DEFAULT '[]'::jsonb,
            画像 TEXT,
            投稿日時 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # お知らせテーブル
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            タイトル TEXT NOT NULL,
            内容 TEXT NOT NULL,
            日付 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            既読 BOOLEAN DEFAULT FALSE,
            対象ユーザー TEXT NOT NULL
        )
        """)
        
        # 週間予定テーブル
        cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_schedules (
            id SERIAL PRIMARY KEY,
            投稿者 TEXT NOT NULL,
            開始日 DATE NOT NULL,
            終了日 DATE NOT NULL,
            月曜日 TEXT,
            火曜日 TEXT,
            水曜日 TEXT,
            木曜日 TEXT,
            金曜日 TEXT,
            土曜日 TEXT,
            日曜日 TEXT,
            投稿日時 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            コメント JSONB DEFAULT '[]'::jsonb
        )
        """)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ✅ 日報保存
def save_report(report):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = sql.SQL("""
            INSERT INTO reports (
                投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, 画像
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)
        
        cur.execute(query, (
            report["投稿者"],
            report["実行日"],
            report.get("カテゴリ", ""),
            report.get("場所", ""),
            report["実施内容"],
            report["所感"],
            report.get("image")
        ))
        
        report_id = cur.fetchone()[0]
        conn.commit()
        return report_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ✅ 日報取得
def load_reports():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute("""
            SELECT *, 投稿日時 AT TIME ZONE 'Asia/Tokyo' as 投稿日時_jst 
            FROM reports 
            ORDER BY 投稿日時 DESC
        """)
        
        reports = []
        for row in cur.fetchall():
            report = dict(row)
            # JSONBの処理
            report["コメント"] = report["コメント"] if report["コメント"] else []
            report["投稿日時"] = report["投稿日時_jst"].replace(tzinfo=None)
            del report["投稿日時_jst"]
            reports.append(report)
        
        return reports
        
    except Exception as e:
        raise e
    finally:
        cur.close()
        conn.close()

# ✅ リアクション更新
def update_reaction(report_id, reaction_type):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        column = "いいね" if reaction_type == "いいね" else "ナイスファイト"
        query = sql.SQL("""
            UPDATE reports 
            SET {} = {} + 1 
            WHERE id = %s
        """).format(sql.Identifier(column), sql.Identifier(column))
        
        cur.execute(query, (report_id,))
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ✅ コメント保存
def save_comment(report_id, commenter, comment):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 日報情報取得
        cur.execute("""
            SELECT 投稿者, 実行日, 場所, 実施内容 
            FROM reports 
            WHERE id = %s
        """, (report_id,))
        result = cur.fetchone()
        
        if not result:
            return

        投稿者, 実行日, 場所, 実施内容 = result

        # コメント追加
        new_comment = {
            "投稿者": commenter,
            "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "コメント": comment
        }
        
        cur.execute("""
            UPDATE reports 
            SET コメント = コメント || %s::jsonb 
            WHERE id = %s
        """, (json.dumps([new_comment]), report_id))
        
        # 通知作成（投稿者と異なる場合）
        if 投稿者 != commenter:
            notification_content = f"""
【お知らせ】
{new_comment['日時']}

実施日: {実行日}
場所: {場所}
実施内容: {実施内容}

の投稿に {commenter} さんがコメントしました。
コメント内容: {comment}
            """
            
            cur.execute("""
                INSERT INTO notices (タイトル, 内容, 対象ユーザー)
                VALUES (%s, %s, %s)
            """, (
                "新しいコメントが届きました！",
                notification_content,
                投稿者
            ))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ✅ お知らせ処理
def load_notices(user_name):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute("""
            SELECT *, 日付 AT TIME ZONE 'Asia/Tokyo' as 日付_jst 
            FROM notices 
            WHERE 対象ユーザー = %s 
            ORDER BY 日付 DESC
        """, (user_name,))
        
        notices = []
        for row in cur.fetchall():
            notice = dict(row)
            notice["日付"] = notice["日付_jst"].replace(tzinfo=None)
            del notice["日付_jst"]
            notices.append(notice)
        
        return notices
        
    except Exception as e:
        raise e
    finally:
        cur.close()
        conn.close()

def mark_notice_as_read(notice_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE notices 
            SET 既読 = TRUE 
            WHERE id = %s
        """, (notice_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ✅ 週間予定関連
def save_weekly_schedule(schedule):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = sql.SQL("""
            INSERT INTO weekly_schedules (
                投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 
                木曜日, 金曜日, 土曜日, 日曜日
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)
        
        cur.execute(query, (
            schedule["投稿者"],
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
        
        schedule_id = cur.fetchone()[0]
        conn.commit()
        return schedule_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def load_weekly_schedules():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute("""
            SELECT *, 投稿日時 AT TIME ZONE 'Asia/Tokyo' as 投稿日時_jst 
            FROM weekly_schedules 
            ORDER BY 投稿日時 DESC
        """)
        
        schedules = []
        for row in cur.fetchall():
            schedule = dict(row)
            schedule["コメント"] = schedule["コメント"] if schedule["コメント"] else []
            schedule["投稿日時"] = schedule["投稿日時_jst"].replace(tzinfo=None)
            del schedule["投稿日時_jst"]
            schedules.append(schedule)
        
        return schedules
        
    except Exception as e:
        raise e
    finally:
        cur.close()
        conn.close()

def save_weekly_schedule_comment(schedule_id, commenter, comment):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # スケジュール情報取得
        cur.execute("""
            SELECT 投稿者, 開始日, 終了日 
            FROM weekly_schedules 
            WHERE id = %s
        """, (schedule_id,))
        result = cur.fetchone()
        
        if not result:
            return

        投稿者, 開始日, 終了日 = result

        # コメント追加
        new_comment = {
            "投稿者": commenter,
            "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "コメント": comment
        }
        
        cur.execute("""
            UPDATE weekly_schedules 
            SET コメント = コメント || %s::jsonb 
            WHERE id = %s
        """, (json.dumps([new_comment]), schedule_id))
        
        # 通知作成（投稿者と異なる場合）
        if 投稿者 != commenter:
            notification_content = f"""
【お知らせ】
{new_comment['日時']}

期間: {開始日} ～ {終了日}
の週間予定投稿に {commenter} さんがコメントしました。
コメント内容: {comment}
            """
            
            cur.execute("""
                INSERT INTO notices (タイトル, 内容, 対象ユーザー)
                VALUES (%s, %s, %s)
            """, (
                "新しいコメントが届きました！",
                notification_content,
                投稿者
            ))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# 初期化処理
init_db()
