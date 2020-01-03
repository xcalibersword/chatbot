import json
import ast
import numpy as np
import jieba as jb

from keras.preprocessing.text import Tokenizer, tokenizer_from_json

if __name__ == "__main__":
    MAIN = True
    rootpath = ''
    from unzipper import get_vector_dict
    from nlp_utils import is_a_number, preprocess_sequence, postprocess_sequence

else:
    MAIN = False
    rootpath = 'embedding/'
    from embedding.unzipper import get_vector_dict
    from embedding.nlp_utils import is_a_number, preprocess_sequence, postprocess_sequence


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

def test_predictor(pred_obj):
    # Test the predictor
    fail_dict = {}
    score = 0
    for testin, ans in test_set:
        out = pred_obj.predict(testin)
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
        
        
        print("In:",testin, "passed?", passed)
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
    # Test suite    
    test_set = [
        ("我在上海，以前交过","inform"),
        ("上海的以前没交过","inform"),
        ("我在北京，不是首次","inform"),
        ("苏州的，之前有开户口","inform"),
        ("我之前有开户口","inform"),
        ("加上一金的话？","inform"),
        ("6月份的话？","inform"),
        ("12000","inform"),
        ("12月呢？","inform"),
        ("哦，没开过户口","inform"),
        ("嗯没有交公积金","inform"),
        ("支付过了哦","inform_paid"),
        ("已经付好啦","inform_paid"),
        ("费用已付注意查收","inform_paid"),
        ("哦好滴，了解","affirm"),
        ("喔好的","affirm"),
        ("之前交的社保可以补吗","ask_can_topup"),
        ("成都社保可不可以补缴？","ask_can_topup"),
        ("社保可不可以补缴？","ask_can_topup"),
        ("以前缴的公积金能补吗","ask_can_topup"),
        ("社保加公积金上海的一个月差不多要多少","ask_how_much"),
        ("服务费怎么算","ask_how_much"),
        ("你们可以看到成功了吗","ask_shebao_status"),
        ("社保公积金一起做收多少服务费啊","ask_how_much"),
        ("请问多久才到账", "ask_turnaround_time"),
        ("一般要多久才交上", "ask_turnaround_time"),
        ("交上社保要等多久", "ask_turnaround_time"),
        ("社保基数用8000的","ask_custom_jishu"),
        ("可以不要按照最低的吧","ask_custom_jishu"),
        ("按照12000的","ask_custom_jishu"),
        ("社保交了之后可以改基数吗？","ask_custom_jishu"),
        ("怀孕了还可以代缴吗","query_pregnant"),
        ("怀孕了还可以买吗","query_pregnant"),
        ("是在淘宝上拍那个吗","query_how_settle"),
        ("直接拍就可以了吧","query_how_settle"),
        ("怎么去拍啊","query_how_settle"),
        ("接着怎么去拍呢","request_link"),
        ("有没有链接？","request_link"),
        ("我该拍哪个？","request_link"),
        ("拍哪个宝贝？","request_link"),
        ("啥时间发货","query_fahuo"),
        ("一般会什么时间发货呢","query_fahuo"),
        ("可以延迟发货吗","query_delay_fahuo"),
        ("我想在北京买房","query_housing"),
        ("这个会影响购房么？","query_housing"),
        ("落户苏州","luohu"),
        ("落户可以办理吗","luohu"),
        ("我要交杭州社保落户用的","luohu"),
        ("我不太懂哦","confused"),
        ("你说了啥？","confused"),
        ("没了，谢谢","deny"),
        ("没","deny"),
        ("你们公司在几号截止的呢","query_pay_date"),
        ("你们一般什么时候下单？","query_pay_date"),
        ("深圳的还可以交吗","query_pay_deadline"),
        ("这个月还可以下单吗","query_pay_deadline"),
        ("首次要提供什材料吗？","query_req_resources"),
        ("需要我提供什东西吗","query_req_resources"),
        ("要参保的话需要什么资料","query_req_resources"),
        ("要啥材料吗","query_req_resources"),
        ("什么时候能查到","query_when_check_shebao_status"),
        ("要多久能查到呢？","query_when_check_shebao_status"),
        ("请问可以代缴上海社保吗","purchase"),
        ("我想交11月社保不断的可以吗","purchase"),
        ("我是想要代缴9月的","purchase"),
        ("想要代缴昆山社保的","purchase"),
        ("这里能代缴广州五险一金吗","purchase"),
        ("我可不可以用花呗来下单啊","query_use_huabei"),
        ("方便用电话讲吗","query_phone"),
        ("请问流程是怎么样的？","query_pay_process"),
        ("你们交社保的流程是怎么样？","query_pay_process"),
        ("怎么看到缴纳记录？","query_how_check_shebao_status"),
        ("缴纳之后能查看记录吗？","query_how_check_shebao_status"),
        ("在哪里能查到社保","query_how_check_shebao_status"),
        ("怎么去查社保有没有交上了","query_how_check_shebao_status"),
        ("怎么查杭州社保是否交了","query_how_check_shebao_status"),
        ("你们是交哪几个区的","query_region_coverage"),
        ("可以同时代缴两地吗", "query_multiple_locations"),
        ("能交两个地方的社保吗", "query_multiple_locations"),
        ("下月还得这里拍吗","query_xufei"),
        ("我真的很爱您哦","complicated"),
        ("我这个月失业了还能继续代缴吗","complicated"),
        ("外地人能交社保吗","complicated"),
        ("您好我这个月离职","complicated"),
        ("我准备离职中间两个月不交社保。这里可以帮我代缴吗","complicated"),
        ("我给朋友推荐了你们公司","complicated"),
        ("会有什么影响吗？","query_various_effects"),
        ("有什么后果吗？","query_various_effects"),
        ("不缴公积金会有什么影响啊","query_break"),
        ("断了会怎么样吗","query_break"),
        ("费用为啥80","doublecheck_value"),
        ("这个1937是包括费用么","doublecheck_value"),
        ("1000是吧","doublecheck_value"),
        ("生病之后去办理医保可以吗","query_sick"),
        ("参保可以吗 因为我已经生病了","query_sick"),
        ("看病没关系吧","query_sick_light"),
        ("好了就联系我哦","request_notify"),
        ("如果那边有什么问题要及时通知我哦","request_notify")
    ]

    print("Please enter the model filename")
    nmf = input()
    if len(nmf) < 2:
        nmf = "trained.h5"
        print("No name given,using", nmf)

    pp = Predictor(nmf)
    test_predictor(pp)

    
    # pp.predict_loop()