# ChatBot Supporting Variables (and functions)
import os
import re
import json


WRITE_TO_FILE = 0 # Switch to turn of writing for testing purposes.


def DEFAULT_CONFUSED():
    return ["不好意思,我听不懂","不好意思,我不明白亲说啥"]

def PREV_STATE_FLAG():
    return "299 PREV_STATE"

def CHINA_CITIES():
    cities = ["上海","北京","深圳","杭州","广州", "上海", "成都", "shanghai", "beijing"]
    return cities

# Digits in regex form
def DIGITS():
    return "[零一二三四五六七八九十|0-9]"

def DIGITSET():
    return {0,1,2,3,4,5,6,7,8,9}

def INFO_GATHER_STATE_KEY():
    return "221 recv info"

# def INFO_GATHER_STATE_REPLIES():
#     return 

def is_number(n):
    return isinstance(n, float) or isinstance(n, int)

# Converts a string number to real number
def conv_numstr(n,wantint = False):
    cnvrt = (lambda n: int(n)) if wantint else (lambda n: float(n))

    try:
        con = cnvrt(n)
        print("raw",n)
        return con
    except ValueError:
        #if DEBUG: print("Tried to convert {} to float and failed".format(n))
        return n

def NO_INTENT():
    return {
        "key":"unknown",
        "replies": DEFAULT_CONFUSED()
    }

def state_key_dict(states):
    ks = states.keys()
    out = {}
    for k in ks:
        out[k] = states[k]["key"]
    return out

def getstatekey(state):
    # print("SSAD",state)
    return state["key"]

def CITY():
    return "city"

def check_contain_zw(check_str):
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
        else:
            return False

def list_to_regexList(lst):
        re_list = ""
        for e in lst:
            re_list = re_list + e + "|"
        re_list = re_list[:-1] # Remove last char

        return re_list

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

def dump_to_json(filename, data, DEBUG = 0, OVERRIDE = 0):
    if not WRITE_TO_FILE and not OVERRIDE: 
        print("<BACKEND WARNING: Writing to file has been disabled> Restore it in cbsv.py\n {} remains unchanged".format(filename))
        return
    try:
        with open(filename,'w+', encoding='utf8') as f:
            json.dump(data, f, indent = 4, ensure_ascii=0)
        if DEBUG: print("Finished writing to " + str(filename))
        
    except FileNotFoundError as fnf_error:
        print(fnf_error)
    

def read_json(json_filename):
    try:
        with open(json_filename, 'r',encoding="utf-8") as f:
            data = json.loads(f.read(),encoding="utf-8")
        return data
    except Exception as e:
        print("Exception opening{}".format(json_filename), e)
        return ()
        

def check_file_exists(filepath):
    return os.path.isfile(filepath)

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