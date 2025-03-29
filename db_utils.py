import psycopg2
import json
import os
from datetime import datetime, timedelta
import streamlit as st

# ✅ データベース接続情報
def get_db_connection():
    try:
        conn = st.connection(
            name="neon",
            type="sql",
            url=st.secrets.connections.neon.url
        )
        # 接続テスト
        cur = conn.cursor()
        cur.execute("SELECT 1")
        return conn
    except Exception as e:
        print(f"⚠️ データベース接続エラー: {e}")
        raise
        
def init_db(keep_existing=True):
    """データベースの初期化（テーブル作成）"""
    conn = get_db_connection()
    cur = conn.cursor()

    if not keep_existing:
        cur.execute("DROP TABLE IF EXISTS reports")
        cur.execute("DROP TABLE IF EXISTS notices")
        cur.execute("DROP TABLE IF EXISTS weekly_schedules")

    # ✅ 日報データのテーブル作成（存在しない場合のみ）
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

    # ✅ お知らせデータのテーブル作成（存在しない場合のみ）
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

    # ✅ 週間予定データのテーブル作成（存在しない場合のみ）
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

def save_report(report):
    """日報をデータベースに保存"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        if '実行日' not in report or not report['実行日']:
            report['実行日'] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")

        cur.execute("""
        INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント, 画像, 投稿日時)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            report["投稿者"], 
            report["実行日"], 
            report["カテゴリ"], 
            report["場所"],
            report["実施内容"], 
            report["所感"], 
            0,  # いいね初期値
            0,  # ナイスファイト初期値
            json.dumps([]),  # 空のコメント配列
            report.get("image", None), 
            report["投稿日時"]
        ))

        conn.commit()
        print(f"✅ 日報を保存しました（投稿者: {report['投稿者']}, 実行日: {report['実行日']}）")

    except Exception as e:
        print(f"⚠️ データベースエラー: {e}")
        raise

def load_reports():
    """日報データを取得（最新の投稿順にソート）"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM reports ORDER BY 投稿日時 DESC")
    rows = cur.fetchall()

    reports = []
    for row in rows:
        reports.append({
            "id": row[0], "投稿者": row[1], "実行日": row[2], "カテゴリ": row[3], 
            "場所": row[4], "実施内容": row[5], "所感": row[6], "いいね": row[7], 
            "ナイスファイト": row[8], "コメント": json.loads(row[9]), "image": row[10], 
            "投稿日時": row[11]
        })
    return reports
