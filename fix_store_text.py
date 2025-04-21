#!/usr/bin/env python3
import re

# 正規表現パターン
pattern1 = r'(\s+selected_in_this_session\.append\(store_dict\)\n\s+day_stores\.append\(store_dict\))\n\s+store_text \+= f"\【\{name\}\】"'
pattern2 = r'(\s+selected_in_this_session\.append\(store_dict\)\n\s+day_stores\.append\(store_dict\))\n\s+store_text \+= f"\【\{name\}\】"'
pattern3 = r'(\s+selected_in_this_session\.append\(store_dict\)\n\s+day_stores\.append\(store_dict\))\n\s+store_text \+= f"\【\{location\.strip\(\)\}\】"'

# 置換テキスト
replacement = r'\1\n                    # 店舗名のテキスト追加は不要に'

# 元のファイルを読む
with open('ok-nippou.py', 'r') as f:
    content = f.read()

# 置換を行う
content = re.sub(pattern1, replacement, content)
content = re.sub(pattern2, replacement, content)
content = re.sub(pattern3, replacement, content)

# 結果を保存
with open('ok-nippou.py.new', 'w') as f:
    f.write(content)

print("処理が完了しました")
