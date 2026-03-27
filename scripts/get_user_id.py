import os

from dotenv import load_dotenv
from flask import Flask, request
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent

load_dotenv()


from linebot.v3.messaging import (  # noqa: E402
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    print("你的 User ID 是：", user_id)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="收到訊息")]
            )
        )


if __name__ == "__main__":
    app.run(port=5000)