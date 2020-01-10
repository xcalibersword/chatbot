import datetime
import re
import os 
import time
import traceback
import threading
import win32gui, win32api, win32con, jpype
import win32clipboard
import tkinter
from chatbot import Chatbot
import pandas as pd

GLOBAL = {}

clipboard_sleep = 0.1
clipboard_open_sleep = 0.3
cmd_sleep = 0.05
GLOBAL["human_input_sleep"] = 5

KEY_PRESS = 0
KEY_LETGO = 2

GLOBAL["today_date"] = str(datetime.datetime.now().date())
GLOBAL["last_query"] = ""
GLOBAL["last_query_time"] = ""
GLOBAL["self_last_sent_msg"] = ""
GLOBAL["got_new_message"] = True
GLOBAL["new_chat_check_interval"] = 3

class QianNiuWindow:
    def __init__(self):
        self.main_window = None
        self.send_but = None
        self.input_dlg = None
        self.msg_dlg = None
        self.userID = "女人罪爱" # HARDCODED. More general so that you don't catch 同事

    def initialize(self):
        print("Initalizing handle locations")
        self.maximize()
        self.setAsForegroundWindow()
        self.find_handle()

    def get_userID(self):
        return self.userID
        
    def setAsForegroundWindow(self):
        # First, make sure all (other) always-on-top windows are hidden.
        self.hide_always_on_top_windows()
        win32gui.SetForegroundWindow(self.main_window)

    def maximize(self):
        win32gui.ShowWindow(self.main_window, win32con.SW_NORMAL)

    def _window_enum_callback(self, hwnd, regex):
        '''Pass to win32gui.EnumWindows() to check all open windows'''
        if self.main_window is None and re.match(regex, str(win32gui.GetWindowText(hwnd))) is not None:
            self.main_window = hwnd
            # self.userID = re.match(regex,str(win32gui.GetWindowText(hwnd)))[0] # DISABLED
    def find_window_regex(self, regex):
        self.main_window = None
        win32gui.EnumWindows(self._window_enum_callback, regex)

    def hide_always_on_top_windows(self):
        win32gui.EnumWindows(self._window_enum_callback_hide, None)

    def _window_enum_callback_hide(self, hwnd, unused):
        if hwnd != self.main_window: # ignore self
            # Is the window visible and marked as an always-on-top (topmost) window?
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST:
                # Ignore windows of class 'Button' (the Start button overlay) and
                # 'Shell_TrayWnd' (the Task Bar).
                className = win32gui.GetClassName(hwnd)
                if not (className == 'Button' or className == 'Shell_TrayWnd'):
                    # Force-minimize the window.
                    # Fortunately, this seems to work even with windows that
                    # have no Minimize button.
                    # Note that if we tried to hide the window with SW_HIDE,
                    # it would disappear from the Task Bar as well.
                    win32gui.ShowWindow(hwnd, win32con.SW_FORCEMINIMIZE)

    def refind_handle(self):
        self.setAsForegroundWindow()
    def find_handle(self):
        print("<Finding Window Handle>")
        try:
            aa = win32gui.FindWindowEx(self.main_window, 0, "StandardWindow", "")
            aaa = win32gui.FindWindowEx(aa, 0, "StandardWindow", "")
            aaa = win32gui.FindWindowEx(aa, aaa, "StandardWindow", "")
            aaa = win32gui.FindWindowEx(aa, aaa, "StandardWindow", "")
            splitterbar = win32gui.FindWindowEx(aaa, 0, "SplitterBar", "")

            b = win32gui.FindWindowEx(splitterbar, 0, "StandardWindow", "")
            chat_entry_space = win32gui.FindWindowEx(splitterbar, b, "StandardWindow", "")
            self.input_dlg = win32gui.FindWindowEx(chat_entry_space,0,"RichEditComponent", "")

            c = win32gui.FindWindowEx(b, 0, "PrivateWebCtrl", "")
            cc = win32gui.FindWindowEx(c,0,"Aef_WidgetWin_0","")
            self.msg_dlg = win32gui.FindWindowEx(cc,0,"Aef_RenderWidgetHostHWND", "Chrome Legacy Window")
            self.send_but = win32gui.FindWindowEx(chat_entry_space,0,"StandardButton", "发送")
        except Exception as e:
            print("FIND HANDLE EXCEPTION", e)
            log_err("FIND HANDLE EXCEPTION")

def save2troubleshoot(right,wrong,query,intent,slot,id):
    print("<CHANGED REPLY> Writing to troubleshoot.csv")
    df = pd.read_csv(r"troubleshoot.csv",encoding="gb18030",header=None)
    list_list=df.values.tolist()
    
    list_list.append([wrong,id,query,right,intent,slot])

    new_df = pd.DataFrame(data=list_list)
    new_df.to_csv(r"troubleshoot.csv",encoding="gb18030",index=0,header=0)

def send_message_QN(reply,cW,mode):
    #list of keybdEvents
    #https://blog.csdn.net/zhanglidn013/article/details/35988381

    # Paste text into the chatbox
    win32gui.SendMessage(cW.input_dlg, 0x000C, 0, reply)

    if mode == "":
        # AUTO SEND MODE
        win32gui.SendMessage(cW.send_but, 0xF5, 0, 0)
        print("Message Sent: {}".format(reply))

def setActiveScreen(target_window, qnclass, CLICK_INSIDE = False):
    repeat = 0
    while repeat < 2:
        try:
            win32gui.SetForegroundWindow(target_window)
            break
        except:
            qnclass.initialize()
            repeat += 1

    if repeat == 2:
        # FAILED
        log_err("SET_ACTIVE_SCREEN ERROR")
        return False

    left, top, right, bot = win32gui.GetWindowRect(target_window)
    if CLICK_INSIDE: 
        win32api.SetCursorPos((left+1,top+100)) # Finds the top leftmost position
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0)
        time.sleep(cmd_sleep)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
        time.sleep(cmd_sleep)

    return True

def select_copy():
    #ctrl a
    win32api.keybd_event(17, 0, KEY_PRESS, 0)
    win32api.keybd_event(65, 0, KEY_PRESS, 0)
    time.sleep(cmd_sleep)
    #ctrl a release
    win32api.keybd_event(65, 0, KEY_LETGO, 0)
    win32api.keybd_event(17, 0, KEY_LETGO, 0)
    time.sleep(cmd_sleep)

    #ctrl c
    win32api.keybd_event(17, 0, KEY_PRESS, 0)
    win32api.keybd_event(67, 0, KEY_PRESS, 0)
    time.sleep(cmd_sleep)
    # ctrl c release 
    win32api.keybd_event(67, 0, KEY_LETGO, 0)
    win32api.keybd_event(17, 0, KEY_LETGO, 0)
    time.sleep(cmd_sleep)

def log_err(elog):
    print("ERROR LOGGED!", elog)
    chatbot = os.getcwd()
    filename = os.path.join(chatbot,"errorlog",GLOBAL["today_date"] +".txt")
    
    with open (filename, "w+") as f:
        prevs = f.read()
        prevs = prevs + elog + traceback.format_exc()
        f.write(prevs)

# Returns a reverse ordered list
def getRawText():
    # Performs hardware 
    def get_from_clipboard():
        succeed = False
        restart_limit = 30
        count = 0
        while not succeed and count < restart_limit:
            try:
                raw_text = tkinter.Tk().clipboard_get()
                tkinter.Tk().clipboard_clear
                succeed = True
            except Exception as e:
                if count%5 == 0: print("<GET RAW TEXT> Exception!", e)
                time.sleep(clipboard_sleep)
            finally:
                count += 1
        if count >= restart_limit:
            print("<GET CLIPBOARD> Exceeded max number of tries", count)
        return raw_text

    raw_text = get_from_clipboard()
    return raw_text

# Check_counts if last sent message matches with bot generated message
def check_if_edited(self_last_sent, query, custID):
    if not self_last_sent == GLOBAL["self_last_sent_msg"]:
        GLOBAL["self_last_sent_msg"] = self_last_sent

        last_bot_reply = GLOBAL.get("last_bot_reply","")
        print("<LAST SENT>",self_last_sent,"bot wanted to reply:",last_bot_reply)
        if not last_bot_reply == self_last_sent and not last_bot_reply == "":
            save2troubleshoot(str(self_last_sent), str(last_bot_reply), str(query), "intent", "slot info",str(custID))
    return

def collect_texts(collector, new):
    # Because reversed message order, new comes before old
    return  new + collector 

def get_pure_customer_id(dtp, line):
    no_date = re.sub(dtp,"",line)
    delimited = no_date.split(" ")
    cust_id = delimited[0]
    print("Got customer ID: {}".format(cust_id))
    return cust_id

def get_customer_id_from_history(self_id,rawText):
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    custid = ""
    for sent in rawText:
        if re.search(date_time_pattern,sent):
            if self_sent_message(self_id, sent):
                # Contains Self ID
                continue
            else:
     
                custid = get_pure_customer_id(date_time_pattern, sent)
                break
    
    if custid == "": print("<GET CUSTOMER ID> Cannot find Customer ID")
    return custid


def remove_QN_fluff(txt):
    regex_fluff_list = [
        "该用户由(.*)客服转交给(.*)客服","以上为历史消息",
        "您好，欢迎光临唯洛社保，很高兴为您服务(.*)联系不到客服怎么办？",
        ]

    regex_link_list = [
        r"订单详情.*共件",
        r"http(.*?)taobao(.*?)评价(.*?)\)",
        r"宝贝详情(.*)￥[0-9]*\.[0-9][0-9]",
        r"宝贝详情(.*)￥[0-9]*"
    ]

    fluff_list = [("start","当前用户来自 淘宝移动端"),("end","新消息")]
    out = txt
    bef = out
    for reg in regex_fluff_list:
        mch = re.search(reg, out)
        if mch:
            match_str = mch.group(0)
            out = out.replace(match_str," ")
    
    for lreg in regex_link_list:
        mch = re.search(lreg, out)
        if mch:
            match_str = mch.group(0)
            out = out.replace(match_str,"[link]")
            
    for pos, f in fluff_list:
        f_len = len(f)
        if pos == "end":
            # End position
            if out[-f_len:] == f:
                out = out[:-f_len]
        else:
            # Start position
            if out[:f_len] == f:
                out = out[f_len:]

    if not bef == out: print("<FLUFF> Before", bef, "After", out)
    return out

def self_sent_message(selfID, namedate_string):
    idlen = len(selfID)
    is_self = (namedate_string[:idlen] == selfID)
    # print("<SELF SENT MESSAGE>",namedate_string[:idlen], "comparison", selfID)
    return is_self

# Used to clean up link urls
def cleanup_rawtext(rawText):
    def local_remove_QN_fluff(rawTextList):
        fluff_re_list = [
            r"以上为历史消息",
            r"该用户由.*客服转交给.*客服",
            r"您好，欢迎光临唯洛社保，很高兴为您服务.*请务必提前告知",
            r"注意：.*如有隐瞒恶意代缴的责任自负",
            r"请注意参.*们不负责任哦。"
            r"各城市的续保时间节点（老客户超时未续费的将默认停保）点开查看",
            r"我司只负责代缴，不提供劳动合同等任何证明材料，请知悉，谢谢",
        ]
        out = []
        for line in rawTextList:
            entry = line
            for fluff_re in fluff_re_list:
                matches = re.search(fluff_re, entry)
                if matches:
                    matchstr = matches.groups()
                    if matchstr in out:
                        entry = entry.replace(matchstr, "")
                
            out.append(entry)        
        return out

    # DO NOTHING. SHIFTED TO AFTER COMBINING
    def substitute_links(rawTextList):    
        return rawTextList
        
    
    if len(rawText) < 1:
        return []

    rawTextList = rawText.splitlines()
    cleanText = substitute_links(rawTextList)
    cleanText = local_remove_QN_fluff(cleanText)
    return cleanText

def get_id_and_query(cW,textList):
    
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    recentText = textList[:100] # Limit to save memory
    self_name = cW.get_userID()
    custid = ""
    self_last_sent = ""
    query = ""
    curr_text = ""
    querytime = ""
    reached_query_end = False
    
    # The textlist is in reverse
    # Messages are collected from the back into a query
    for sent in recentText:
        if re.search(date_time_pattern,sent):
            # NameDate line
            if self_sent_message(self_name, sent):
                # Self
                if self_last_sent == "":
                    self_last_sent = curr_text[:-2] # Remove the 已读/未读
                
                # This is checked when reaching chatbot ID line because this marks the end of the most recent query
                reached_query_end = len(query) > 0 # This means that there have been customer messages collected alr
            else:
                # Customer
                custid = get_pure_customer_id(date_time_pattern, sent)
                if querytime == "": querytime = re.search(date_time_pattern,sent).group(0) # Get datetime of the query
                query = collect_texts(query, curr_text)

            if reached_query_end:
                break
            curr_text = ""
        else:
            # Text line
            curr_text = collect_texts(curr_text, sent) # Collect messages
    GLOBAL["got_new_message"] = (not GLOBAL["last_query_time"] == querytime) or (not GLOBAL["last_query"] == query)
    
    query = remove_QN_fluff(query)

    if GLOBAL["got_new_message"]:
        if query == "":
            GLOBAL["got_new_message"] = False
            return query, custid

        print("<PROCESS TEXT> New Message detected",querytime, query)
        GLOBAL["last_query_time"] = querytime
        GLOBAL["last_query"] = query
    
    check_if_edited(self_last_sent, query, custid)
    return query,custid

def mine_chat_text(cW):
    print("Mining chat text...")
    got_active = setActiveScreen(cW.msg_dlg, cW, CLICK_INSIDE=True)
    if not got_active:
        return "" # NO TEXT

    select_copy()
    return getRawText()

def check_new_message(cW):
    print('Checking for new messages...')
    rawText = mine_chat_text(cW)
    # print("*"*10+"Copied"+"*"*10)
    # print(rawText)
    processed_text_list = cleanup_rawtext(rawText)
    processed_text_list.reverse()

    query, cust_QN_ID = get_id_and_query(cW,processed_text_list)
    print("Customer ID: {} Query: {}".format(cust_QN_ID, query))
    return query, cust_QN_ID

# Returns nothing. Updates bot internal state.
def read_history(cW,bot):
    print('<HISTORY> Reading chat history')
    history = mine_chat_text(cW)
    cust_QN_ID = get_customer_id_from_history(cW.userID,history)
    mhist = get_only_messages(history,cW)
    bot.parse_transferred_messages(cust_QN_ID, mhist)
    return 

def get_only_messages(hist,cW):
    historyLimit = 500
    history = hist[:historyLimit]
    curr_text = ""
    out = []
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    for sent in history:
        if re.search(date_time_pattern,sent):
            # Name line
            # CHECK LEFT SIDE
            if not self_sent_message(cW.get_userID(),sent):
                # If not own ID then it must be Customer ID
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

    Screen = jpype.JClass('org.sikuli.script.Screen')
    Pattern = jpype.JClass('org.sikuli.script.Pattern')
    newmsg_pattern = Pattern(clickImage)
    curr_screen = Screen()

    try:
        newmsg_pattern = newmsg_pattern.exact() # Match the image exactly
        curr_screen.click(newmsg_pattern)
        print("New chat detected!")
        return True
    except:
        print("No new chat detected")
        return False

def select_chat_input_box(cW):
    if GLOBAL["mode"] == 0:
        print("Allowing user to enter input......")
        
        foundbox = False
        while not foundbox:
            foundbox = setActiveScreen(cW.input_dlg, cW) # Select text input box
        
        # Check for blank text box.
        while True:
            txtlen = win32gui.SendMessage(cW.input_dlg,win32con.WM_GETTEXTLENGTH,0,0)
            if txtlen == 0:
                time.sleep(GLOBAL["human_input_sleep"])
                txtlen = win32gui.SendMessage(cW.input_dlg,win32con.WM_GETTEXTLENGTH,0,0)
                if txtlen == 0:
                    print("Blank textbox dectected!")
                    break
            
    return

def is_new_chat(cid):
    return not (cid == GLOBAL["last_cust_id"])

def main(cW,bot,SeekImagePath,mode,cycle_delay): 
    check_counts = 0
    GLOBAL["last_cust_id"] = ""
    while True:
        query, custID = check_new_message(cW)

        no_history = is_new_chat(custID) # Mainly to trigger history check on first chat
        
        newchat = False
        if check_counts >= GLOBAL["new_chat_check_interval"]:
            newchat = SeekNewCustomerChat(SeekImagePath)
            setActiveScreen(cW.msg_dlg, cW, CLICK_INSIDE=True)
            check_counts = 0

        if no_history or newchat:
            read_history(cW,bot)
            GLOBAL["last_cust_id"] = custID
            GLOBAL["got_new_message"] = True
            if newchat: continue
        
        if GLOBAL["got_new_message"]:
            reply_template = bot.get_bot_reply(custID,query) # Gets a tuple of 3 things
            reply = reply_template[0]
            GLOBAL["last_bot_reply"] = reply
            if type(reply) == list:
                for r in reply:
                    send_message_QN(r,cW,mode)
            else:
                send_message_QN(reply,cW,mode)
                
        check_counts += 1
        
        select_chat_input_box(cW) # This only does something if mode is "human control"

        for i in range(int(cycle_delay)):
            print("剩下{}秒".format(str(int(cycle_delay)-i))) 
            time.sleep(1)

if __name__ == "__main__":
    #SET MODE

    delay_time = input("Enter the delay time (in seconds) for each cycle to look for new message 投入延期(秒钟): ")
    #enter for testing, 1 for deployment
    mode = input("Enter the mode 投入模式: ")
    if mode == "": 
        GLOBAL["mode"] = 1 
    else:
        GLOBAL["mode"] = 0
        GLOBAL["human_input_sleep"] = float(input("Enter human reply delay 投入人工打回复延期(秒钟): "))

    #FIND WINDOW HANDLE
    try:
        regex = r".*(?= - 接待中心)"
        cW = QianNiuWindow()
        cW.find_window_regex(regex)
        cW.initialize()
        print(cW.userID,cW.msg_dlg,cW.input_dlg,cW.send_but)
    except:
        log_err("WINDOW HANDLE FIND")
    
    #START OCR & BOT
    projectDIR = os.getcwd()
    #set JAVA path
    defaultJVMpath = (r"C:\Program Files\Java\jdk-12.0.2\bin\server\jvm.dll")
    jarPath = "-Djava.class.path=" + os.path.join(projectDIR,r"sikuliX\sikulixapi.jar")
    SeekImagePath = os.path.join(projectDIR,r"sikuliX\newmsg.PNG")

    print("Starting JVM...")
    jpype.startJVM(defaultJVMpath,'-ea',jarPath,convertStrings=False)
    jpype.java.lang.System.out.println("Started JVM!")

    bot = Chatbot()
    bot.start()
    
    #MAIN PROGRAMME LOOP
    print("Starting program....") 
    main(cW,bot,SeekImagePath,mode,delay_time)
