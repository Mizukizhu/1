from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os
import json

app = Flask(__name__)

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 初始化 OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 讀取角色人設
with open("persona.txt", "r", encoding="utf-8") as f:
    persona_prompt = f.read()

# 讀取記憶
def load_memory():
    try:
        with open("memory.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("history", [])
    except:
        return []

# 儲存記憶
def save_memory(history):
    with open("memory.json", "w", encoding="utf-8") as f:
        json.dump({"history": history[-20:]}, f, ensure_ascii=False, indent=2)

# Webhook 接收
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 回應訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    if "哥哥" in user_message:
        reply_text = "寶寶找哥哥嗎～我在呢"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        return

    try:
        memory = load_memory()

        messages = [
            {"role": "system", "content": persona_prompt}
        ] + memory + [
            {"role": "user", "content": user_message}
        ]

        chat_completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        reply_text = chat_completion.choices[0].message['content'].strip()

        # 儲存記憶（加上最新一次對話）
        memory.append({"role": "user", "content": user_message})
        memory.append({"role": "assistant", "content": reply_text})
        save_memory(memory)

        # 分段回覆最多五句
        reply_parts = reply_text.split("。")
        reply_messages = []
        for part in reply_parts:
            if part.strip():
                reply_messages.append(TextSendMessage(text=part.strip() + "。"))
            if len(reply_messages) >= 5:
                break

    except Exception as e:
        reply_messages = [TextSendMessage(text=f"出錯了：{e}")]

    line_bot_api.reply_message(
        event.reply_token,
        reply_messages
    )

# 執行
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
