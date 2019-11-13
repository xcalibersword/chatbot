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

    def _remove_symbols(self, s):
        for symbol in self.ignore_chars:
            s = s.replace(symbol,"")
        return s
    
    # MAIN METHOD
    def predict(self, raw):
        arr = self.tokenize(raw)
        print("input_arr",arr)
        raw_pred = self.pmodel.predict(arr)[0] # We want a single prediction
        outdict = self.pred_to_word(raw_pred)
        return outdict

    # Tokenizes and converts to int
    def tokenize(self, string):
        string = self._remove_symbols(string)
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
    # Test suite    
    test_ins = [
        ("我在上海，以前交过","inform"),
        ("我在北京，不是首次","inform"),
        ("苏州的，之前有开户口","inform"),
        ("哦好滴，解了","affirm"),
        ("社保基数怎么算","ask_how_much"),
        ("服务费怎么算","ask_how_much"),
        ("怀孕了还可以代缴吗","query_pregnant"),
        ("怀孕了还可以买吗","query_pregnant"),
        ("怎么去拍啊","how_to_pai"),
        ("我应该怎么拍","how_to_pai"),
        ("有没有链接？","request_link"),
        ("拍哪个宝贝？","request_link"),
        ("我想在北京买房","query_housing"),
        ("落户苏州","luohu"),
        ("我不太懂哦","confused"),
        ("没了，谢谢","deny"),
        ("没","deny"),
        ("之前交的社保可以补吗","ask_can_topup"),
        ("社保可不可以补缴？","ask_can_topup"),
        ("首次要提供什材料吗？","query_req_resources"),
        ("需要我提供什东西吗","query_req_resources"),
        ("要啥材料吗","query_req_resources"),
        ("请问可以代缴上海社保吗","purchase"),
        ("我想交5月社保不断的可以吗","purchase"),
        ("我是想要代缴","purchase"),
        ("我真的很爱您哦","complicated"),
        ("社保交了之后可以改基数吗？","complicated")
    ]
    # for testin in testins:
    #     print(jb.lcut(testin,cut_all=True))
    # exit()

    print("Please enter the model filename")
    nmf = input()
    if len(nmf) < 2:
        print("No name given,using", model_filename)
        nmf = model_filename

    pp = Predictor(nmf)

    score = 0
    for testin, ans in test_ins:
        
        out = pp.predict(testin)
        pred = out["prediction"]
        passed = pred == ans
        if passed: score+=1
        passedstr = "PASSED TEST" if passed else "@@@@@@@@@ FAILED TEST"

        print("In:",testin)
        print(passedstr, "Expected:", ans)
        print("Predicted Intent:",out)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    print("---------------------------")
    print("Performance:{}/{}".format(score,len(test_ins)))
    print("---------------------------")
    # pp.predict_loop()