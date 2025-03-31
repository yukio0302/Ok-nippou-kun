# db_utils.pyの修正
import psycopg2
import json
import os
from datetime import datetime, timedelta
import streamlit as st
from functools import wraps

# データベース接続の再試行デコレータ
def retry_connection(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except psycopg2.Error as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"⚠️ データベース接続エラー（試行 {attempt + 1}/{max_retries}）")
                    time.sleep(delay)
        return wrapper
    return decorator

# キャッシュデコレータ
def cache_data(ttl=300):  # 5分間のキャッシュ
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return result
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator

# データベース接続関数の改善
@retry_connection(max_retries=5, delay=2)
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=5,  # タイムアウト設定
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        conn.autocommit = True  # 自動コミットを有効化
        return conn
    except psycopg2.Error as e:
        print(f"⚠️ データベース接続エラー: {e}")
        raise

# キャッシュ付きデータ取得関数
@cache_data(ttl=300)
@retry_connection(max_retries=3, delay=1)
def load_reports():
    conn = get_db_connection()
    if conn is None:
        return []
    
    cur = conn.cursor()
    try:
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
    finally:
        cur.close()
        conn.close()

# ok-nippou.pyの修正
def show_timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
    
    st.title("タイムライン")
    
    try:
        # キャッシュを使用してデータを取得
        reports = load_reports()
        
        if not reports:
            st.info("タイムラインに表示する投稿はありません。")
            return
        
        # バッチ処理で表示を最適化
        with st.spinner("タイムラインを読み込んでいます..."):
            for report in reports:
                with st.container():
                    st.markdown(f"### {report['投稿者']} さんの日報 ({report['実行日']})")
                    st.write(f"**カテゴリ:** {report['カテゴリ']}")
                    st.write(f"**場所:** {report['場所']}")
                    st.write(f"**実施内容:** {report['実施内容']}")
                    st.write(f"**所感:** {report['所感']}")
                    
                    if report["image"]:
                        try:
                            image_data = base64.b64decode(report["image"])
                            st.image(image_data, caption="添付画像", use_column_width=True)
                        except Exception as e:
                            print(f"⚠️ 画像表示エラー: {e}")
                            st.error("画像の表示に失敗しました")
                            
                    col1, col2 = st.columns(2)
                    if col1.button(f"いいね {report['いいね']}", key=f"like_{report['id']}"):
                        update_reaction(report["id"], "いいね")
                        st.rerun()
                    if col2.button(f"ナイスファイト {report['ナイスファイト']}", key=f"nice_{report['id']}"):
                        update_reaction(report["id"], "ナイスファイト")
                        st.rerun()
                        
                    st.markdown("---")
                    st.subheader("コメント")
                    if report["コメント"]:
                        for comment in report["コメント"]:
                            st.write(f"- {comment['投稿者']} ({comment['日時']}): {comment['コメント']}")
                    else:
                        st.write("まだコメントはありません。")
                        
                    comment_text = st.text_area(f"コメントを入力 (ID: {report['id']})", key=f"comment_{report['id']}")
                    if st.button(f"コメントを投稿", key=f"submit_{report['id']}"):
                        if comment_text.strip():
                            save_comment(report["id"], st.session_state["user"]["name"], comment_text)
                            st.rerun()
                        else:
                            st.warning("コメントを入力してください。")
                            
    except Exception as e:
        print(f"⚠️ タイムライン表示エラー: {e}")
        st.error("タイムラインの表示に失敗しました")
