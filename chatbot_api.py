import sys
import socket
import subprocess as sp
from chatbot import Chatbot


def extract_data(request):
    # Returns whatever is after the 3rd nextline
    # GET...\n Host:... \n Connection:close \n <DATA>
    newline_count = 0
    for c in request:
        if c == "\n":
            newline_count += 1
    return request.split("\n")[newline_count]

def format_text(raw):
    clean = raw.replace("%20", " ")
    return clean

def decipher_data(data):
    first, second= data.split("&")
    chatID = first.split("=")[1] # Get the content after the "="
    msg = second.split("=")[1]
    return (chatID, msg)


def handle_request(bot, request, conn, addr):
    print("request is ", request)
    data = format_text(extract_data(request))
    chatID, incoming_message = decipher_data(data)
    print("ChatID: ", chatID, "message", incoming_message)

    reply_message = bot.recv_new_message(chatID, incoming_message)
    reply_content = chatID + "|" + reply_message

    print("CHATBOT relpying with:", reply_content)
    reply_packet = reply_content.encode()
    conn.sendall(reply_packet)
    return reply_content

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
        conn, addr = sock.accept()
        request = conn.recv(1024).decode() # Accept a message w length 1024
        print("We have a connection!")
        try:
            outcome = handle_request(bot, request, conn, addr)
            print(outcome)

        except Exception as e:
            print("EXCEPTION",e)

        # close connection
        conn.close()


p = sys.argv[1]
listen_forever(p)
