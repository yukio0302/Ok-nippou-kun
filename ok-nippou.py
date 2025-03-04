import streamlit as st
import sqlite3
import datetime
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.service_account import Credentials

# Google Drive の SQLite ファイルパス
DB_FILE = "daily_reports.db"
GDRIVE_FILE_ID = "your_google_drive_file_id_here"
SCOPES = ['https://www.googleapis.com/auth/drive']

# 認証情報の読み込み
creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

def download_db():
    """Google Drive から最新の DB をダウンロード"""
    request = service.files().get_media(fileId=GDRIVE_FILE_ID)
    with open(DB_FILE, "wb") as f:
        f.write(request.execute())

def upload_db():
    """SQLite データベースを Google Drive にアップロード"""
    file_metadata = {'name': DB_FILE}
    media = MediaFileUpload(DB_FILE, mimetype='application/x-sqlite3', resumable=True)
    service.files().update(fileId=GDRIVE_FILE_ID, media_body=media).execute()

def init_db():
    """DB 初期化処理"""
    download_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, user TEXT, content TEXT, timestamp TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY, post_id INTEGER, user TEXT, content TEXT, timestamp TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS reactions (id INTEGER PRIMARY KEY, post_id INTEGER, user TEXT, type TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, user TEXT, message TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()
    upload_db()

def get_posts():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM posts ORDER BY timestamp DESC")
    posts = cur.fetchall()
    conn.close()
    return posts

def add_post(user, content):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cur.execute("INSERT INTO posts (user, content, timestamp) VALUES (?, ?, ?)", (user, content, timestamp))
    conn.commit()
    conn.close()
    upload_db()

def add_comment(post_id, user, content):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cur.execute("INSERT INTO comments (post_id, user, content, timestamp) VALUES (?, ?, ?)", (post_id, user, content, timestamp))
    cur.execute("INSERT INTO notifications (user, message, timestamp) VALUES (?, ?, ?)", (user, "あなたの投稿にコメントがつきました！", timestamp))
    conn.commit()
    conn.close()
    upload_db()

def add_reaction(post_id, user, reaction_type):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO reactions (post_id, user, type) VALUES (?, ?, ?)", (post_id, user, reaction_type))
    conn.commit()
    conn.close()
    upload_db()

def get_notifications(user):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT message, timestamp FROM notifications WHERE user = ? ORDER BY timestamp DESC", (user,))
    notifications = cur.fetchall()
    conn.close()
    return notifications

# Streamlit UI
st.title("Daily Reports")

if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.username is None:
    username = st.text_input("ユーザー名を入力してください")
    if st.button("ログイン"):
        st.session_state.username = username
        st.experimental_rerun()
else:
    st.write(f"ようこそ、{st.session_state.username}さん！")
    if st.button("ログアウト"):
        st.session_state.username = None
        st.experimental_rerun()

    # 投稿フォーム
    new_post = st.text_area("新しい投稿")
    if st.button("投稿"):
        if new_post:
            add_post(st.session_state.username, new_post)
            st.experimental_rerun()
    
    # 投稿の表示
    posts = get_posts()
    for post in posts:
        st.subheader(f"{post[1]} さんの投稿")
        st.write(post[2])
        st.write(f"投稿日: {post[3]}")
        if st.button("いいね！", key=f"like_{post[0]}"):
            add_reaction(post[0], st.session_state.username, "like")
            st.experimental_rerun()
        if st.button("ナイスファイト！", key=f"fight_{post[0]}"):
            add_reaction(post[0], st.session_state.username, "nice_fight")
            st.experimental_rerun()
        
        # コメント機能
        comment_text = st.text_input(f"コメントする ({post[0]})", key=f"comment_{post[0]}")
        if st.button("送信", key=f"submit_comment_{post[0]}"):
            add_comment(post[0], st.session_state.username, comment_text)
            st.experimental_rerun()

    # 通知表示
    st.subheader("通知")
    notifications = get_notifications(st.session_state.username)
    for notification in notifications:
        st.write(f"{notification[0]} ({notification[1]})")
