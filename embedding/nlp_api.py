import json
import ast
import numpy as np
import jieba as jb

from keras.preprocessing.text import Tokenizer, tokenizer_from_json

if __name__ == "__main__":
    MAIN = True
    rootpath = ''
    from unzipper import get_vector_dict
    from nlp_utils import is_a_number, preprocess_sequence, postprocess_sequence, test_set

else:
    MAIN = False
    rootpath = 'embedding/'
    from embedding.unzipper import get_vector_dict
    from embedding.nlp_utils import is_a_number, preprocess_sequence, postprocess_sequence, test_set


from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences 

# model_filename = 'embedding/241019_1600_model.h5'
model_filename = rootpath+'API_model.h5'
w2v_filepath = "/Users/davidgoh/Desktop/sgns.weibo.bigram-char.bz2"
VDLIMIT = 60000 #35000 includes gongjijin

USE_WORD2VECTOR = False

DEBUG = False

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
        self.ignore_chars = {" ", ",", ":", "：", "。", "，"}
        self.unknown_token_val = 0
        self._load_jsons()
        if USE_WORD2VECTOR: 
            self.w2v = get_vector_dict(w2v_filepath, limit = VDLIMIT)  
        else: 
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
        intent_arr, wordlist = self.tokenize(raw)
        if DEBUG: print("<NLP_API PREDICT> input_arr",intent_arr)

        raw_pred = self.pmodel.predict(intent_arr)[0] # We want a single prediction
        outdict = {}
        pred_dict = self.pred_to_word(raw_pred)

        num_list = self.filter_numbers(wordlist)
        num_dict = {"numbers": num_list}
        outdict.update(pred_dict)
        outdict.update(num_dict)

        return outdict

    # Tokenizes and converts to int
    def tokenize(self, string):
        lesser_cut = jb.cut(string)
        wordlist = list(lesser_cut)

        string = self._remove_symbols(string)
        string = preprocess_sequence(string) # REMOVES STOPWORDS
        
        jbstring = jb.cut(string,cut_all=True)
        jbstring = postprocess_sequence(jbstring)
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
        return out, wordlist

    def filter_numbers(self, seq):
        out = []
        for item in seq:
            # print("FN item",item)
            if is_a_number(item):
                try:
                    fi = float(item)
                    out.append(fi)
                except Exception as e:
                    print("<FILTER NUMBERS> Exception",e)
                
        if DEBUG: print("<FILTER NUMBERS>",out)
        return out

    def pred_to_word(self,pred):
        top = 3
        total = np.sum(pred)
        s_pred = np.sort(pred,-1)
        best = None
        breakdown = ""
        rel_threshold = 40
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

    def test_predictor(self,test_set):
        # Test the predictor
        fail_dict = {}
        score = 0
        for testin, ans in test_set:
            out = self.predict(testin)
            pred = out["prediction"]
            passed = pred == ans
            if passed: score+=1
            if passed:
                passedstr = "PASSED" 
            else:
                passedstr = "@@@@@@@@@@@@@@@@@@ FAILED TEST"
                if ans in fail_dict:
                    fail_dict[ans] = fail_dict[ans] + 1
                else:
                    fail_dict[ans] = 1
            
            
            print("In:<",testin, "> Passed?:", passed)
            if not passed or DEBUG:
                print(passedstr, "Expected:", ans)
                print("Predicted Intent:",out)
            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        print("---------------RESULTS---------------")
        print("Performance:{}/{}".format(score,len(test_set)))
        print("Failed topics:")
        for t, c in fail_dict.items():
            print(t,c)
        print("---------------------------------------------")


if MAIN:
    print("Please enter the model filename")
    nmf = input()
    if len(nmf) < 2:
        nmf = "trained.h5"
        print("No name given,using", nmf)
    
    pp = Predictor(nmf)
    pp.test_predictor(test_set)