import bz2

ENCODING = "utf-8"
filepath = "/Users/davidgoh/Desktop/sgns.weibo.bigram-char.bz2"

print("target acquired")

ignore = {";","：",">","<"}

def get_vector_dict(filepath, limit = 50000):
    print("Fetching word2vec of size {}...".format(limit))
    vector_dict = {}
    target = bz2.BZ2File(filepath, 'rb')
    try:
        count = 0
        while count < limit:
            blinedata = target.readline(-1)
            if count > 0:
                linedata = blinedata.decode(ENCODING)
                # print("raw",blinedata)
                splitted = linedata.split(" ")
                token = splitted[0]
                vector_dict[token] = splitted[1:-1]
                
            count+=1 
    finally:
        target.close()

    entries = list(vector_dict.keys())
    print("Number of entries: {}".format(len(entries)))
    return vector_dict


