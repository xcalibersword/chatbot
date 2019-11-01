import win32clipboard as wc
import win32con
import pandas as pd
import numpy as np
from chatbot.data_utils import RawDataProcessor

# 获取剪切板内容
def getCopy():
    wc.OpenClipboard()
    t = wc.GetClipboardData(win32con.CF_UNICODETEXT)
    wc.CloseClipboard()
    return t

# 写入剪切板内容
def setCopy(str):
    wc.OpenClipboard()
    wc.EmptyClipboard()
    wc.SetClipboardData(win32con.CF_UNICODETEXT, str)
    wc.CloseClipboard()

w = RawDataProcessor()
custlist = np.array(pd.read_csv(r"D:\chatbot\data\quick fi.csv",encoding="utf-8")).tolist()
print(custlist)
for row in custlist:
    msg_string = row[0]
    new_msg = []
    for word in row[0]:
        new_msg.append(word)
    row[0] = " ".join(new_msg)
    if type(row[1]) == float:
        row[1] = w.label_intent(msg_string)
    if type(row[2]) == float:
        row[2] = w.label_slot(new_msg)
    print(row)

new_df = pd.DataFrame(data=custlist)
new_df.to_csv(r"D:\chatbot\data\quick_fixed.csv",index=False,encoding="utf-8")


    

