from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')


def GPT_response(text):
    # 接收回應
    response = openai.Completion.create(model="gpt-3.5-turbo-instruct", prompt=text, temperature=0.5, max_tokens=500)
    print(response)
    # 重組回應
    answer = response['choices'][0]['text'].replace('。','')
    return answer


# 監聽所有來自 /callback 的 Post Request
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


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        GPT_answer = GPT_response(msg)
        print(GPT_answer)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(event.reply_token, TextSendMessage('你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息'))
        

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


# 使用List記憶的對話

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rich import print as pprint

from dotenv import load_dotenv
load_dotenv()

# 初始化一個歷史對話列表，包含初始的系統訊息
messages = [
("system", "你只能根據我問的內容回答問題，並且記住我問的所有答案"),
]

# 設定LangChain的Chat模型與輸出解析器
chat = ChatOpenAI(temperature=.7, model='gpt-3.5-turbo')
str_parser = StrOutputParser()

  
# 建立一個函數來處理每次對話，並將歷史對話加入到Prompt中
def chat_with_memory(input_text):
    # 加入新的使用者訊息到歷史對話中
    messages.append(("human", input_text))
    # 將歷史對話轉換成適合LangChain的格式
    prompt_1 = ChatPromptTemplate.from_messages(messages)
    # 連接Prompt與Chat模型
    chain_1 = prompt_1 | chat | str_parser
    # 執行對話並獲取回應
    response = chain_1.invoke({"input": input_text})
    # 將AI的回應加入到歷史對話中
    messages.append(("ai", response))
    return response

# 進行對話循環，並不斷保存歷史對話
while True:
    question = input("請輸入問題:")
    if not question.strip():
        break
    response = chat_with_memory(question)

# 顯示AI回應
pprint(response)
        
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
