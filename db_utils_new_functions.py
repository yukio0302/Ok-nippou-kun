def save_report_image(report_id, file_name, file_type, image_data):
    """日報に添付された画像をデータベースに保存する
    
    Args:
        report_id: 関連する日報ID
        file_name: ファイル名
        file_type: ファイルの種類 (MIME type)
        image_data: base64エンコードされた画像データ
        
    Returns:
        画像ID (成功時) または None (失敗時)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO report_images (report_id, file_name, file_type, image_data)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (report_id, file_name, file_type, image_data))
        
        image_id = cur.fetchone()[0]
        conn.commit()
        logging.info(f"画像を保存しました（ID: {image_id}, 日報ID: {report_id}）")
        return image_id
    except Exception as e:
        logging.error(f"画像保存エラー: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_report_images(report_id):
    """特定の日報に関連付けられた画像を取得する
    
    Args:
        report_id: 日報ID
        
    Returns:
        画像情報のリスト
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, file_name, file_type, image_data, created_at
            FROM report_images 
            WHERE report_id = %s
            ORDER BY created_at ASC
        """, (report_id,))
        
        images = cur.fetchall()
        return [dict(img) for img in images]
    except Exception as e:
        logging.error(f"画像取得エラー（日報ID: {report_id}）: {e}")
        return []
    finally:
        if conn:
            conn.close()

def delete_report_image(image_id):
    """画像を削除する
    
    Args:
        image_id: 画像ID
        
    Returns:
        削除成功時はTrue、失敗時はFalse
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM report_images WHERE id = %s", (image_id,))
        conn.commit()
        logging.info(f"画像を削除しました（ID: {image_id}）")
        return True
    except Exception as e:
        logging.error(f"画像削除エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
