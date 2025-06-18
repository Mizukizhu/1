from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage
import os
import json
import random
import openai
import tempfile
import base64
from long_term_memory import load_user_memory, save_user_memory

app = Flask(__name__)

# 環境變數設定
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

MEMORY_FILE = "memory.json"
MAX_MEMORY = 30

# Webhook 接收
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 文字訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()

    memory = load_user_memory(user_id, MEMORY_FILE)
    memory.append({"role": "user", "content": user_input})

    try:
        with open("persona.txt", "r", encoding="utf-8") as f:
            persona = f.read()

        # 加入「請你用夏以晝的語氣連續說 3～5 句話」提示
        prompt = persona + "\n請你根據以上角色人設，用自然對話語氣連續說三到五句話，不要只用一句回答。"

        messages = [{"role": "system", "content": prompt}] + memory

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.8
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
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="哥哥出錯了嗚嗚…\n" + str(e))
        )

# 圖片訊息處理
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

        # 圖片提示詞：請用夏以晝的語氣看圖說話，連續講 3~5 句
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "請你用夏以晝的語氣回應這張圖片，連續說三到五句話，不要只用一句。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64," + base64_image
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.8
        )

        reply_text = response.choices[0].message.content.strip()
        reply_lines = [line.strip() for line in reply_text.split("\n") if line.strip()]
        reply_messages = [TextSendMessage(text=line) for line in reply_lines]

        line_bot_api.reply_message(event.reply_token, reply_messages)

    except Exception as e:
        import traceback
        traceback.print_exc()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="哥哥看圖的時候出錯了…\n" + str(e))
        )

if __name__ == "__main__":
    app.run()
