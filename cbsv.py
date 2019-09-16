import re

def DEFAULT_CONFUSED():
    return "不好意思，我听不懂"

def PREV_STATE_FLAG():
    return "299 PREV_STATE"

def CHINA_CITIES():
    cities = ["上海","北京","深圳","上海","上海","上海","杭州","广州"]
    return cities

if __name__ == "__main__":
    k = {
        "a": 1,
        "b": 2
    }
    td = {
        k["a"]:123
    }

    print(list(k.keys()))



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