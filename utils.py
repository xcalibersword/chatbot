import threading
from win32gui import *
from chatbot import Chatbot
import os

#hwnd
a = FindWindow("StandardFrame","tb584238398 - 接待中心")
aa = FindWindowEx(a, 0, "StandardWindow", "")
aaa = FindWindowEx(aa, 0, "StandardWindow", "")
aaa = FindWindowEx(aa, aaa, "StandardWindow", "")
aaaa = FindWindowEx(aaa, 0, "SplitterBar", "")

b = FindWindowEx(aaaa, 0, "StandardWindow", "")
b = FindWindowEx(aaaa, b, "StandardWindow", "")
bb = FindWindowEx(b,0,"RichEditComponent", "")
QN_text_hwnd = bb

print(QN_text_hwnd)

bot = Chatbot()
bot.start()

bot.get_bot_reply("MyUserId",input())

"""
        public IntPtr WidgetHost()
        {
            IntPtr aH = FindWindowEx(SplitterBar(), IntPtr.Zero, "StandardWindow", "");
            IntPtr bH = FindWindowEx(aH, IntPtr.Zero, "PrivateWebCtrl", "");
            IntPtr cH = FindWindowEx(bH, IntPtr.Zero, "Aef_WidgetWin_0", "");
            IntPtr dH = FindWindowEx(cH, IntPtr.Zero, "Aef_RenderWidgetHostHWND", "Chrome Legacy Window");
            return dH;
        }
        public IntPtr SendButton()
        {
            IntPtr aH = FindWindowEx(SplitterBar(), IntPtr.Zero, "StandardWindow", "");
            aH = FindWindowEx(SplitterBar(), aH, "StandardWindow", "");
            IntPtr bH = FindWindowEx(aH, IntPtr.Zero, "StandardButton", "发送");
            return bH;
        }


        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern int SendMessage(IntPtr hwnd, int wMsg, int wParam, string lParam);
        public void SendReplyToUser(string message)
        {
            //send message
            SendMessage(RichEditComponent(), 0x000C, 0, message);
            //click messagebox
            SendMessage(RichEditComponent(), 0xF5, 0, null);
            //click sendbutton
            SendMessage(SendButton(), 0xF5, 0, null);
            //AutoClick2();
        }

        [DllImport("USER32.DLL")]
        public static extern void keybd_event(byte bVk, byte bScan, int dwFlags, int dwExtraInfo);  //导入模拟键盘的方法
        [DllImport("USER32.DLL")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);  //导入为windows窗体设置焦点的方法
        public void CopyPasteMethod()
        {
            SetForegroundWindow(WidgetHost());
            //ctrl a
            keybd_event(0x11, 0, 0, 0);
            keybd_event(65, 0, 0, 0);
            Thread.Sleep(100);
            keybd_event(0x11, 0, 2, 0);
            keybd_event(65, 0, 2, 0);
            Thread.Sleep(100);
            //ctrl c
            keybd_event(0x11, 0, 0, 0);
            keybd_event(67, 0, 0, 0);
            Thread.Sleep(100);
            keybd_event(0x11, 0, 2, 0);
            keybd_event(67, 0, 2, 0);
            Thread.Sleep(100);
            string unparsed_text = Clipboard.GetText();
            String[] sArray = unparsed_text.Split('\n');
            List<string> list = new List<string>(sArray);

        """