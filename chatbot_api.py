import sys
import socketio
import requests
import subprocess as sp
from aiohttp import web
from chatbot import Chatbot

chatbot_api_PORT = 8881
chatbot_api_url = "localhost:"+str(chatbot_api_PORT)
sio = socketio.AsyncServer(async_mode = 'aiohttp')
app = web.Application()
sio.attach(app)

def extract_data(request):
    # Returns whatever is after the 3rd nextline
    # GET...\n Host:... \n Connection:close \n <DATA>
    newline_count = 0
    for c in request:
        if c == "\n":
            newline_count += 1
    data = request.split("\n")[newline_count]
    reply_port = request.split("\n")[newline_count-1]
    return (data, reply_port)

def format_text(raw):
    clean = raw.replace("%20", " ")
    return clean

def decipher_data(data):
    first, second= data.split("&")
    chatID = first.split("=")[1] # Get the content after the "="
    msg = second.split("=")[1]
    return (chatID, msg)

def package_data(data, return_address):
    def post_header():
        header = {
            'Connection': "keep-alive",
            'Accept': "text/html",
            'Accept-Encoding': 'utf-8'
        }
        return header
    edata = data
    print("returnadd", return_address, " edata",edata)
    res = requests.post(return_address, data=edata)
    print("r url", res.url)
    print("replying request raw",res)
    print("reply in string", res.text)
    print("res content", res.content)
    return res.content

def handle_request(bot, request, client, addr):
    print("request is:\n" + request)
    data, reply_port = extract_data(request)
    data = format_text(data)
    chatID, incoming_message = decipher_data(data)
    print("ChatID:", chatID, "Message:", incoming_message)
    reply_message = bot.recv_new_message(chatID, incoming_message)
    reply_content = {"chatid":chatID, "text":reply_message}

    return_addr = "http://localhost:" + str(reply_port)

    packet = package_data(reply_content, return_addr)
    # client.send(packet)
    # print('Send %s bytes back to %s' % (packet, return_addr))
    return 

def listen_forever(port):
    port = int(port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("",port))
    print("Listening to port <", port, ">")
    
    bot = Chatbot()
    bot.start()

    while True:
    # while False:
        sock.listen(5) # 5 connections max
        client, addr = sock.accept()
        request = client.recv(1024).decode() # Accept a message w length 1024
        print("We have a connection!")
        try:
            outcome = handle_request(bot, request, client, addr)

        except Exception as e:
            print("EXCEPTION",e)

        # close connection
        client.close()

@sio.event
def message(data):
    print("I have gotten mail", data)

@sio.event
def connect(sid, environ):
    print("A connection!")
    print("Contacted by someone at", sid)

@sio.event
def disconnect(sid):
    print('disconnect', sid)

def emit_data(cID, reply):
    sio.emit('chat reply', {'chatID':cID, 'message':reply})


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Chatbot_API: Port not provided. Exiting")
        exit()
    p = sys.argv[1]

    app.listen(chatbot_api_PORT)
    web.run_app(app)
