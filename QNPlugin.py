import threading,re,os
from win32gui import *
from win32api import *
from win32clipboard import *
from win32con import *
from time import *
from jpype import *
from chatbot import Chatbot

def find_handle(userid):
    #spy++ | hard coded have to update if qianniu update their UI
    a = FindWindow("StandardFrame",userid + " - 接待中心")
    aa = FindWindowEx(a, 0, "StandardWindow", "")
    aaa = FindWindowEx(aa, 0, "StandardWindow", "")
    aaa = FindWindowEx(aa, aaa, "StandardWindow", "")
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
    #list of keybdEvents
    #https://blog.csdn.net/zhanglidn013/article/details/35988381

    #type text
    SendMessage(QN_input_hwnd, 0x000C, 0, text)
    #send text
    SendMessage(QN_sendBut_hwnd, 0xF5, 0, 0)
    print("Message Sent: {}".format(text))

def setActiveScreen(QN_output_hwnd):
    SetForegroundWindow(QN_output_hwnd)
    SetCursorPos((800,500))
    sleep(0.05)
    mouse_event(MOUSEEVENTF_LEFTDOWN,0,0,0,0)
    mouse_event(MOUSEEVENTF_LEFTUP,0,0,0,0)
    sleep(0.05)

def select_copy():
    #ctrl a
    keybd_event(17, 0, 0, 0)
    keybd_event(65, 0, 0, 0)
    sleep(0.05)
    keybd_event(65, 0, 2, 0)
    keybd_event(17, 0, 2, 0)
    #ctrl c
    sleep(0.05)
    keybd_event(17, 0, 0, 0)
    keybd_event(67, 0, 0, 0)
    sleep(0.05)
    keybd_event(67, 0, 2, 0)
    keybd_event(17, 0, 2, 0)
    sleep(0.05)
    
def getRawText():
    OpenClipboard()
    raw_text = GetClipboardData()
    CloseClipboard()
    raw_text_list = raw_text.splitlines()
    processed_text_list = []
    for sent in raw_text_list:
        sent = sent.strip()
        if sent != "" and sent != "以上为历史消息":
            processed_text_list.append(sent)
    processed_text_list.reverse()
    return processed_text_list

def processText(userID,rawText):
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    idx = 0
    prevs_idx = 0
    query_list = []
    custid = ""
    for sent in rawText:
        if re.search(date_time_pattern,sent):
            if re.search(userID,sent):
                break
            else:
                custid = re.sub(date_time_pattern,"",sent)
                for i in range(prevs_idx,idx):
                    query_list.append(rawText[i])
                prevs_idx = idx + 1
        idx += 1
    query_list.reverse()
    query = " ".join(query_list)
    return query,custid

def check_new_message(userID,QN_output_hwnd):
    print('Checking for new message...')
    setActiveScreen(QN_output_hwnd)
    select_copy()
    rawText = getRawText()
    query,cust_QN_ID = processText(userID,rawText)
    print("Query: {}".format(query))
    print("Customer ID: {}".format(cust_QN_ID))
    return query, cust_QN_ID

#insert image path here for the series of place for the OCR to click on
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
    
    if not query == "":
        reply_template = bot.get_bot_reply(custID,query)
        reply = reply_template[0]
        if type(reply) == list:
            for r in reply:
                send_message_QN(r,text_in_hwnd,button_hwnd)
        else:
            send_message_QN(reply,text_in_hwnd,button_hwnd)
    
    SeekNewMessage(SeekImagePath)

    #timer = threading.Timer(10,main,[text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot,SeekImagePath])
    #add something to stop the program
    #timer.start()

if __name__ == "__main__":
    userID = "女人罪爱:小梅"
    time = 10
    try:    
        text_in_hwnd,text_out_hwnd,button_hwnd = find_handle(userID)
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
    
    print("Starting program....") 
    while True:
        main(text_in_hwnd,text_out_hwnd,button_hwnd,userID,bot,SeekImagePath)
        sleep(time)