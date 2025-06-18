from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os
import json

app = Flask(__name__)

# LINE Bot 初始化
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# OpenAI 初始化
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 記憶檔案與人設檔案
MEMORY_FILE = "memory.json"
PERSONA_FILE = "persona.txt"

# 讀取人設檔案
def load_persona():
    try:
        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "你是夏以昼，一位溫柔克制的哥哥，對妹妹奕姍有強烈保護欲。"

# 讀取對話記憶
def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# 儲存對話記憶
def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# LINE webhook 路由
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # 讀取人設與記憶
    persona = load_persona()
    memory = load_memory()

    # 新增使用者輸入
    memory.append({"role": "user", "content": user_message})
    if len(memory) > 1000:
        memory = memory[-1000:]  

    try:
        # 呼叫 GPT-4o
        chat_completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": persona},
                *memory
            ]
        )

        reply_text = chat_completion.choices[0].message.content.strip()
        memory.append({"role": "assistant", "content": reply_text})
        save_memory(memory)

    except Exception as e:
        reply_text = f"出錯了：{e}"

    # 傳回 LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# 開發測試用
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
