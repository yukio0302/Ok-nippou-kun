import pandas as pd
import io
import base64
from datetime import datetime
import logging
import json
import csv

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_download_link(b64, filename):
    """ダウンロードリンクを生成する共通関数"""
    # 目立つスタイルのダウンロードボタン
    download_button = f'''
    <div style="margin: 10px 0; text-align: center;">
        <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" 
           download="{filename}" 
           style="background-color: #4CAF50; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 4px; display: inline-block; 
                  font-weight: bold; margin: 10px 0; font-size: 16px; cursor: pointer;
                  box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
            Excelファイルをダウンロード
        </a>
    </div>
    '''
    return download_button

def export_to_excel(reports, filename="日報データ.xlsx", include_content=False):
    """日報データをExcelファイルとしてエクスポート
    
    Args:
        reports: 日報データのリスト
        filename: 出力ファイル名
        include_content: 内容と今後のアクションを含めるかどうか
    """
    try:
        # データフレーム変換用にデータを整形
        data = []
        for report in reports:
            # 訪問店舗情報を整形
            visited_stores = report.get("visited_stores", [])
            store_names = [store["name"] for store in visited_stores] if visited_stores else []
            store_names_str = ", ".join(store_names)
            
            # 内容（新旧フィールド名に対応）
            content = ""
            if "実施内容" in report and report["実施内容"]:
                content = report["実施内容"]
            elif "業務内容" in report and report["業務内容"]:
                content = report["業務内容"]
                
            # 所感データがあれば追加
            if "所感" in report and report["所感"]:
                if content:
                    content += "\n\n" + report["所感"]
                else:
                    content = report["所感"]
            elif "メンバー状況" in report and report["メンバー状況"]:
                if content:
                    content += "\n\n" + report["メンバー状況"]
                else:
                    content = report["メンバー状況"]
                    
            # 今後のアクション（新旧フィールド名に対応）
            action = ""
            if "今後のアクション" in report and report["今後のアクション"]:
                action = report["今後のアクション"]
            elif "翌日予定" in report and report["翌日予定"]:
                action = report["翌日予定"]
            
            # 基本情報（すべての場合で含める）
            row = {
                "投稿者": report["投稿者"],
                "所属部署": report["所属部署"],
                "日付": report["日付"],
                "訪問店舗": store_names_str,
                "投稿日時": report["投稿日時"]
            }
            
            # マイページからの出力の場合は内容と今後のアクションを追加
            if include_content:
                row["内容"] = content
                row["今後のアクション"] = action
            else:
                # 従来の項目も保持（管理者向け）
                row["業務内容"] = report.get("業務内容", "")
                row["メンバー状況"] = report.get("メンバー状況", "")
                row["作業時間"] = report.get("作業時間", "")
                row["翌日予定"] = report.get("翌日予定", "")
                row["相談事項"] = report.get("相談事項", "")
            
            data.append(row)
        
        # データフレーム作成
        df = pd.DataFrame(data)
        
        # Excelファイルを作成（メモリ上）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='日報データ', index=False)
            
            # ワークシートとワークブックの取得
            workbook = writer.book
            worksheet = writer.sheets['日報データ']
            
            # 列幅の調整
            worksheet.set_column('A:A', 12)  # 投稿者
            worksheet.set_column('B:B', 12)  # 所属部署
            worksheet.set_column('C:C', 12)  # 日付
            worksheet.set_column('D:D', 25)  # 訪問店舗
            
            # 内容と今後のアクションが含まれる場合、列幅を調整
            if include_content:
                worksheet.set_column('E:E', 15)  # 投稿日時
                worksheet.set_column('F:F', 40)  # 内容
                worksheet.set_column('G:G', 30)  # 今後のアクション
            else:
                worksheet.set_column('E:J', 15)  # その他の列
        
        # Streamlitでダウンロードリンクを作成するためのデータを返す
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode('utf-8')
        # 共通関数を使って目立つダウンロードリンクを生成
        href = create_download_link(b64, filename)
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
            
            # ワークシートとワークブックの取得
            workbook = writer.book
            worksheet = writer.sheets['週間予定データ']
            
            # 列幅の調整
            worksheet.set_column('A:A', 12)  # 投稿者
            worksheet.set_column('B:C', 12)  # 開始日、終了日
            
            # 各曜日とその訪問店舗に適切な幅を設定
            col_index = 3  # 'D'から始まる（0ベースのインデックス）
            for _ in range(7):  # 7日分の繰り返し
                # 予定列（15文字分）
                worksheet.set_column(col_index, col_index, 15)
                col_index += 1
                
                # 訪問店舗列（30文字分）
                worksheet.set_column(col_index, col_index, 30)
                col_index += 1
            
            # 投稿日時
            worksheet.set_column('R:R', 18)  # 'R'列 = 投稿日時
        
        # Streamlitでダウンロードリンクを作成するためのデータを返す
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode('utf-8')
        # 共通関数を使って目立つダウンロードリンクを生成
        href = create_download_link(b64, filename)
        return href
    except Exception as e:
        logging.error(f"週間予定Excelエクスポートエラー: {e}")
        return None

def export_store_visits_to_excel(store_visits, filename="店舗訪問データ.xlsx"):
    """店舗訪問データをExcelファイルとしてエクスポート
    
    1シート目: 訪問店舗データサマリ
    2シート目以降: 各ユーザーごとの訪問詳細データ（各ユーザーに1シート）
    """
    try:
        # データフレーム作成用のリスト
        data = []
        
        # エラーがあれば詳細にログ出力
        logging.info(f"店舗訪問データ: {type(store_visits)}")
        
        # ユーザーごとのデータを格納する辞書
        user_data = {}
        
        if isinstance(store_visits, dict):
            for user_name, visits in store_visits.items():
                # 各ユーザーのシート用データを初期化
                if user_name not in user_data:
                    user_data[user_name] = []
                
                for store in visits:
                    # サマリー用データ
                    row = {
                        "ユーザー名": user_name,
                        "店舗コード": store["code"],
                        "店舗名": store["name"],
                        "訪問回数": store["count"],
                        "訪問日": ", ".join(store["dates"])
                    }
                    data.append(row)
                    
                    # ユーザー詳細シート用データ (内容と今後のアクションを追加)
                    user_row = {
                        "店舗コード": store["code"],
                        "店舗名": store["name"],
                        "訪問回数": store["count"],
                        "訪問日": ", ".join(store["dates"]),
                        "内容": "",  # 詳細情報から内容を後で取得
                        "今後のアクション": ""  # 詳細情報から今後のアクションを後で取得
                    }
                    
                    # 詳細があれば、最新の詳細から内容と今後のアクションを取得
                    if "details" in store and store["details"]:
                        # 最新の詳細から内容を取得して追加
                        latest_detail = store["details"][0]
                        content = latest_detail.get("content", "")
                        if content:
                            user_row["内容"] = content
                        
                        # 最新の詳細から今後のアクションを取得して追加
                        action = latest_detail.get("action", "")
                        if action:
                            user_row["今後のアクション"] = action
                        
                    user_data[user_name].append(user_row)
        else:
            logging.error(f"店舗訪問データの形式が不正: {type(store_visits)}")
            # エラーだった場合はシンプルなメッセージを表示
            return '<div style="color:red;">データのエクスポートに失敗しました。管理者に連絡してください。</div>'
        
        # データがない場合のチェック
        if not data:
            logging.error("店舗訪問データが空です。")
            return '<div style="color:orange;">エクスポートするデータがありません。</div>'
        
        # サマリーデータフレーム作成
        df_summary = pd.DataFrame(data)
        
        # 訪問回数でソート（降順）
        if not df_summary.empty:
            df_summary = df_summary.sort_values(by=["ユーザー名", "訪問回数"], ascending=[True, False])
        
        # Excelファイルを作成（メモリ上）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # サマリーシートの作成
            df_summary.to_excel(writer, sheet_name='訪問店舗データサマリ', index=False)
            
            # ワークシートとワークブックの取得
            workbook = writer.book
            summary_worksheet = writer.sheets['訪問店舗データサマリ']
            
            # サマリーシートの列幅調整
            summary_worksheet.set_column('A:A', 15)  # ユーザー名
            summary_worksheet.set_column('B:B', 12)  # 店舗コード
            summary_worksheet.set_column('C:C', 25)  # 店舗名
            summary_worksheet.set_column('D:D', 10)  # 訪問回数
            summary_worksheet.set_column('E:E', 40)  # 訪問日
            
            # 各ユーザーのシートを作成
            for user_name, user_visits in user_data.items():
                # ユーザー名をシート名として使用（シート名の制限に対応）
                sheet_name = user_name
                if len(sheet_name) > 31:  # Excelのシート名は31文字までの制限あり
                    sheet_name = sheet_name[:28] + "..."
                
                # ユーザーのデータがない場合は空のデータフレームを作成
                if not user_visits:
                    df_user = pd.DataFrame(columns=["店舗コード", "店舗名", "訪問回数", "訪問日"])
                else:
                    df_user = pd.DataFrame(user_visits)
                    # 訪問回数でソート（降順）
                    df_user = df_user.sort_values(by="訪問回数", ascending=False)
                
                # ユーザーシートの作成
                df_user.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # ワークシートの取得
                user_worksheet = writer.sheets[sheet_name]
                
                # 列幅調整
                user_worksheet.set_column('A:A', 12)  # 店舗コード
                user_worksheet.set_column('B:B', 25)  # 店舗名
                user_worksheet.set_column('C:C', 10)  # 訪問回数
                user_worksheet.set_column('D:D', 40)  # 訪問日
                user_worksheet.set_column('E:E', 50)  # 内容
                user_worksheet.set_column('F:F', 50)  # 今後のアクション
        
        # Streamlitでダウンロードリンクを作成するためのデータを返す
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode('utf-8')
        # 共通関数を使って目立つダウンロードリンクを生成
        href = create_download_link(b64, filename)
        return href
    except Exception as e:
        logging.error(f"店舗訪問Excelエクスポートエラー: {e}")
        logging.error(f"エラー詳細: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return '<div style="color:red;">エクスポート中にエラーが発生しました。</div>'

def convert_excel_to_json(uploaded_file, format_type="stores"):
    """アップロードされたExcelファイルをJSON形式に変換"""
    try:
        # Excelファイルを読み込む (エンコードの問題に対応)
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as excel_err:
            logging.error(f"Excel読み込みエラー: {excel_err}, 別の方法を試みます。")
            # 別の方法を試す
            try:
                # ファイルポインタをリセット
                uploaded_file.seek(0)
                # Excelオプションを変更して再試行
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            except Exception as openpyxl_err:
                logging.error(f"openpyxlでの読み込みも失敗: {openpyxl_err}")
                return None, f"Excelファイルの読み込みに失敗しました: {str(openpyxl_err)}"
        
        if format_type == "stores":
            # 期待されるカラム名のリスト (必須と任意)
            expected_mandatory_columns = ["得意先c", "得意先名"]
            expected_optional_columns = ["郵便番号", "住所", "部門c", "担当者c", "担当者名", "担当者社員コード"]
            all_expected_columns = expected_mandatory_columns + expected_optional_columns
            
            # カラム名の検証 (必須カラムのみ)
            for col in expected_mandatory_columns:
                if col not in df.columns:
                    # カラム名が見つからない場合はエラーを返す
                    return None, f"必須カラム '{col}' がExcelファイルに見つかりません。"
            
            # NaNをNoneに変換
            df = df.where(pd.notna(df), None)
            
            # JSONに変換
            stores_data = []
            for _, row in df.iterrows():
                # 必須フィールド
                if pd.isna(row["得意先c"]) or pd.isna(row["得意先名"]):
                    continue  # 得意先コードや名前が空の行はスキップ
                
                store = {
                    "code": str(row["得意先c"]) if not pd.isna(row["得意先c"]) else "",
                    "name": str(row["得意先名"]) if not pd.isna(row["得意先名"]) else "",
                }
                
                # 任意フィールド (存在する場合のみ追加)
                for col in expected_optional_columns:
                    if col in df.columns and not pd.isna(row.get(col, None)):
                        # カラム名をJSON用にマッピング
                        json_key = {
                            "郵便番号": "postal_code",
                            "住所": "address",
                            "部門c": "department_code",
                            "担当者c": "staff_code",
                            "担当者名": "staff_name",
                            "担当者社員コード": "担当者社員コード"
                        }.get(col, col)
                        
                        store[json_key] = str(row[col])
                
                # 必須フィールドが揃っている場合のみデータに追加
                if store["code"] and store["name"]:
                    stores_data.append(store)
            
            if not stores_data:
                return None, "有効なデータがExcelファイルから見つかりませんでした。"
            
            return stores_data, None
        
        return None, "サポートされていない変換形式です。"
    except Exception as e:
        logging.error(f"Excel変換エラー: {e}")
        return None, f"Excelファイルの変換中にエラーが発生しました: {str(e)}"

# 以下の関数はCSVエクスポート用関数でしたが、要件変更によりExcelエクスポートに統一
# カスタマーリクエストにより、以下のCSV関連関数は残しておきます（互換性のため）
# ただし、アプリのUIからは呼び出されなくなります

def export_to_csv(data, filename="data.csv"):
    """データをCSVファイルとしてエクスポート（互換性のために残す）"""
    try:
        # データフレームを作成
        df = pd.DataFrame(data)
        
        # CSVをメモリ上に出力
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')  # BOMを含めてUTF-8で出力（Excel対応）
        
        # Base64エンコード
        csv_str = csv_buffer.getvalue()
        csv_bytes = csv_str.encode('utf-8')
        b64 = base64.b64encode(csv_bytes).decode()
        
        # ダウンロードリンク生成
        href = f'<a href="data:text/csv;charset=utf-8,{b64}" download="{filename}">CSVファイルをダウンロード</a>'
        return href
    except Exception as e:
        logging.error(f"CSVエクスポートエラー: {e}")
        return None

def export_reports_to_csv(reports, filename="日報データ.csv"):
    """日報データをCSVファイルとしてエクスポート（互換性のために残す）"""
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
        
        return export_to_csv(data, filename)
    except Exception as e:
        logging.error(f"日報CSVエクスポートエラー: {e}")
        return None

def export_weekly_schedules_to_csv(schedules, filename="週間予定データ.csv"):
    """週間予定データをCSVファイルとしてエクスポート（互換性のために残す）"""
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
        
        return export_to_csv(data, filename)
    except Exception as e:
        logging.error(f"週間予定CSVエクスポートエラー: {e}")
        return None

def export_store_visits_to_csv(store_visits, filename="店舗訪問データ.csv"):
    """店舗訪問データをCSVファイルとしてエクスポート（互換性のために残す）"""
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
        
        # CSVをメモリ上に出力
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')  # BOMを含めてUTF-8で出力（Excel対応）
        
        # Base64エンコード
        csv_str = csv_buffer.getvalue()
        csv_bytes = csv_str.encode('utf-8')
        b64 = base64.b64encode(csv_bytes).decode()
        
        # ダウンロードリンク生成
        href = f'<a href="data:text/csv;charset=utf-8,{b64}" download="{filename}">CSVファイルをダウンロード</a>'
        return href
    except Exception as e:
        logging.error(f"店舗訪問CSVエクスポートエラー: {e}")
        return None

def export_monthly_stats_to_excel(stats, year, filename=None):
    """月次投稿統計データをExcelファイルとしてエクスポート"""
    try:
        if not filename:
            filename = f"投稿統計_{year}年.xlsx"
            
        # 年でフィルタリング
        year_prefix = f"{year}-"
        filtered_stats = [s for s in stats if s["年月"].startswith(year_prefix)]
        
        if not filtered_stats:
            return None
            
        # 通常形式（全データ）
        df = pd.DataFrame(filtered_stats)
        
        # ピボット形式のデータも作成
        pivot_data = {}
        for stat in filtered_stats:
            user = stat["投稿者"]
            year_month = stat["年月"]
            count = stat["投稿数"]
            
            if user not in pivot_data:
                pivot_data[user] = {"名前": user}
            
            # 月だけを取り出して列名にする
            month_str = f"{int(year_month.split('-')[1])}月"
            pivot_data[user][month_str] = count
        
        # データフレームに変換
        pivot_df = pd.DataFrame(list(pivot_data.values()))
        
        # 月の列を正しい順序に並べ替え
        month_cols = [f"{m}月" for m in range(1, 13)]
        existing_cols = [col for col in month_cols if col in pivot_df.columns]
        
        if existing_cols:
            # 合計を計算して追加
            pivot_df["合計"] = pivot_df[existing_cols].sum(axis=1)
            pivot_df = pivot_df.sort_values("合計", ascending=False)
        
        # Excelファイルを作成（メモリ上）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 詳細データをシート1に出力
            df.to_excel(writer, sheet_name='詳細データ', index=False)
            
            # サマリーデータをシート2に出力
            pivot_df.to_excel(writer, sheet_name='サマリーデータ', index=False)
            
            # ワークシートとワークブックの取得
            workbook = writer.book
            detailed_worksheet = writer.sheets['詳細データ']
            summary_worksheet = writer.sheets['サマリーデータ']
            
            # 詳細データの列幅を調整
            detailed_worksheet.set_column('A:A', 15)  # 投稿者
            detailed_worksheet.set_column('B:B', 12)  # 年月
            detailed_worksheet.set_column('C:C', 10)  # 投稿数
            
            # サマリーデータの列幅を調整
            summary_worksheet.set_column('A:A', 15)  # 名前
            
            # 月の列（B～M）の幅を設定
            for i, _ in enumerate(existing_cols):
                col_letter = chr(ord('B') + i)
                summary_worksheet.set_column(f'{col_letter}:{col_letter}', 8)
            
            # 合計列の幅を設定
            summary_worksheet.set_column('N:N', 10)  # 合計列
            
            # 数値セルのフォーマット設定
            number_format = workbook.add_format({'num_format': '0'})
            
            # サマリーデータにフォーマット適用
            for i, _ in enumerate(existing_cols):
                col_index = i + 1  # B列から始まるため（0ベース + 1）
                for row in range(1, len(pivot_data) + 1):  # ヘッダー行を除く
                    summary_worksheet.set_column(col_index, col_index, 8, number_format)
            
            # 合計列にもフォーマット適用
            if existing_cols:
                total_col_index = len(existing_cols) + 1
                summary_worksheet.set_column(total_col_index, total_col_index, 10, number_format)
        
        # Streamlitでダウンロードリンクを作成するためのデータを返す
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode('utf-8')
        # 共通関数を使って目立つダウンロードリンクを生成
        href = create_download_link(b64, filename)
        return href
    except Exception as e:
        logging.error(f"月次統計Excelエクスポートエラー: {e}")
        return None

def export_monthly_stats_to_csv(stats, year, filename=None):
    """月次投稿統計データをCSVファイルとしてエクスポート（互換性のために残す）"""
    # 推奨されないため、Excelエクスポートを使用するように変更
    return export_monthly_stats_to_excel(stats, year, filename.replace('.csv', '.xlsx') if filename else None)

def parse_excel_to_stores_json(file_path):
    """ファイルパスを指定してExcelファイルを店舗JSONに変換する"""
    try:
        # ファイルを読み込む
        df = pd.read_excel(file_path, engine='openpyxl')
        
        # 得意先cと得意先名カラムが存在するか確認
        if "得意先c" not in df.columns or "得意先名" not in df.columns:
            logging.error("必須カラムがExcelファイルに見つかりません")
            return None
        
        # データクリーニング
        df = df.where(pd.notna(df), None)
        
        # 店舗データ変換
        stores_data = []
        for _, row in df.iterrows():
            # 得意先cまたは得意先名が空の行はスキップ
            if pd.isna(row["得意先c"]) or pd.isna(row["得意先名"]):
                continue
                
            store = {
                "code": str(row["得意先c"]),
                "name": str(row["得意先名"]),
            }
            
            # 任意フィールド
            if "郵便番号" in df.columns and not pd.isna(row["郵便番号"]):
                store["postal_code"] = str(row["郵便番号"])
            
            if "住所" in df.columns and not pd.isna(row["住所"]):
                store["address"] = str(row["住所"])
            
            if "担当者社員コード" in df.columns and not pd.isna(row["担当者社員コード"]):
                store["担当者社員コード"] = str(row["担当者社員コード"])
            
            if "担当者名" in df.columns and not pd.isna(row["担当者名"]):
                store["staff_name"] = str(row["担当者名"])
            
            stores_data.append(store)
        
        # JSONに変換
        return stores_data
    except Exception as e:
        logging.error(f"Excel店舗データ変換エラー: {e}")
        return None
