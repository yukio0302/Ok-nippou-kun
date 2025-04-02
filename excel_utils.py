import pandas as pd
import io
import base64
from datetime import datetime
import logging
import json

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def export_to_excel(reports, filename="日報データ.xlsx"):
    """日報データをExcelファイルとしてエクスポート"""
    try:
        # データフレーム変換用にデータを整形
        data = []
        for report in reports:
            # 訪問店舗情報を整形
            visited_stores = report.get("visited_stores", [])
            store_names = [store["name"] for store in visited_stores] if visited_stores else []
            store_names_str = ", ".join(store_names)
            
            row = {
                "投稿者": report["投稿者"],
                "所属部署": report["所属部署"],
                "日付": report["日付"],
                "訪問店舗": store_names_str,
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
            # 各曜日の訪問店舗情報を整形
            weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
            store_info = {}
            
            for day in weekdays:
                day_stores_key = f"{day}_visited_stores"
                day_stores = schedule.get(day_stores_key, [])
                store_names = [store["name"] for store in day_stores] if day_stores else []
                store_info[f"{day}_訪問店舗"] = ", ".join(store_names)
            
            row = {
                "投稿者": schedule["投稿者"],
                "開始日": schedule["開始日"],
                "終了日": schedule["終了日"],
                "月曜日": schedule["月曜日"],
                "月曜日_訪問店舗": store_info["月曜日_訪問店舗"],
                "火曜日": schedule["火曜日"],
                "火曜日_訪問店舗": store_info["火曜日_訪問店舗"],
                "水曜日": schedule["水曜日"],
                "水曜日_訪問店舗": store_info["水曜日_訪問店舗"],
                "木曜日": schedule["木曜日"],
                "木曜日_訪問店舗": store_info["木曜日_訪問店舗"],
                "金曜日": schedule["金曜日"],
                "金曜日_訪問店舗": store_info["金曜日_訪問店舗"],
                "土曜日": schedule["土曜日"],
                "土曜日_訪問店舗": store_info["土曜日_訪問店舗"],
                "日曜日": schedule["日曜日"],
                "日曜日_訪問店舗": store_info["日曜日_訪問店舗"],
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

def export_store_visits_to_excel(store_visits, filename="店舗訪問データ.xlsx"):
    """店舗訪問データをExcelファイルとしてエクスポート"""
    try:
        # データフレーム作成用のリスト
        data = []
        
        for user_name, visits in store_visits.items():
            for store in visits:
                row = {
                    "ユーザー名": user_name,
                    "店舗コード": store["code"],
                    "店舗名": store["name"],
                    "訪問回数": store["count"],
                    "訪問日": ", ".join(store["dates"])
                }
                data.append(row)
        
        # データフレーム作成
        df = pd.DataFrame(data)
        
        # 訪問回数でソート（降順）
        if not df.empty:
            df = df.sort_values(by=["ユーザー名", "訪問回数"], ascending=[True, False])
        
        # Excelファイルを作成（メモリ上）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='店舗訪問データ', index=False)
            
            # ワークシートとワークブックの取得
            workbook = writer.book
            worksheet = writer.sheets['店舗訪問データ']
            
            # 列幅の調整
            worksheet.set_column('A:A', 15)  # ユーザー名
            worksheet.set_column('B:B', 12)  # 店舗コード
            worksheet.set_column('C:C', 25)  # 店舗名
            worksheet.set_column('D:D', 10)  # 訪問回数
            worksheet.set_column('E:E', 40)  # 訪問日
        
        # Streamlitでダウンロードリンクを作成するためのデータを返す
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode('utf-8')
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Excelファイルをダウンロード</a>'
        return href
    except Exception as e:
        logging.error(f"店舗訪問Excelエクスポートエラー: {e}")
        return None

def convert_excel_to_json(uploaded_file, format_type="stores"):
    """アップロードされたExcelファイルをJSON形式に変換"""
    try:
        # Excelファイルを読み込む
        df = pd.read_excel(uploaded_file)
        
        if format_type == "stores":
            # カラム名のマッピング確認
            expected_columns = ["得意先c", "得意先名", "郵便番号", "住所", "部門c", "担当者c", "担当者名", "担当者社員コード"]
            
            # カラム名を確認
            for col in expected_columns:
                if col not in df.columns:
                    return None, f"必要なカラム '{col}' がExcelファイルに見つかりません。"
            
            # NaNをNoneに変換
            df = df.where(pd.notna(df), None)
            
            # JSONに変換
            stores_data = []
            for _, row in df.iterrows():
                store = {
                    "code": str(row["得意先c"]) if row["得意先c"] is not None else "",
                    "name": row["得意先名"] if row["得意先名"] is not None else "",
                    "postal_code": str(row["郵便番号"]) if row["郵便番号"] is not None else "",
                    "address": row["住所"] if row["住所"] is not None else "",
                    "department_code": str(row["部門c"]) if row["部門c"] is not None else "",
                    "staff_code": str(row["担当者c"]) if row["担当者c"] is not None else "",
                    "staff_name": row["担当者名"] if row["担当者名"] is not None else "",
                    "担当者社員コード": str(row["担当者社員コード"]) if row["担当者社員コード"] is not None else ""
                }
                stores_data.append(store)
            
            return stores_data, None
        
        return None, "サポートされていない変換形式です。"
    except Exception as e:
        logging.error(f"Excel変換エラー: {e}")
        return None, f"Excelファイルの変換中にエラーが発生しました: {str(e)}"
