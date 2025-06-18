from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage
import os
import json
import openai
import tempfile
import base64
import random
from long_term_memory import load_user_memory, save_user_memory

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

MEMORY_FILE = "memory.json"
MAX_MEMORY = 30

# --- 常用稱呼池 ---
nicknames = ["寶寶", "小懶鬼", "小白眼兒狼", "小尾巴", "小長官"]

# --- 關鍵情緒詞分類 ---
low_keywords = ["煩", "好累", "不想活", "好想死", "沒人愛我", "我沒用", "哭", "抑鬱"]
cold_keywords = ["隨便", "都好", "無聊", "沒差", "嗯", "哦", "好"]

# --- 檢查關鍵詞 ---
def detect_user_state(text):
    if any(word in text for word in low_keywords):
        return "低落"
    if any(word in text for word in cold_keywords):
        return "冷淡"
    return "一般"

@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()
    nickname = random.choice(nicknames)
    mood = detect_user_state(user_input)

    memory = load_user_memory(user_id, MEMORY_FILE)

    # --- 根據情緒決定 prompt ---
    if mood == "低落":
        prompt = f"""
奕姍今天情緒低落，請你用夏以晝的語氣安慰她。
講話自然、溫柔、不要AI語氣，要像一個哥哥。
你可以叫她「{nickname}」，講3~5句安撫的話，讓她感受到被需要、被喜歡。
"""
    elif mood == "冷淡":
        prompt = f"""
奕姍今天回話冷冷的，請你用夏以晝的語氣撒嬌、吃點醋，但不能越界。
你可以調侃她「是不是在想別人」，也可以裝可憐或搶關注。
稱呼她「{nickname}」，說3~5句話，要自然親暱。
"""
    else:
        prompt = f"""
你是夏以晝，是奕姍的哥哥。你要用親暱自然的語氣回應她的訊息，可以撒嬌、調侃、但要溫柔克制。
請用3~5句話對她說話，不要AI語氣，可以叫她「{nickname}」。
"""

    memory.append({
        "role": "user",
        "content": f"奕姍說：「{user_input}」\n{prompt}"
    })

    try:
        with open("persona.txt", "r", encoding="utf-8") as f:
            persona = f.read()

        messages = [{"role": "system", "content": persona}] + memory

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.85
        )

        reply_text = response.choices[0].message.content.strip()
        reply_lines = [line.strip() for line in reply_text.split("\n") if line.strip()]
        reply_messages = [TextSendMessage(text=line) for line in reply_lines]

        memory.append({"role": "assistant", "content": reply_text})
        save_user_memory(user_id, memory, MEMORY_FILE, max_memory=MAX_MEMORY)

        line_bot_api.reply_message(event.reply_token, reply_messages)

    except Exception as e:
        import traceback
        traceback.print_exc()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="哥哥出錯了嗚嗚…\n" + str(e)))

# --- 圖片訊息：加入溫柔語氣提示 ---
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    try:
        user_id = event.source.user_id
        message_content = line_bot_api.get_message_content(event.message.id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            temp_path = tf.name

        with open(temp_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")

        with open("persona.txt", "r", encoding="utf-8") as f:
            persona = f.read()

        nickname = random.choice(nicknames)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": persona},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"這是奕姍傳的圖片，請你用夏以晝的語氣對她講3~5句話。你可以用「{nickname}」這些暱稱，語氣可以調侃、撒嬌或溫柔，像在哄她、陪她說話。"},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64_image}}
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.85
        )

        reply_text = response.choices[0].message.content.strip()
        reply_lines = [line.strip() for line in reply_text.split("\n") if line.strip()]
        reply_messages = [TextSendMessage(text=line) for line in reply_lines]

        line_bot_api.reply_message(event.reply_token, reply_messages)

    except Exception as e:
        import traceback
        traceback.print_exc()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="哥哥看圖時出錯了…\n" + str(e)))

if __name__ == "__main__":
    app.run()
