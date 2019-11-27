import threading,re,os
from win32gui import *
from win32api import *
from win32clipboard import *
from win32con import *
from time import *
from jpype import *
from chatbot import Chatbot
import pandas as pd

GLOBAL = {}

clipboard_sleep = 0.05
cmd_sleep = 0.05
GLOBAL["human_input_sleep"] = 5
self_userID = "temporary"

KEY_PRESS = 0
KEY_LETGO = 2

GLOBAL["last_query"] = ""
GLOBAL["last_query_time"] = ""
GLOBAL["last_sent_msg"] = ""
GLOBAL["got_new_message"] = True
GLOBAL["new_chat_check_interval"] = 3

def find_handle(userid):
    #spy++ | hard coded have to update if qianniu update their UI
    a = FindWindow("StandardFrame",userid + " - 接待中心")
    aa = FindWindowEx(a, 0, "StandardWindow", "")
    aaa = FindWindowEx(aa, 0, "StandardWindow", "")
    aaa = FindWindowEx(aa, aaa, "StandardWindow", "")
    aaa = FindWindowEx(aa, aaa, "StandardWindow", "") # Please have better names
    aaaa = FindWindowEx(aaa, 0, "SplitterBar", "")

    b = FindWindowEx(aaaa, 0, "StandardWindow", "")
    bb = FindWindowEx(aaaa, b, "StandardWindow", "")
    QN_input_hwnd = FindWindowEx(bb,0,"RichEditComponent", "") #Find chat message input box
    GLOBAL["QN_input_box"] = QN_input_hwnd

    c = FindWindowEx(b, 0, "PrivateWebCtrl", "")
    cc = FindWindowEx(c,0,"Aef_WidgetWin_0","")
    QN_output_hwnd = FindWindowEx(cc,0,"Aef_RenderWidgetHostHWND", "Chrome Legacy Window") # Find chat message display windows
    GLOBAL["QN_output_box"] = QN_output_hwnd

    QN_sendBut_hwnd = FindWindowEx(bb,0,"StandardButton", "发送") # Find send button
    GLOBAL["QN_send_button"] = QN_sendBut_hwnd

    return QN_input_hwnd,QN_output_hwnd,QN_sendBut_hwnd

def save2troubleshoot(right,wrong,query,intent,slot,id):
    df = pd.read_csv(r"troubleshoot.csv",encoding="gb18030")
    list_list=df.values.tolist()
    
    list_list.append([wrong,id,query,right,intent,slot])

    new_df = pd.DataFrame(data=list_list)
    new_df.to_csv(r"troubleshoot.csv",encoding="gb18030",index=0,header=0)

def send_message_QN(text,QN_input_hwnd,QN_sendBut_hwnd,query,reply_template,custID,mode):
    #list of keybdEvents
    #https://blog.csdn.net/zhanglidn013/article/details/35988381

    # Paste text into the chatbox
    SendMessage(QN_input_hwnd, 0x000C, 0, text)

    if mode == "":
        # AUTO SEND MODE
        SendMessage(QN_sendBut_hwnd, 0xF5, 0, 0)
        print("Message Sent: {}".format(text))
    else:
        # CONFIRMATION MODE
        # do nothing
        return

        # -- EVERYTHING BELOW HERE DOESNT HAPPEN -- 
        confirm = input("如果回复是对的请按回车键,不然请输入对的回答:  ")
        if confirm == "":
            #send text
            SendMessage(QN_sendBut_hwnd, 0xF5, 0, 0)
            print("Message Sent: {}".format(text))
        else:
            SendMessage(QN_input_hwnd, 0x000C, 0, confirm)
            SendMessage(QN_sendBut_hwnd, 0xF5, 0, 0)
            print("Message Sent: {}".format(text))
            save2troubleshoot(confirm,text,query,str(reply_template[1]),str(reply_template[2]),custID)

def setActiveScreen(target_window):
    SetForegroundWindow(target_window)

    rect = GetWindowRect(target_window)
    # Finds the top right position
    SetCursorPos((rect[2]-50,rect[1]+10))
    
    sleep(cmd_sleep)
    mouse_event(MOUSEEVENTF_LEFTDOWN,0,0,0,0)
    mouse_event(MOUSEEVENTF_LEFTUP,0,0,0,0)
    sleep(cmd_sleep)

def select_copy():
    #ctrl a
    keybd_event(17, 0, KEY_PRESS, 0)
    keybd_event(65, 0, KEY_PRESS, 0)
    sleep(cmd_sleep)
    #ctrl a release
    keybd_event(65, 0, KEY_LETGO, 0)
    keybd_event(17, 0, KEY_LETGO, 0)

    #ctrl c
    sleep(cmd_sleep)
    keybd_event(17, 0, KEY_PRESS, 0)
    keybd_event(67, 0, KEY_PRESS, 0)
    sleep(cmd_sleep)
    # ctrl c release 
    keybd_event(67, 0, KEY_LETGO, 0)
    keybd_event(17, 0, KEY_LETGO, 0)
    sleep(cmd_sleep)

# Returns a reverse ordered list
def getRawText():
    rpt = 0
    rpt_limit = 10
    succeed = False
    while not succeed and rpt < rpt_limit:
        try:
            OpenClipboard()
            succeed = True
        except Exception as e:
            print("OPEN CLIPBOARD EXCEPTION:",e,"Trying again...")
        rpt += 1

    sleep(clipboard_sleep)

    rpt = 0
    raw_text = ""
    while raw_text == "" and rpt < rpt_limit:
        try:
            raw_text = GetClipboardData()
        except Exception as e:
            print("GET CLIPBOARD EXCEPTION:",e,"Trying again...")
        rpt += 1

    sleep(clipboard_sleep)

    try:
        EmptyClipboard()
        succeed = True
    except Exception as e:
        print("EmptyClipboard EXCEPTION:",e)

    rpt = 0
    succeed = False
    while not succeed and rpt < rpt_limit + 10:
        try:
            CloseClipboard()
            succeed = True
        except Exception as e:
            print("CLOSE CLIPBOARD EXCEPTION:",e,"Trying again...")
        rpt += 1

    raw_text_list = raw_text.splitlines()
    processed_text_list = []
    for sent in raw_text_list:
        sent = sent.strip()
        if sent != "" and sent != "以上为历史消息":
            processed_text_list.append(sent)
    processed_text_list.reverse()
    return processed_text_list

def check_if_edited(last_sent, q, cid):
    if not last_sent == GLOBAL["last_sent_msg"]:
        GLOBAL["last_sent_msg"] = last_sent

        last_bot_reply = GLOBAL.get("last_bot_reply","")
        print("<LAST SENT>",last_sent,"bot wanted to reply:",last_bot_reply)
        if not last_bot_reply == last_sent and not last_bot_reply == "":
            save2troubleshoot(str(last_sent), str(last_bot_reply), str(q), "intent", "slot info",str(cid))
    return

def collect_texts(collector, new):
    # Because reversed message order, new comes before old
    return  new + collector 

def get_customer_id(self_userID,rawText):
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    custid = ""
    for sent in rawTest:
        if re.search(date_time_pattern,sent):
            if re.search(self_userID,sent):
                continue
            else:
                custid = custid = re.sub(date_time_pattern,"",sent)
                break
    
    if custid == "": print("<GET CUSTOMER ID> Cannot find Customer ID")
    return custid


def processText(self_userID,rawText):
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    recentText = rawText[:30]
    custid = ""
    last_sent = ""
    query = ""
    curr_text = ""
    querytime = ""
    print("RECENT TEXT", recentText[:10])
    for sent in recentText:
        if re.search(date_time_pattern,sent):
            # Name line
            if re.search(self_userID,sent):
                # Self
                if last_sent == "":
                    last_sent = curr_text[:-2] # Remove the 已读/未读
            else:
                # Customer
                custid = re.sub(date_time_pattern,"",sent)
                if querytime == "": querytime = re.search(date_time_pattern,sent).group(0)
                query = collect_texts(query, curr_text)

            if len(query) > 0 and len(last_sent) > 0:
                break
            curr_text = ""
        else:
            # Text line
            curr_text = collect_texts(curr_text, sent) # Collect messages
        
    if not GLOBAL["last_query_time"] == querytime:
        print("New Message deteced",querytime, query)
        GLOBAL["last_query_time"] = querytime
        GLOBAL["got_new_message"] = True
        GLOBAL["last_query"] = query
    else:
        GLOBAL["got_new_message"] = False

    check_if_edited(last_sent, query, custid)
    return query,custid

def mine_chat_text(text_win):
    setActiveScreen(text_win)
    select_copy()
    return getRawText()

def check_new_message(self_userID,textwindow):
    print('Checking for new messages...')
    rawText = mine_chat_text(textwindow)
    query, cust_QN_ID = processText(self_userID,rawText)
    print("Customer ID: {} Query: {}".format(cust_QN_ID, query))
    return query, cust_QN_ID

# Returns nothing. Updates bot internal state.
def read_history(selfID, bot, textwindow):
    print('<HISTORY> Reading chat history')
    history = mine_chat_text(textwindow)
    cust_QN_ID = get_customer_id(self_userID,history)
    mhist = get_only_messages(history)
    bot.parse_transferred_messages(cust_QN_ID, mhist)
    return 

def get_only_messages(hist):
    historyLimit = 500
    history = hist[:historyLimit]
    curr_text = ""
    out = []
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    for sent in history:
        if re.search(date_time_pattern,sent):
            # Name line
            if not re.search(self_userID,sent):
                # Customer
                # custid = re.sub(date_time_pattern,"",sent)
                # querytime = re.search(date_time_pattern,sent).group(0)
                out.append(curr_text)
            
            curr_text = ""
        else:
            # Text line
            curr_text = collect_texts(curr_text, sent) # Collect messages
    return out

#insert image path here for the series of place for the OCR to click on
def SeekNewCustomerChat(clickImage):
    print("Finding new chat...")

    Screen = JClass('org.sikuli.script.Screen')
    screen = Screen()

    try:
        screen.click(clickImage)
        return True
    except Exception:
        print("No new chat")
        return False

def select_chat_input_box():
    if GLOBAL["mode"] == 0:
        print("Allowing user to enter input......")
        input_box = GLOBAL["QN_input_box"]
        setActiveScreen(input_box) # Select text input box
        # #ctrl + right
        # keybd_event(17, 0, KEY_PRESS, 0)
        # keybd_event(39, 0, KEY_PRESS, 0)
        # sleep(cmd_sleep)
        # #ctrl + right release
        # keybd_event(39, 0, KEY_LETGO, 0)
        # keybd_event(17, 0, KEY_LETGO, 0)

        sleep(GLOBAL["human_input_sleep"])
    return

def main(text_in_hwnd,text_out_hwnd,button_hwnd,self_userID,bot,SeekImagePath,mode,cycle_delay): 
    checks = 0
    while True:
        query, custID = check_new_message(self_userID,text_out_hwnd)
        
        if GLOBAL["got_new_message"]:
            reply_template = bot.get_bot_reply(custID,query) # Gets a tuple of 3 things
            reply = reply_template[0]
            GLOBAL["last_bot_reply"] = reply
            if type(reply) == list:
                for r in reply:
                    send_message_QN(r,text_in_hwnd,button_hwnd,query,reply_template,custID,mode)
            else:
                send_message_QN(reply,text_in_hwnd,button_hwnd,query,reply_template,custID,mode)
                
        elif checks >= GLOBAL["new_chat_check_interval"]:
            newchat = SeekNewCustomerChat(SeekImagePath)
            checks = 0
            if newchat:
                read_history(self_userID, bot,text_out_hwnd)
                GLOBAL["got_new_message"] = True
                continue

        checks += 1
        select_chat_input_box() # This only does something if mode is "human control"
        sleep(float(cycle_delay))
    #timer = threading.Timer(10,main,[text_in_hwnd,text_out_hwnd,button_hwnd,self_userID,bot,SeekImagePath])
    #add something to stop the program
    #timer.start()

if __name__ == "__main__":
    self_userID = "女人罪爱:小梅"
    delay_time = input("Enter the delay time (in seconds) for each cycle to look for new message 投入延期(秒钟): ")
    #enter for testing, 1 for deployment
    mode = input("Enter the mode 投入模式: ")
    if mode == "": 
        GLOBAL["mode"] = 1 
    else:
        GLOBAL["mode"] = 0
        GLOBAL["human_input_sleep"] = float(input("Enter human reply delay 投入人工打回复延期(秒钟): "))

    try:    
        text_in_hwnd,text_out_hwnd,button_hwnd = find_handle(self_userID)
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
    main(text_in_hwnd,text_out_hwnd,button_hwnd,self_userID,bot,SeekImagePath,mode,delay_time)
