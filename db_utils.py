import psycopg2
import json
import os
from datetime import datetime, timedelta
import streamlit as st
from psycopg2.extras import DictCursor

# データベース接続の最適化
@st.cache_data
def get_db_connection():
    try:
        conn = st.connection(
            name="neon",
            type="sql",
            url=st.secrets.connections.neon.url
        )
        return conn
    except Exception as e:
        print(f"⚠️ データベース接続エラー: {e}")
        raise

# データベース初期化の改善
def init_db(keep_existing=True):
    """データベースの初期化（テーブル作成）"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if not keep_existing:
        # 既存テーブルの削除
        for table in ["reports", "notices", "weekly_schedules"]:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table}")
            except Exception as e:
                print(f"⚠️ テーブル削除エラー: {e}")
    
    # テーブルの作成
    try:
        # 日報データのテーブル作成
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                投稿者 TEXT,
                実行日 TEXT,
                カテゴリ TEXT,
                場所 TEXT,
                実施内容 TEXT,
                所感 TEXT,
                いいね INTEGER DEFAULT 0,
                ナイスファイト INTEGER DEFAULT 0,
                コメント JSONB DEFAULT '[]'::JSONB,
                画像 TEXT,
                投稿日時 TIMESTAMP
            )
        """)
        
        # お知らせデータのテーブル作成
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                id SERIAL PRIMARY KEY,
                タイトル TEXT,
                内容 TEXT,
                日付 TIMESTAMP,
                既読 INTEGER DEFAULT 0,
                対象ユーザー TEXT
            )
        """)
        
        # 週間予定データのテーブル作成
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_schedules (
                id SERIAL PRIMARY KEY,
                投稿者 TEXT,
                開始日 TEXT,
                終了日 TEXT,
                月曜日 TEXT,
                火曜日 TEXT,
                水曜日 TEXT,
                木曜日 TEXT,
                金曜日 TEXT,
                土曜日 TEXT,
                日曜日 TEXT,
                投稿日時 TIMESTAMP,
                コメント JSONB DEFAULT '[]'::JSONB
            )
        """)
        
        conn.commit()
        print("✅ データベースを初期化しました！")
    except Exception as e:
        print(f"⚠️ データベース初期化エラー: {e}")
        raise
    finally:
        cur.close()

# ユーザー認証の改善
def authenticate_user(employee_code, password):
    """ユーザー認証（users_data.jsonを使用）"""
    USER_FILE = "data/users_data.json"
    
    try:
        if not os.path.exists(USER_FILE):
            return None
            
        with open(USER_FILE, "r", encoding="utf-8-sig") as file:
            users = json.load(file)
            
        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user
        return None
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ ユーザー認証ファイルの読み込みエラー")
        return None
    except Exception as e:
        print(f"⚠️ ユーザー認証エラー: {e}")
        return None

# データ保存の改善
def save_report(report):
    """日報をデータベースに保存"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        if '実行日' not in report or not report['実行日']:
            report['実行日'] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
        
        cur.execute("""
            INSERT INTO reports (
                投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, 
                いいね, ナイスファイト, コメント, 画像, 投稿日時
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            report["投稿者"], report["実行日"], report["カテゴリ"],
            report["場所"], report["実施内容"], report["所感"],
            0, 0, json.dumps([]), report.get("image"), report["投稿日時"]
        ))
        
        conn.commit()
        print(f"✅ 日報を保存しました！")
    except Exception as e:
        print(f"⚠️ データベースエラー: {e}")
        raise
    finally:
        cur.close()

# データ取得の最適化
@st.cache_data
def load_reports():
    """日報データを取得（最新の投稿順にソート）"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM reports 
            WHERE 投稿日時 >= (NOW() - INTERVAL '7 days')
            ORDER BY 投稿日時 DESC
            LIMIT 100
        """)
        
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"⚠️ データ取得エラー: {e}")
        return []
    finally:
        cur.close()

# コメント保存の改善
def save_comment(report_id, commenter, comment):
    """コメントを保存＆通知を追加"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        with conn:
            # コメントを保存
            cur.execute("""
                UPDATE reports 
                SET コメント = コメント || %s 
                WHERE id = %s
            """, (json.dumps([{
                "投稿者": commenter,
                "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "コメント": comment
            }]), report_id))
            
            # 通知を追加（必要な場合のみ）
            if should_notify(commenter):
                add_notification(report_id, commenter, comment)
                
    except Exception as e:
        print(f"⚠️ コメント保存エラー: {e}")
        raise
    finally:
        cur.close()

# お知らせ関連機能の改善
def load_notices(user_name):
    """お知らせデータを取得（対象ユーザーのみ）"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM notices 
            WHERE 対象ユーザー = %s 
            ORDER BY 日付 DESC
            LIMIT 100
        """, (user_name,))
        
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"⚠️ お知らせ取得エラー: {e}")
        return []
    finally:
        cur.close()

def mark_notice_as_read(notice_id):
    """お知らせを既読にする"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("UPDATE notices SET 既読 = 1 WHERE id = %s", (notice_id,))
        conn.commit()
    except Exception as e:
        print(f"⚠️ 既読更新エラー: {e}")
        raise
    finally:
        cur.close()

# 週間予定関連機能の改善
def save_weekly_schedule(schedule):
    """週間予定をデータベースに保存"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        with conn:
            # 投稿日時を JST で保存
            schedule["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
            
            cur.execute("""
                INSERT INTO weekly_schedules (
                    投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 
                    木曜日, 金曜日, 土曜日, 日曜日, 投稿日時
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                schedule["投稿者"], schedule["開始日"], schedule["終了日"],
                schedule["月曜日"], schedule["火曜日"], schedule["水曜日"],
                schedule["木曜日"], schedule["金曜日"], schedule["土曜日"],
                schedule["日曜日"], schedule["投稿日時"]
            ))
            
            print("✅ 週間予定を保存しました！")
    except Exception as e:
        print(f"⚠️ 週間予定の保存エラー: {e}")
        raise
    finally:
        cur.close()

# データベーススキーマの更新
def update_db_schema():
    """既存のデータベーススキーマを安全に更新"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # カラム存在チェック
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'notices'
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        if "対象ユーザー" not in columns:
            cur.execute("ALTER TABLE notices ADD COLUMN 対象ユーザー TEXT")
            conn.commit()
            print("✅ 対象ユーザーカラムを追加しました！")
    except Exception as e:
        print(f"⚠️ スキーマ更新エラー: {e}")
    finally:
        cur.close()
