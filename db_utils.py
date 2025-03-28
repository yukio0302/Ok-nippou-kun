import psycopg2
import json
import os
from datetime import datetime, timedelta
import streamlit as st

# Neonデータベース接続情報
DB_HOST = "ep-dawn-credit-a16vhe5b-pooler.ap-southeast-1.aws.neon.tech"
DB_NAME = "neondb"
DB_USER = "neondb_owner"
DB_PASSWORD = "npg_E63kPJglOeih"
DB_PORT = "5432"

def get_db_connection():
    """データベース接続を確立"""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode='require'
    )

def authenticate_user(employee_code, password):
    """ユーザー認証（users_data.jsonを使用）"""
    USER_FILE = "data/users_data.json"
    
    if not os.path.exists(USER_FILE):
        return None

    try:
        with open(USER_FILE, "r", encoding="utf-8-sig") as file:
            users = json.load(file)

        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user
    except Exception as e:
        st.error(f"認証エラー: {str(e)}")
    return None

def init_db(keep_existing=True):
    """データベースの初期化（テーブル作成）"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if not keep_existing:
            cur.execute("DROP TABLE IF EXISTS reports CASCADE")
            cur.execute("DROP TABLE IF EXISTS notices CASCADE")
            cur.execute("DROP TABLE IF EXISTS weekly_schedules CASCADE")

        # 日報テーブル
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            投稿者 TEXT NOT NULL,
            実行日 DATE NOT NULL,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INT DEFAULT 0,
            ナイスファイト INT DEFAULT 0,
            コメント JSONB DEFAULT '[]'::jsonb,
            画像 TEXT,
            投稿日時 TIMESTAMP NOT NULL
        )
        """)

        # お知らせテーブル
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            タイトル TEXT NOT NULL,
            内容 TEXT,
            日付 DATE NOT NULL,
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
            投稿日時 TIMESTAMP NOT NULL,
            コメント JSONB DEFAULT '[]'::jsonb
        )
        """)

        conn.commit()
        st.success("データベース初期化が完了しました")
    except psycopg2.Error as e:
        st.error(f"データベースエラー: {e}")
        raise
    finally:
        if conn:
            conn.close()

def save_report(report):
    """日報を保存"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        report["投稿日時"] = datetime.now() + timedelta(hours=9)
        if not report.get("実行日"):
            report["実行日"] = report["投稿日時"].date()

        cur.execute("""
        INSERT INTO reports (
            投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, 
            いいね, ナイスファイト, コメント, 画像, 投稿日時
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            report["投稿者"],
            report["実行日"],
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            0,  # いいね初期値
            0,  # ナイスファイト初期値
            json.dumps([]),
            report.get("image"),
            report["投稿日時"]
        ))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"保存エラー: {e}")
        raise
    finally:
        if conn:
            conn.close()

def load_reports():
    """日報を読み込み"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT id, 投稿者, 実行日::text, カテゴリ, 場所, 実施内容, 所感,
               いいね, ナイスファイト, コメント, 画像, 投稿日時::text
        FROM reports 
        ORDER BY 投稿日時 DESC
        """)
        return [{
            "id": row[0],
            "投稿者": row[1],
            "実行日": row[2],
            "カテゴリ": row[3],
            "場所": row[4],
            "実施内容": row[5],
            "所感": row[6],
            "いいね": row[7],
            "ナイスファイト": row[8],
            "コメント": json.loads(row[9]),
            "image": row[10],
            "投稿日時": row[11]
        } for row in cur.fetchall()]
    except psycopg2.Error as e:
        st.error(f"読み込みエラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 続く...
def update_reaction(report_id, reaction_type):
    """リアクション更新"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        column = "いいね" if reaction_type == "いいね" else "ナイスファイト"
        cur.execute(f"""
            UPDATE reports 
            SET {column} = {column} + 1 
            WHERE id = %s
        """, (report_id,))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"リアクション更新エラー: {e}")
    finally:
        if conn:
            conn.close()

def save_comment(report_id, commenter, comment):
    """コメントを保存"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 既存コメント取得
        cur.execute("""
        SELECT 投稿者, コメント 
        FROM reports 
        WHERE id = %s
        FOR UPDATE
        """, (report_id,))
        result = cur.fetchone()
        
        if not result:
            raise ValueError("投稿が見つかりません")

        original_poster = result[0]
        comments = json.loads(result[1]) if result[1] else []

        # 新規コメント追加
        new_comment = {
            "投稿者": commenter,
            "日時": (datetime.now() + timedelta(hours=9)).isoformat(),
            "コメント": comment
        }
        comments.append(new_comment)

        # コメント更新
        cur.execute("""
        UPDATE reports 
        SET コメント = %s 
        WHERE id = %s
        """, (json.dumps(comments, ensure_ascii=False), report_id))

        # 通知作成（投稿者≠コメント者の場合）
        if commenter != original_poster:
            cur.execute("""
            INSERT INTO notices (
                タイトル, 内容, 日付, 対象ユーザー
            ) VALUES (%s, %s, %s, %s)
            """, (
                "新しいコメント",
                f"{commenter}さんがコメントしました: {comment}",
                datetime.now().date(),
                original_poster
            ))

        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"コメント保存エラー: {e}")
        raise
    finally:
        if conn:
            conn.close()

def load_notices(user_name):
    """お知らせ取得"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT id, タイトル, 内容, 日付::text, 既読 
        FROM notices 
        WHERE 対象ユーザー = %s 
        ORDER BY 日付 DESC
        """, (user_name,))
        return [{
            "id": row[0],
            "タイトル": row[1],
            "内容": row[2],
            "日付": row[3],
            "既読": row[4]
        } for row in cur.fetchall()]
    except psycopg2.Error as e:
        st.error(f"お知らせ取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 続く...
def save_weekly_schedule(schedule):
    """週間予定を保存"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        schedule["投稿日時"] = datetime.now() + timedelta(hours=9)
        
        cur.execute("""
        INSERT INTO weekly_schedules (
            投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 
            木曜日, 金曜日, 土曜日, 日曜日, 投稿日時
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            schedule["投稿者"],
            schedule["開始日"],
            schedule["終了日"],
            schedule.get("月曜日", ""),
            schedule.get("火曜日", ""),
            schedule.get("水曜日", ""),
            schedule.get("木曜日", ""),
            schedule.get("金曜日", ""),
            schedule.get("土曜日", ""),
            schedule.get("日曜日", ""),
            schedule["投稿日時"]
        ))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"週間予定保存エラー: {e}")
        raise
    finally:
        if conn:
            conn.close()

def load_weekly_schedules():
    """週間予定を取得"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT id, 投稿者, 開始日::text, 終了日::text, 
               月曜日, 火曜日, 水曜日, 木曜日, 
               金曜日, 土曜日, 日曜日, 投稿日時::text, コメント 
        FROM weekly_schedules 
        ORDER BY 投稿日時 DESC
        """)
        return [{
            "id": row[0],
            "投稿者": row[1],
            "開始日": row[2],
            "終了日": row[3],
            "月曜日": row[4],
            "火曜日": row[5],
            "水曜日": row[6],
            "木曜日": row[7],
            "金曜日": row[8],
            "土曜日": row[9],
            "日曜日": row[10],
            "投稿日時": row[11],
            "コメント": json.loads(row[12]) if row[12] else []
        } for row in cur.fetchall()]
    except psycopg2.Error as e:
        st.error(f"週間予定取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 他の関数も同様にPostgreSQL用に修正...
def delete_report(report_id):
    """投稿を削除"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        conn.commit()
        return cur.rowcount > 0
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"削除エラー: {e}")
        return False
    finally:
        if conn:
            conn.close()

def edit_report(report_id, new_date, new_location, new_content, new_remarks):
    """投稿を編集"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE reports
            SET 実行日 = %s,
                場所 = %s,
                実施内容 = %s,
                所感 = %s
            WHERE id = %s
        """, (new_date, new_location, new_content, new_remarks, report_id))
        conn.commit()
        return cur.rowcount > 0
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"編集エラー: {e}")
        return False
    finally:
        if conn:
            conn.close()

def save_weekly_schedule_comment(schedule_id, commenter, comment):
    """週間予定へのコメント保存"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
        SELECT 投稿者, コメント 
        FROM weekly_schedules 
        WHERE id = %s
        FOR UPDATE
        """, (schedule_id,))
        result = cur.fetchone()
        
        if not result:
            raise ValueError("週間予定が見つかりません")

        original_poster = result[0]
        comments = json.loads(result[1]) if result[1] else []

        new_comment = {
            "投稿者": commenter,
            "日時": (datetime.now() + timedelta(hours=9)).isoformat(),
            "コメント": comment
        }
        comments.append(new_comment)

        cur.execute("""
        UPDATE weekly_schedules 
        SET コメント = %s 
        WHERE id = %s
        """, (json.dumps(comments, ensure_ascii=False), schedule_id))

        if commenter != original_poster:
            cur.execute("""
            INSERT INTO notices (
                タイトル, 内容, 日付, 対象ユーザー
            ) VALUES (%s, %s, %s, %s)
            """, (
                "週間予定へのコメント",
                f"{commenter}さんがコメントしました: {comment}",
                datetime.now().date(),
                original_poster
            ))

        conn.commit()
        return True
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"週間予定コメント保存エラー: {e}")
        return False
    finally:
        if conn:
            conn.close()

def mark_notice_as_read(notice_id):
    """お知らせを既読にする"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE notices
            SET 既読 = TRUE
            WHERE id = %s
        """, (notice_id,))
        conn.commit()
        return cur.rowcount > 0
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"既読更新エラー: {e}")
        return False
    finally:
        if conn:
            conn.close()

def load_commented_reports(commenter_name):
    """コメントした投稿を取得"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*,
                   c.comment_data->>'日時' as comment_time
            FROM reports r,
                 jsonb_array_elements(r.コメント) AS c(comment_data)
            WHERE c.comment_data->>'投稿者' = %s
            ORDER BY comment_time DESC
        """, (commenter_name,))
        
        reports = []
        for row in cur.fetchall():
            reports.append({
                "id": row[0],
                "投稿者": row[1],
                "実行日": row[2].strftime("%Y-%m-%d"),
                "カテゴリ": row[3],
                "場所": row[4],
                "実施内容": row[5],
                "所感": row[6],
                "いいね": row[7],
                "ナイスファイト": row[8],
                "コメント": json.loads(row[9]),
                "image": row[10],
                "投稿日時": row[11].strftime("%Y-%m-%d %H:%M:%S"),
                "コメント日時": row[12]
            })
        return reports
    except psycopg2.Error as e:
        st.error(f"コメント投稿取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_db_schema():
    """データベーススキーマの更新"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 対象ユーザーカラムの存在チェック
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='notices' AND column_name='対象ユーザー'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE notices ADD COLUMN 対象ユーザー TEXT")
            conn.commit()

        # 週間予定コメントカラムの存在チェック
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='weekly_schedules' AND column_name='コメント'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント JSONB DEFAULT '[]'::jsonb")
            conn.commit()

    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"スキーマ更新エラー: {e}")
    finally:
        if conn:
            conn.close()

# アプリ起動時にスキーマ更新を実行
update_db_schema()
