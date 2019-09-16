# ChatBot Supporting Variables (and functions)

import re

def DEFAULT_CONFUSED():
    return "不好意思，我听不懂"

def PREV_STATE_FLAG():
    return "299 PREV_STATE"

def CHINA_CITIES():
    cities = ["上海","北京","深圳","上海","上海","上海","杭州","广州"]
    return cities

def check_contain_zw(check_str):
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
        else:
            return False

def check_input_against_db(msg, db, exact = False):
    search_fn = lambda x,y: re.search(x,y)
    if exact:
        search_fn = lambda x,y: re.fullmatch(x,y)
    
    match = False
    for keyword in db:
        match = search_fn(keyword,msg)
        if match:
            break
    return match


if __name__ == "__main__":

    k = {
        "a": 1,
        "b": 2
    }
    td = {
        k["a"]:123
    }

    print(list(k.keys()))


# 2009年8月
# 2011年8月12日
# 北京 2011年8月12日

# TESTING REGEX
# Check if search allows trailing chars
# E.g. plan alakazam = plan a

if __name__ == "__main__":
    def chk(inp):
        mtch = re.search("[^ ]+(?=day)",inp)
        if mtch:
            print(mtch)
            print(mtch.group(0))    
        return
    while 1:
        i = input()
        chk(i)