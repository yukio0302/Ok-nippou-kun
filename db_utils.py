import sqlite3
import json
import os
from datetime import datetime, timedelta
import streamlit as st

# データベース設定
DB_PATH = "/mount/src/ok-nippou-kun/Ok-nippou-kun/data/reports.db"

# === ユーザー認証 ===
def authenticate_user(employee_code, password):
    """ユーザー認証（users_data.jsonを使用）"""
    try:
        with open("data/users_data.json", "r", encoding="utf-8-sig") as file:
            users = json.load(file)
        return next((u for u in users if u["code"] == employee_code and u["password"] == password), None)
    except Exception as e:
        st.error(f"認証エラー: {e}")
        return None

# === データベース初期化 ===
def init_db(keep_existing=True):
    """データベースの初期化（テーブル作成 + スキーマ更新）"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        
        if not keep_existing:
            cur.executescript("""
                DROP TABLE IF EXISTS reports;
                DROP TABLE IF EXISTS notices;
                DROP TABLE IF EXISTS weekly_schedules;
            """)

        # テーブル作成
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                投稿者 TEXT, 実行日 TEXT, カテゴリ TEXT, 場所 TEXT,
                実施内容 TEXT, 所感 TEXT, いいね INTEGER DEFAULT 0,
                ナイスファイト INTEGER DEFAULT 0, コメント TEXT DEFAULT '[]',
                画像 TEXT, 投稿日時 TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                タイトル TEXT, 内容 TEXT, 日付 TEXT,
                既読 INTEGER DEFAULT 0, 対象ユーザー TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                投稿者 TEXT, 開始日 TEXT, 終了日 TEXT,
                月曜日 TEXT, 火曜日 TEXT, 水曜日 TEXT, 木曜日 TEXT,
                金曜日 TEXT, 土曜日 TEXT, 日曜日 TEXT,
                投稿日時 TEXT, コメント TEXT DEFAULT '[]'
            )
        """)
        
        # スキーマ更新処理
        try:
            cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass

# === 共通コメント機能 ===
def handle_comment(item_type, item_id, commenter, comment):
    """コメント処理の共通ハンドラー"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            
            # 対象アイテムの情報取得
            if item_type == "report":
                query = "SELECT 投稿者, 実行日, 場所, 実施内容, コメント FROM reports WHERE id=?"
            else:
                query = "SELECT 投稿者, 開始日, 終了日, コメント FROM weekly_schedules WHERE id=?"
            
            cur.execute(query, (item_id,))
            result = cur.fetchone()
            
            if not result:
                return False

            # コメント情報更新
            comments = json.loads(result[-1]) if result[-1] else []
            new_comment = {
                "投稿者": commenter,
                "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "コメント": comment
            }
            comments.append(new_comment)
            
            # データベース更新
            update_query = f"""
                UPDATE {'reports' if item_type == 'report' else 'weekly_schedules'}
                SET コメント = ? WHERE id = ?
            """
            cur.execute(update_query, (json.dumps(comments), item_id))
            
            # 通知処理（自分以外へのコメントの場合）
            owner = result[0]
            if owner != commenter:
                # 通知内容生成
                if item_type == "report":
                    details = f"実施日: {result[1]}\n場所: {result[2]}\n内容: {result[3]}"
                else:
                    details = f"期間: {result[1]} ～ {result[2]}"
                
                notification = f"""
                    【{item_type.replace('report', '日報').replace('weekly', '週間予定')}コメント】
                    {new_comment['日時']}
                    {details}
                    {commenter}さんからのコメント:
                    {comment}
                """
                
                # 通知登録
                cur.execute("""
                    INSERT INTO notices (タイトル, 内容, 日付, 既読, 対象ユーザー)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    "新しいコメント",
                    notification.strip(),
                    new_comment['日時'],
                    0,
                    owner
                ))
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"コメント処理エラー: {e}")
        return False

# === データ取得 ===
def load_reports():
    """日報データ取得"""
    with sqlite3.connect(DB_PATH) as conn:
        return [dict(row) for row in conn.execute("""
            SELECT *, json_extract(コメント, '$') as コメント 
            FROM reports ORDER BY 投稿日時 DESC
        """)]

def load_weekly_schedules():
    """週間予定データ取得"""
    with sqlite3.connect(DB_PATH) as conn:
        return [dict(row) for row in conn.execute("""
            SELECT *, json_extract(コメント, '$') as コメント 
            FROM weekly_schedules ORDER BY 投稿日時 DESC
        """)]

# === その他の共通関数 ===
def update_reaction(item_type, item_id, reaction):
    """リアクション更新（日報専用）"""
    if item_type != "report":
        return
    
    with sqlite3.connect(DB_PATH) as conn:
        column = "いいね" if reaction == "like" else "ナイスファイト"
        conn.execute(f"""
            UPDATE reports 
            SET {column} = {column} + 1 
            WHERE id = ?
        """, (item_id,))

def get_comments(item_type, item_id):
    """コメント取得"""
    with sqlite3.connect(DB_PATH) as conn:
        table = "reports" if item_type == "report" else "weekly_schedules"
        result = conn.execute(f"""
            SELECT json_extract(コメント, '$') 
            FROM {table} WHERE id = ?
        """, (item_id,)).fetchone()
        return json.loads(result[0]) if result else []

# === 通知関連 ===
def load_notices(username):
    """ユーザー宛てのお知らせ取得"""
    with sqlite3.connect(DB_PATH) as conn:
        return [dict(row) for row in conn.execute("""
            SELECT * FROM notices 
            WHERE 対象ユーザー = ? 
            ORDER BY 日付 DESC
        """, (username,))]

def mark_notice_read(notice_id):
    """既読処理"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE notices 
            SET 既読 = 1 
            WHERE id = ?
        """, (notice_id,))

# === 投稿管理 ===
def save_report(report_data):
    """日報保存"""
    report_data["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO reports (
                投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, 
                コメント, 画像, 投稿日時
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_data["投稿者"], report_data["実行日"],
            report_data["カテゴリ"], report_data["場所"],
            report_data["実施内容"], report_data["所感"],
            json.dumps([]), report_data.get("image"),
            report_data["投稿日時"]
        ))

def save_weekly_schedule(schedule_data):
    """週間予定保存"""
    schedule_data["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO weekly_schedules (
                投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日,
                木曜日, 金曜日, 土曜日, 日曜日, 投稿日時, コメント
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule_data["投稿者"], schedule_data["開始日"],
            schedule_data["終了日"], schedule_data["月曜日"],
            schedule_data["火曜日"], schedule_data["水曜日"],
            schedule_data["木曜日"], schedule_data["金曜日"],
            schedule_data["土曜日"], schedule_data["日曜日"],
            schedule_data["投稿日時"], json.dumps([])
        ))

# === データ更新 ===
def update_item(item_type, item_id, **kwargs):
    """投稿更新共通処理"""
    table = "reports" if item_type == "report" else "weekly_schedules"
    set_clause = ", ".join([f"{k} = ?" for k in kwargs])
    values = list(kwargs.values()) + [item_id]
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"""
            UPDATE {table}
            SET {set_clause}
            WHERE id = ?
        """, values)

# === データ削除 ===
def delete_item(item_type, item_id):
    """投稿削除共通処理"""
    table = "reports" if item_type == "report" else "weekly_schedules"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
