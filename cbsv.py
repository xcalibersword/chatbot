
def DEFAULT_CONFUSED():
    return "不好意思，我听不懂"

def PREV_STATE_FLAG():
    return "299 PREV_STATE"


if __name__ == "__main__":
    k = {
        "a": 1,
        "b": 2
    }
    td = {
        k["a"]:123
    }

    print(list(k.keys()))