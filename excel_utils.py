import pandas as pd
import io
import base64
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def export_to_excel(reports, filename="日報データ.xlsx"):
    """日報データをExcelファイルとしてエクスポート"""
    try:
        # データフレーム変換用にデータを整形
        data = []
        for report in reports:
            row = {
                "投稿者": report["投稿者"],
                "所属部署": report["所属部署"],
                "日付": report["日付"],
                "業務内容": report["業務内容"],
                "メンバー状況": report["メンバー状況"],
                "作業時間": report["作業時間"],
                "翌日予定": report["翌日予定"],
                "相談事項": report["相談事項"],
                "投稿日時": report["投稿日時"]
            }
            data.append(row)
        
        # データフレーム作成
        df = pd.DataFrame(data)
        
        # Excelファイルを作成（メモリ上）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='日報データ', index=False)
        
        # Streamlitでダウンロードリンクを作成するためのデータを返す
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode('utf-8')
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Excelファイルをダウンロード</a>'
        return href
    except Exception as e:
        logging.error(f"Excelエクスポートエラー: {e}")
        return None

def export_weekly_schedules_to_excel(schedules, filename="週間予定データ.xlsx"):
    """週間予定データをExcelファイルとしてエクスポート"""
    try:
        # データフレーム変換用にデータを整形
        data = []
        for schedule in schedules:
            row = {
                "投稿者": schedule["投稿者"],
                "開始日": schedule["開始日"],
                "終了日": schedule["終了日"],
                "月曜日": schedule["月曜日"],
                "火曜日": schedule["火曜日"],
                "水曜日": schedule["水曜日"],
                "木曜日": schedule["木曜日"],
                "金曜日": schedule["金曜日"],
                "土曜日": schedule["土曜日"],
                "日曜日": schedule["日曜日"],
                "投稿日時": schedule["投稿日時"]
            }
            data.append(row)
        
        # データフレーム作成
        df = pd.DataFrame(data)
        
        # Excelファイルを作成（メモリ上）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='週間予定データ', index=False)
        
        # Streamlitでダウンロードリンクを作成するためのデータを返す
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode('utf-8')
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Excelファイルをダウンロード</a>'
        return href
    except Exception as e:
        logging.error(f"週間予定Excelエクスポートエラー: {e}")
        return None
