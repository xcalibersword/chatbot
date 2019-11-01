import numpy as np
import re
from chatbot.cbsv import *
import jieba_fast as jieba
import string
import win32clipboard as wc
import win32con

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

#city image 
#1 2|3 4|
def generate_slot(name_list,msg,pos_list_list):
    slot_list = ["O" for w in msg]

    if name_list != [""]:
        count = 0
        for item in pos_list_list:
            pos_list = item.split(" ")
            start = int(pos_list[0])
            if len(pos_list) > 1:
                end = int(pos_list[1])
            else:
                end = start
            if end == start:
                slot_list[start] = "B-" + name_list[count]
            else:
                slot_list[start] = "B-" + name_list[count]
                for i in range(end - start):
                    slot_list[start+i+1] = "I-" + name_list[count]
            count += 1
    return slot_list



def main():
    name_list = input("tag >>> ").split(" ")
    #name_list = ['']
    msg = input("msg >>> ").split(" ")
    a = []
    for pair in enumerate(msg):
        a.append(pair)
    print(a)
    pos_list_list = input("pos >>> ").split("|")
    #pos_list_list = ['']
    slot = generate_slot(name_list,msg,pos_list_list)
    setCopy(" ".join(slot))
if __name__ == "__main__":
    while True:
        main()