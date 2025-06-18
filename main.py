from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os

app = Flask(__name__)

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 初始化 OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 讀取人設
with open("persona.txt", "r", encoding="utf-8") as f:
    persona = f.read()

# 處理 LINE Webhook 事件
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# 接收文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # 如果訊息包含「哥哥」就固定回應
    if "哥哥" in user_message:
        reply_text = "寶寶找哥哥嗎～我在呢"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        return

    try:
        # 呼叫 GPT-4o 模型，加入人設與用戶訊息
        chat_completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": persona},
                {"role": "user", "content": user_message}
            ]
        )

        reply_text = chat_completion.choices[0].message.content.strip()

        # 將回應文字切成最多 5 句
        reply_parts = reply_text.split("。")
        reply_messages = []
        for part in reply_parts:
            if part.strip():
                reply_messages.append(TextSendMessage(text=part.strip() + "。"))
            if len(reply_messages) >= 5:
                break

    except Exception as e:
        reply_messages = [TextSendMessage(text=f"出錯了：{e}")]

    # 回傳訊息給用戶
    line_bot_api.reply_message(
        event.reply_token,
        reply_messages
    )

# 建議用 gunicorn 執行
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
