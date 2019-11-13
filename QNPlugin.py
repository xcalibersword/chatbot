import threading,re
from win32gui import *
from chatbot import Chatbot
from win32api import *
import win32clipboard as w
import time
from jpype import *
import os

def find_handle():
    #window handle | hard coded | spy++
    a = FindWindow("StandardFrame","tb584238398 - 接待中心")
    aa = FindWindowEx(a, 0, "StandardWindow", "")
    aaa = FindWindowEx(aa, 0, "StandardWindow", "")
    aaa = FindWindowEx(aa, aaa, "StandardWindow", "")
    aaaa = FindWindowEx(aaa, 0, "SplitterBar", "")

    b = FindWindowEx(aaaa, 0, "StandardWindow", "")
    bb = FindWindowEx(aaaa, b, "StandardWindow", "")
    QN_input_hwnd = FindWindowEx(bb,0,"RichEditComponent", "")

    c = FindWindowEx(b, 0, "PrivateWebCtrl", "")
    cc = FindWindowEx(c,0,"Aef_WidgetWin_0","")
    QN_output_hwnd = FindWindowEx(cc,0,"Aef_RenderWidgetHostHWND", "Chrome Legacy Window")

    QN_sendBut_hwnd = FindWindowEx(bb,0,"StandardButton", "发送")

    return QN_input_hwnd,QN_output_hwnd,QN_sendBut_hwnd

def send_message_QN(text,QN_input_hwnd,QN_sendBut_hwnd):
    #type text
    SendMessage(QN_input_hwnd, 0x000C, 0, text)
    #send text
    SendMessage(QN_sendBut_hwnd, 0xF5, 0, 0)
    print("Message Sent: {}".format(text))

def check_new_message(userID,QN_output_hwnd):
    print('Checking for new message...')
    SetForegroundWindow(QN_output_hwnd)
    #ctrl a
    keybd_event(0x11, 0, 0, 0)
    keybd_event(65, 0, 0, 0)
    time.sleep(0.5)
    keybd_event(0x11, 0, 2, 0)
    keybd_event(65, 0, 2, 0)
    #ctrl c
    keybd_event(0x11, 0, 0, 0)
    keybd_event(67, 0, 0, 0)
    time.sleep(0.5)
    keybd_event(0x11, 0, 2, 0)
    keybd_event(67, 0, 2, 0)

    w.OpenClipboard()
    raw_text = w.GetClipboardData()
    w.CloseClipboard()
    raw_text_list = raw_text.splitlines()

    processed_text_list = []
    for word in raw_text_list:
        if word.strip() != "":
            processed_text_list.append(word)

    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    user_pattern = re.compile(userID + r" \d*-\d*-\d* \d{2}:\d{2}:\d{2}")

    #identify where the impt messages are
    count = 0
    last_not_user_idx_list = []
    last_user_idx = 0
    cust_QN_ID = ""
    for word in processed_text_list:
        if date_time_pattern.search(word):
            if not user_pattern.search(word):
                last_not_user_idx_list.append(count)
                if cust_QN_ID == "":
                    cust_QN_ID = date_time_pattern.sub("",processed_text_list[last_not_user_idx_list[0]])
            else:
                last_user_idx = count
                last_not_user_idx_list.clear()      
        count += 1
    #retrieve the impt messages
    unanswered_convo = []
    if len(last_not_user_idx_list) > 0: 
        if last_not_user_idx_list[-1] > last_user_idx:
            print("New message found!")
            for line in processed_text_list[last_not_user_idx_list[0]:]:
                if not date_time_pattern.search(line):
                    unanswered_convo.append(line)
                # if unanswered_convo == []:
                #     print("Emoji detected!")
                #     unanswered_convo.append("[emoji]")
    query = " ".join(unanswered_convo)
    print("Query: {}".format(query))
    print("Customer ID: {}".format(cust_QN_ID))
    return query, cust_QN_ID

def SeekNewMessage(clickImage):
    print("Finding new chat...")

    Screen = JClass('org.sikuli.script.Screen')
    screen = Screen()

    try:
        screen.click(clickImage)
    except Exception:
        print("No new chat")

def main(text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot,SeekImagePath):   

    query, custID = check_new_message(userID,text_out_hwnd)
    
    if query == "":
        SeekNewMessage(SeekImagePath)
    else:
        #reply_template = bot.get_bot_reply(custID,query)
        #reply = reply_template[0]
        reply = query
        send_message_QN(reply,text_in_hwnd,button_hwnd)
        SeekNewMessage(SeekImagePath)
    #timer = threading.Timer(10,main,[text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot,SeekImagePath])
    #add something to stop the program
    #timer.start()

if __name__ == "__main__":
    try:    
        text_in_hwnd,text_out_hwnd,button_hwnd = find_handle()
    except Exception:
        print("Window Handle cannot be found!")

    projectDIR = os.getcwd()
    #set JAVA path
    defaultJVMpath = (r"C:\Program Files\Java\jdk-12.0.2\bin\server\jvm.dll")
    jarPath = "-Djava.class.path=" + os.path.join(projectDIR,r"sikuliX\sikulixapi.jar")
    SeekImagePath = os.path.join(projectDIR,r"sikuliX\A.PNG")

    print("Starting JVM...")
    startJVM(defaultJVMpath,'-ea',jarPath,convertStrings=False)
    java.lang.System.out.println("Started JVM!")

    bot = Chatbot()
    bot.start()
    
    userID = "tb584238398"
    print("Starting program....") 
    while True:
        main(text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot,SeekImagePath)
        time.sleep(10)