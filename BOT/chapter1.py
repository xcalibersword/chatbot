import random
import re

pattern = "你还记得(.*)吗？"

name = {
    "你的名字是什么？": [
        "我是回音机器人",
        "他们叫我草人",
        "我名回音，姓机器人"
    ],
}

weather = {
    "今天天气怎样？":"今天{}"
}

random_chat = [
    "多说一点！",
    "为什么你那么认为？"
]

weather_today = "乌云密布"

def swap_pronouns(phrase):
    if "我" in phrase:
        return re.sub("我","你",phrase)
    if "你" in phrase:
        return re.sub("你","我",phrase)
    else:
        return phrase

def reply(msg):
    if msg in name:
        return random.choice(name[msg])
    elif msg in weather:
        return weather[msg].format(weather_today)
    elif len(msg) > 10:
        return random.choice(random_chat)
    else:
        return "我听得到，你说{}".format(msg)

def initiate_bot():
    while 1==1:
        msg = input()
        match = re.search(pattern,msg)
        if match:
            match = swap_pronouns(match)
            print("当然记得{}啊！".format(match.group(1)))
        else:
            print(reply(msg))

if __name__ == "__main__":
    initiate_bot()