# encoding: utf-8

import asyncio
import sys
import socketio
from aiohttp import web
from chatbot import Chatbot

# This file opens a server that is a front for the chatbot. 
# Right now it defaults to localhost:8080 due to aiohttp

sio = socketio.AsyncServer()
app = web.Application() # This is implicitly an aiohttp apparently
sio.attach(app)


welcome_msg = "您好，欢迎光临唯洛社保，很高兴为您服务。本店现在可以代缴上海、北京、长沙、广州、苏州、杭州、成都的五险一金。请问需要代缴哪个城市的呢？需要从几月份开始代缴呢？注意：社保局要求已怀孕的客户（代缴后再怀孕的客户不受影响）和重大疾病或者慢性病状态客户，我司不能为其代缴社保，如有隐瞒恶意代缴的责任自负！请注意参保手续开始办理后，无法退款。"

def init_chatbot():
    bot = Chatbot()
    bot.start()
    return bot

# Initalize chatbot
bot = init_chatbot()

def robotify(msg):
    return "<机器人>: " + str(msg)

def get_bot_reply(bot, cid, message):
    replytext = bot.get_bot_reply(cid,message)
    reply = robotify(replytext)
    return reply

def display_own_message(msg):
    return "<您>: " + str(msg)

def index(request):
    indexfilepath = 'testing_server/index.html'
    with open(indexfilepath) as f:
        return web.Response(text = f.read(), content_type = 'text/html')

@sio.event
async def connect(sid, environ):
    sio.enter_room(sid, sid) # Take a client and put them into a room that is their socket ID
    print("####### New connection! #######")
    print("Contacted by someone at", sid)
    greet = robotify(welcome_msg)
    await sio.emit('message', greet, room=sid)

@sio.event
async def disconnect(sid):
    print('disconnect', sid)

@sio.on('chat')
async def chat_message(sid, msg):
    await sio.emit('message',display_own_message(msg),room=sid)
    print("Recieved from",sid,"Content:",msg)
    reply = get_bot_reply(bot, sid, msg)
    await sio.emit('message', reply, room=sid)

app.router.add_get('/', index)

if __name__ == '__main__':
    web.run_app(app, port = 8080)