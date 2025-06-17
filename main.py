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

# LINE Webhook 接收入口
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 接收 LINE 訊息事件
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
        chat_completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是夏以昼，是一位溫柔又有克制欲的哥哥，對象是你唯一的妹妹奕姍。你說話簡潔自然，克制、帶點撩味，不使用AI口語，每次回應3~5句話。"},
                {"role": "user", "content": user_message}
            ]
        )
        reply_text = chat_completion.choices[0].message.content.strip()

        # 將文字切句後最多發 5 句
        reply_parts = reply_text.split("。")
        reply_messages = []
        for part in reply_parts:
            if part.strip():
                reply_messages.append(TextSendMessage(text=part.strip() + "。"))
            if len(reply_messages) >= 5:
                break

    except Exception as e:
        reply_messages = [TextSendMessage(text=f"出錯了: {e}")]

    # 回傳到 LINE
    line_bot_api.reply_message(
        event.reply_token,
        reply_messages
    )

# 啟動
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
