import re
import en_core_web_sm
import numpy as np


pattern_1 = re.compile('.* from (.*) to (.*)')
pattern_2 = re.compile('.* to (.*) from (.*)')


#get sentence vector for each label data and the test data -> contain in np.array -> cosine_similarity them -> np.argmax -> return the label based on this index
#from sklearn.metrics.pairwise import cosine_similarity

#\b : rather to match the "hi" in "which", we want to match hi as a word
#| : match either of these words
def prac1():
    pattern = r"\b(你好|在吗|hi|hello|hey)\b"
    message = "which one?"
    message1 = "hey there!"
    match = re.search(pattern,message)
    print(match)
    match = re.search(pattern,message1)
    print(match)

    pattern1 = re.compile('[A-Z]{1}[a-z]*')
    message2 = """
    Marry is a friend of mine,
    she studied at Oxford and
    now works at Google"""
    print(pattern1.findall(message2))

    return 0
#dict of intent and keywords
#create pattern using re.compile and "|".join()
#use pattern to identify intent then give the appriopriate response
pattern = re.compile('http.*')
while 1==1:
    msg = input("website: ")
    print(type(pattern.findall(msg)))
    if pattern.findall(msg) == []
        print('wonrg')
    print(type(pattern.match(msg)))