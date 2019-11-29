import threading,re,os,time
import win32gui,win32api,win32clipboard,win32con,jpype
import pandas as pd
from chatbot import Chatbot
import traceback

class QianNiuWindow:
    def __init__(self):
        self.main_window = None
        self.send_but = None
        self.input_dlg = None
        self.msg_dlg = None
        self.userID = None

    def SetAsForegroundWindow(self):
        # First, make sure all (other) always-on-top windows are hidden.
        self.hide_always_on_top_windows()
        win32gui.SetForegroundWindow(self.main_window)
    def Maximize(self):
        win32gui.ShowWindow(self.main_window, win32con.SW_MAXIMIZE)
    def _window_enum_callback(self, hwnd, regex):
        '''Pass to win32gui.EnumWindows() to check all open windows'''
        if self.main_window is None and re.match(regex, str(win32gui.GetWindowText(hwnd))) is not None:
            self.main_window = hwnd
            self.userID = re.match(regex,str(win32gui.GetWindowText(hwnd)))[0]
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
    def find_handle(self):
        aa = win32gui.FindWindowEx(self.main_window, 0, "StandardWindow", "")
        aaa = win32gui.FindWindowEx(aa, 0, "StandardWindow", "")
        aaa = win32gui.FindWindowEx(aa, aaa, "StandardWindow", "")
        #aaa = win32gui.FindWindowEx(aa, aaa, "StandardWindow", "")
        aaaa = win32gui.FindWindowEx(aaa, 0, "SplitterBar", "")

        b = win32gui.FindWindowEx(aaaa, 0, "StandardWindow", "")
        bb = win32gui.FindWindowEx(aaaa, b, "StandardWindow", "")
        self.input_dlg = win32gui.FindWindowEx(bb,0,"RichEditComponent", "")

        c = win32gui.FindWindowEx(b, 0, "PrivateWebCtrl", "")
        cc = win32gui.FindWindowEx(c,0,"Aef_WidgetWin_0","")
        self.msg_dlg = win32gui.FindWindowEx(cc,0,"Aef_RenderWidgetHostHWND", "Chrome Legacy Window")
        self.send_but = win32gui.FindWindowEx(bb,0,"StandardButton", "发送")

def setActiveScreen(QN_output_hwnd):
    print("SetForegroundWindow...")
    win32gui.SetForegroundWindow(QN_output_hwnd)
    rect = win32gui.GetWindowRect(QN_output_hwnd)
    win32api.SetCursorPos((rect[2]-20,rect[1]+10))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
    
def select_copy():
    #ctrl a
    time.sleep(0.3)
    win32api.keybd_event(17, 0, 0, 0)
    win32api.keybd_event(65, 0, 0, 0)
    time.sleep(0.1)
    win32api.keybd_event(65, 0, 2, 0)
    win32api.keybd_event(17, 0, 2, 0)
    #ctrl c
    time.sleep(0.3)
    win32api.keybd_event(17, 0, 0, 0)
    win32api.keybd_event(67, 0, 0, 0)
    time.sleep(0.1)
    win32api.keybd_event(67, 0, 2, 0)
    win32api.keybd_event(17, 0, 2, 0)

def fromClipboard():
    win32clipboard.OpenClipboard(None)
    try:
        raw_text = win32clipboard.GetClipboardData(13)
    except Exception:
        print("Failed to retrieve clipboard data")
        print(Exception)
    win32clipboard.CloseClipboard()
    return raw_text

def processTextList(raw_text):
    raw_text_list = raw_text.splitlines()
    processed_text_list = []
    for sent in raw_text_list:
        sent = sent.strip()
        if sent != "" and sent != "以上为历史消息":
            processed_text_list.append(sent)
    processed_text_list.reverse()
    return processed_text_list

#transfer call pick up chat history
def processText(userID,rawText):
    date_time_pattern = re.compile(r"\d*-\d*-\d* \d{2}:\d{2}:\d{2}")
    idx = 0
    prevs_idx = 0
    query_list = []
    custid = ""
    for sent in rawText:
        if re.search(date_time_pattern,sent):
            if re.search(userID,sent):
                if re.search("-->",sent):
                    print("Detected transfer call!!!")
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

def save2troubleshoot(wrong,id,query,right,intent,slot):
    df = pd.read_csv(r"troubleshoot.csv",encoding="gb18030",header=None)
    list_list=df.values.tolist()
    
    list_list.append([wrong,id,query,right,intent,slot])

    new_df = pd.DataFrame(data=list_list)
    new_df.to_csv(r"troubleshoot.csv",encoding="gb18030",index=0,header=0)

def check_new_message(cW):
    print('Checking for new message...')
    setActiveScreen(cW.msg_dlg)
    select_copy()
    rawText = fromClipboard()
    text_list = processTextList(rawText)
    query,cust_QN_ID = processText(cW.userID,text_list)
    print("Query: {}".format(query))
    print("Customer ID: {}".format(cust_QN_ID))
    return query, cust_QN_ID

def SeekNewMessage(clickImage):
    print("Finding new chat...")

    Screen = jpype.JClass('org.sikuli.script.Screen')
    screen = Screen()

    try:
        screen.click(clickImage)
    except Exception:
        print("No new chat")

def send_message_QN(reply,cW,query,reply_template,custID,mode):
    #list of keybdEvents
    #https://blog.csdn.net/zhanglidn013/article/details/35988381

    #type text
    SendMessage(cW.input_dlg, 0x000C, 0, reply)

    if mode == "":
        SendMessage(cW.send_but, 0xF5, 0, 0)
        print("Message Sent: {}".format(reply))
    else:
        while True:
            if win32gui.GetWindowText(cW.input_dlg) == "":
                break

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

if __name__ == "__main__":

    try:
        regex = r".*(?= - 接待中心)"
        cW = QianNiuWindow()
        cW.find_window_regex(regex)
        cW.Maximize()
        cW.SetAsForegroundWindow()
        cW.find_handle()
        print(cW.userID,cW.msg_dlg,cW.input_dlg,cW.send_but)
    except:
        f = open("log.txt", "w")
        f.write(traceback.format_exc())
        print(traceback.format_exc())

    cd = input("Input cooldown: ")
    mode = input("Enter smth for not auto: ")

    projectDIR = os.getcwd()
    #set JAVA path
    defaultJVMpath = (r"C:\Program Files\Java\jdk-12.0.2\bin\server\jvm.dll")
    jarPath = "-Djava.class.path=" + os.path.join(projectDIR,r"sikuliX\sikulixapi.jar")
    SeekImagePath = os.path.join(projectDIR,r"sikuliX\A.PNG")

    print("Starting JVM...")
    jpype.startJVM(defaultJVMpath,'-ea',jarPath,convertStrings=False)
    jpype.java.lang.System.out.println("Started JVM!")

    bot = Chatbot()
    bot.start()
    
    print("Starting program....") 

    while True:
        query, custID = check_new_message(cW)    
        if not query == "":
            reply_template = bot.get_bot_reply(custID,query)
            reply = reply_template[0]
            if type(reply) == list:
                for r in reply:
                    send_message_QN(reply,cW,query,reply_template,custID,mode)
            else:
                send_message_QN(reply,cW,query,reply_template,custID,mode)
        SeekNewMessage(SeekImagePath)

        for i in range(int(cd)):
            print("Countdown: " + str(cd-i))
            time.sleep(1)



# while True:
#             txtlen = win32gui.SendMessage(cW.input_dlg,win32con.WM_GETTEXTLENGTH,0,0)
#             if txtlen == 0:
#                 time.sleep(GLOBAL["human_input_sleep"])
#                 txtlen = win32gui.SendMessage(cW.input_dlg,win32con.WM_GETTEXTLENGTH,0,0)
#                 if txtlen == 0:
#                     print("Message Sent!!!")
#                     break

# def err_log()

