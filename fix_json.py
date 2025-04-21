import json

# ファイルを読み込む
with open("attached_assets/Pasted--code-1002-name-postal-code-103-0022-address--1743565800771.txt", "r") as f:
    lines = f.readlines()

# 各行をJSONオブジェクトとして解析
stores = []
for line in lines:
    line = line.strip()
    if not line:  # 空行はスキップ
        continue
    if line.endswith(","):  # 末尾のカンマを削除
        line = line[:-1]
    try:
        store_data = json.loads(line)
        stores.append(store_data)
    except json.JSONDecodeError as e:
        print(f"Error parsing line: {line}")
        print(f"Error: {e}")
        continue

# 正しいJSONとして書き出す
with open("data/stores_data.json", "w") as f:
    json.dump(stores, f, ensure_ascii=False, indent=2)

print(f"{len(stores)}件の店舗データを保存しました。")
