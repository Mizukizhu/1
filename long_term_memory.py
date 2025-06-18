import json
import os

def load_user_memory(user_id, file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(user_id, [])

def save_user_memory(user_id, memory, file_path, max_memory=30):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data[user_id] = memory[-max_memory:]  # 最多保留 max_memory 筆資料

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
