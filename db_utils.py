import sqlite3
import os
import shutil
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# Google Drive 連携設定
DRIVE_FOLDER_ID = "your_google_drive_folder_id"  # Google DriveのフォルダID
SERVICE_ACCOUNT_FILE = "path/to/your/service_account.json"
DB_FILE = "database.db"
BACKUP_FILE = "backup_database.db"

# Google Drive APIの認証設定
def get_drive_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)

# SQLiteデータベース接続
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# データベース初期化
def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            type TEXT CHECK(type IN ('like', 'nice_fight')) NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        );
        
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        );
        
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    conn.commit()
    conn.close()

# 投稿追加
def add_post(user_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (user_id, content) VALUES (?, ?)", (user_id, content))
    conn.commit()
    conn.close()

# コメント追加
def add_comment(user_id, post_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO comments (user_id, post_id, content) VALUES (?, ?, ?)", (user_id, post_id, content))
    
    # 投稿者に通知を追加
    cursor.execute("""
        INSERT INTO notifications (user_id, message)
        VALUES ((SELECT user_id FROM posts WHERE id = ?), 'あなたの投稿にコメントがつきました！')
    """, (post_id,))
    
    conn.commit()
    conn.close()

# リアクション追加（いいね！・ナイスファイト）
def add_reaction(user_id, post_id, reaction_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reactions (user_id, post_id, type)
        VALUES (?, ?, ?)
    """, (user_id, post_id, reaction_type))
    conn.commit()
    conn.close()

# データをGoogle Driveにバックアップ
def backup_database():
    shutil.copy(DB_FILE, BACKUP_FILE)
    service = get_drive_service()
    file_metadata = {
        "name": BACKUP_FILE,
        "parents": [DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(BACKUP_FILE, mimetype="application/x-sqlite3", resumable=True)
    
    # 既存のバックアップがあれば削除
    query = f"name='{BACKUP_FILE}' and '{DRIVE_FOLDER_ID}' in parents"
    existing_files = service.files().list(q=query).execute().get("files", [])
    for file in existing_files:
        service.files().delete(fileId=file["id"]).execute()
    
    # 新しいファイルをアップロード
    service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    print("バックアップ完了！")

# 通知の取得
def get_notifications(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, message, is_read, created_at FROM notifications WHERE user_id = ?", (user_id,))
    notifications = cursor.fetchall()
    conn.close()
    return notifications

# 通知を既読にする
def mark_notifications_as_read(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# 初回起動時にDBを初期化
initialize_db()
