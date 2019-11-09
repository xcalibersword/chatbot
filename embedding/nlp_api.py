import json
import ast
import numpy as np
import jieba as jb
from keras.preprocessing.text import Tokenizer, tokenizer_from_json

if __name__ == "__main__":
    MAIN = True
    rootpath = ''
    from unzipper import get_vector_dict
else:
    MAIN = False
    rootpath = 'embedding/'
    from embedding.unzipper import get_vector_dict

from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences 

# model_filename = 'embedding/241019_1600_model.h5'
model_filename = rootpath+'API_model.h5'
w2v_filepath = "/Users/davidgoh/Desktop/sgns.weibo.bigram-char.bz2"
VDLIMIT = 60000 #35000 includes gongjijin

USE_WORD2VECTOR = False

def read_json(json_filename):
    try:
        with open(json_filename, 'r',encoding="utf-8") as f:
            data = json.loads(f.read(),encoding="utf-8")
        return data
    except Exception as e:
        print("Exception opening{}".format(json_filename), e)

class Predictor:
    def __init__(self, mf = model_filename):
        self.max_review_length = 30
        print("Initalizing Predictor...")
        self.pmodel = load_model(mf)
        self.pmodel.summary()
        # self.word2int = self._buildWordToInt()
        self.ignore_chars = {" ", ",", "?","？","。","，"}
        self.unknown_token_val = 0
        self._load_jsons()
        if USE_WORD2VECTOR: 
            self.w2v = get_vector_dict(w2v_filepath, limit = VDLIMIT)  
        else: 
            # self.w2v = list(map(lambda x: x[0],self.word2int))
            self.w2v = list(self.word2int.keys())

        print("Finished initalizing Predictor")

    def _load_jsons(self):
        print("Loading jsons...")
        loaded = read_json(rootpath+"yval_tokens.json")
        self.y_tokenizer = tokenizer_from_json(loaded)

        raw_word2int = read_json(rootpath+"xval_man_tokens.json")
        self.word2int = ast.literal_eval(raw_word2int)
        # print(self.word2int["_NA"],self.word2int["社保"])
        self.reverse_word_map = dict(map(reversed, self.y_tokenizer.word_index.items()))
        print("Done with jsons")
        return

    def _buildWordToInt(self):
        w2v = self.w2v
        count = 0
        if USE_WORD2VECTOR: count = 1
        d = {}
        for c in w2v:
            if not c in d:
                d[c] = count
                count += 1
        print("Found {} unique tokens".format(count+1))
        if MAIN: print(d)
        return d
    
    def predict(self, raw):
        arr = self.tokenize(raw)
        print("input_arr",arr)
        raw_pred = self.pmodel.predict(arr)[0] # We want a single prediction
        outdict = self.pred_to_word(raw_pred)
        return outdict

    # Tokenizes and converts to int
    def tokenize(self, string):
        jbstring = jb.cut(string,cut_all=True)
        word2int = self.word2int
        out = []
        for c in jbstring:
            # Converts to an int
            if c in word2int:
                t = word2int[c]
            else:
                t = self.unknown_token_val
            out.append(t)
        out = pad_sequences([out,], self.max_review_length, dtype = object, value=0)
        # print("out",out)
        return out

    def pred_to_word(self,pred):
        top = 3
        total = np.sum(pred)
        s_pred = np.sort(pred,-1)
        best = None
        breakdown = ""
        rel_threshold = 50
        DEFAULT_RETURN = "complicated"
        for i in range(top):
            curr_mag = s_pred[-1]
            if curr_mag == 0:
                break
            s_pred = s_pred[:-1]
            idx = np.where(pred == curr_mag)[0][0]
            intent = self.reverse_word_map[idx]
            conf = (curr_mag*100/total)//0.1/10
            if (best == None) and conf >= rel_threshold: best = intent 
            breakdown = breakdown + "<{}> Intent:{} Confidence:{}%\n".format(i+1, intent, conf)
        if (best == None): best = DEFAULT_RETURN
        out = {"prediction":best,"breakdown":breakdown}
        return out

    def predict_loop(self):
        while 1:
            print("Please enter an input: (press ctrl+d to end)")
            raw_inp = input()
            inp = self.tokenize(raw_inp)
            # print("pro in",inp)
            out = self.pmodel.predict([inp])[0]
            p_out = self.pred_to_word(out)
            print(p_out)

if MAIN:    
    test_ins = ["我在上海","我要付社保","交公积金","您好","哦了解", "拍好了", "怎么拍", "一共多少钱啊", "我好爱您哦", "代缴社保", "落户苏州", "上海社保可以吗", "我不太懂哦","社保可以补交吗","需要我提供什东西吗","要啥材料吗","请问可以代缴上海社保吗"]
    # for testin in testins:
    #     print(jb.lcut(testin,cut_all=True))
    # exit()

    print("Please enter the model filename")
    nmf = input()
    if len(nmf) < 2:
        nmf = model_filename

    pp = Predictor(nmf)

    for testin in test_ins:
        out = pp.predict(testin)
        print("In:",testin,"Predicted Intent:",out)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    pp.predict_loop()