from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import os
import openai

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key initialization
openai.api_key = os.getenv('OPENAI_API_KEY')

# Conversation history storage
conversation_history = []

def GPT_response(messages):
    # Receive response
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5,
        max_tokens=500
    )

    # Extract GPT response
    answer = response['choices'][0]['message']['content']
    return answer

# Listen to all Post Requests from /callback
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Handle messages
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global conversation_history  # Declare as global variable
    msg = event.message.text

    # Add user message to conversation history
    conversation_history.append({"role": "user", "content": msg})
    
    try:
        GPT_answer = GPT_response(conversation_history)
        print(GPT_answer)

        # Add GPT response to conversation history
        conversation_history.append({"role": "assistant", "content": GPT_answer})
        
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=GPT_answer))
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage('你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息')
        )

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
