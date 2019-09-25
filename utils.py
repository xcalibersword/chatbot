import threading,re
from win32gui import *
from chatbot import Chatbot
from win32api import *
import win32clipboard as w
import time
from jpype import *

def find_handle():
    #find all needed window handle
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

    count = 0
    last_not_user_idx_list = []
    last_user_idx = 0
    cust_QN_ID = ""
    for word in processed_text_list:
        if date_time_pattern.search(word):
            if not user_pattern.search(word):
                last_not_user_idx_list.append(count)
                cust_QN_ID = date_time_pattern.sub("",processed_text_list[last_not_user_idx_list[0]])
            else:
                last_user_idx = count
                last_not_user_idx_list.clear()      
        count += 1

    unanswered_convo = []
    if len(last_not_user_idx_list) > 0: 
        if last_not_user_idx_list[-1] > last_user_idx:
            print("message found!")
            for line in processed_text_list[last_not_user_idx_list[0]:]:
                if not date_time_pattern.search(line):
                    unanswered_convo.append(line)
                if unanswered_convo == []:
                    print("emoji detected!")
                    unanswered_convo.append(" ")
                      
    return unanswered_convo, cust_QN_ID

def SeekNewMessage():
    print("Finding new chat...")
    # C:\Program Files\Java\jdk1.8.0_181\jre\bin\server\jvm.dll
    print(getDefaultJVMPath())
    startJVM(getDefaultJVMPath(), "-ea", r"C:\Users\Administrator\Desktop\code (unsorted)\BOT\Sikulix\sikulixapi.jar")
    java.lang.System.out.println("hello world")
    Screen = JClass("org.sikuli.script.Screen")
    screen = Screen()
    # r"F:\work\project\test\sikuli_test\imgs\Chrome.png" 你截取桌面上chrome图标的图片路径
    screen.doubleClick(r"C:\Users\Administrator\Desktop\code (unsorted)\BOT\A.PNG")
    shutdownJVM()

def main(text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot):
    
    message_list, custID = check_new_message(userID,text_out_hwnd)
    query = "".join(message_list)
    print(message_list,custID,query)
    
    if message_list == []:
        SeekNewMessage()
    else:
        reply = bot.get_bot_reply(custID,query)
        print(reply)
        send_message_QN(reply,text_in_hwnd,button_hwnd)
    timer = threading.Timer(2,main,[text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot])
    timer.start()

if __name__ == "__main__":
    text_in_hwnd,text_out_hwnd,button_hwnd = find_handle()
    bot = Chatbot()
    bot.start()
    userID = "tb584238398"

    main(text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot)
    