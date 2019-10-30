import numpy as np
import jieba as jb

if __name__ == "__main__":
    from unzipper import get_vector_dict
else:
    from embedding.unzipper import get_vector_dict

from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences 

# model_filename = 'embedding/241019_1600_model.h5'
rootpath = '/Users/davidgoh/Desktop/chatbot/embedding/'
model_filename = rootpath+'291019_JB_FINAL.h5'
w2v_filepath = "/Users/davidgoh/Desktop/sgns.weibo.bigram-char.bz2"
VDLIMIT = 60000 #35000 includes gongjijin

reverse_word_map = {1: 0, 2: 'complicated', 3: 'purchase', 4: 'affirm', 5: 'no_intent', 6: 'unknown', 7: 'chitchat', 8: 'inform_paid', 9: 'ask_can_topup', 10: 'query_pay_process', 11: 'greet', 12: 'ask_shebao_status', 13: 'query_req_resources', 14: 'inform_payment_history', 15: 'confused', 16: 'doublecheck', 17: 'ask_amt_month_fee_total', 18: 'explore_option', 19: 'thankyou', 20: 'check_can_pay_current_month', 21: 'query_housing', 22: 'luohu', 23: 'ask_verify', 24: 'deny', 25: 'query_how_check_shebao_status', 26: 'purchase_wxyj', 27: 'get_back_later', 28: 'query_various_effects', 29: 'check_is_possible', 30: 'inform_info_filled', 31: 'query_pay_deadline', 32: 'daikuan', 33: 'how_to_pai', 34: 'unsupported_request', 35: 'query_when_check_shebao_status', 36: 'query_phone', 37: 'request_link', 38: 'pay_shui', 39: 'next_step', 40: 'forget_it', 41: 'complain', 42: 'ask_turnaround_time', 43: 'ask_for_refund', 44: 'ask_can_topup_gjj', 45: 'apology', 46: 'request_future_notify', 47: 'query_mini_program', 48: 'gongjijin_only', 49: 'clarify', 50: 'ask_kai_piao',
51: 'affirm#thankyou', 52: 'query_shebao_components', 53: 'question_reliability', 54: 'query_weixin', 55: 'query_product_explain', 56: 'query_pregnant', 57: 'query_pay_part_only', 58: 'ask_how_now', 59: 'ask_amt_service_fee', 60: 'report_issue', 61: 'question_why', 62: 'query_topup', 63: 'query_multiple_locations', 64: 'query_have_service_fee', 65: 'missing_info', 66: 'inform_early_paid', 67: 'query_company_name', 68: 'ask_discount', 69: 'query_wxyj_included', 70: 'query_payment_schedule', 71: 'query_canzhangjin', 72: 'laodong', 73: 'ask_for_details', 74: 'ask_amt_gongjijin', 75: 'affirm#chitchat'}

class Predictor:
    def __init__(self):
        self.max_review_length = 15
        print("Initalizing Predictor...")
        self.pmodel = load_model(model_filename)
        self.pmodel.summary()
        self.w2v = get_vector_dict(w2v_filepath, limit = VDLIMIT)
        self.word2int = self._buildWordToInt()
        self.ignore_chars = {" ", ",", "?","？","。","，"}
        print("Finished initalizing Predictor")

    def _buildWordToInt(self):
        w2v = self.w2v
        count = 1
        d = {}
        for c in w2v:
            if not c in d:
                d[c] = count
                count += 1
        print("Found {} unique tokens".format(count+1))
        self.w2vend = count+1
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
                t = self.w2vend
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

        for i in range(top):
            curr = s_pred[-1]
            if curr == 0:
                break
            s_pred = s_pred[:-1]
            idx = np.where(pred == curr)[0][0]
            intent = reverse_word_map[idx]
            if (best == None): best = intent 
            conf = (curr*100/total)//0.1/10
            breakdown = breakdown + "<{}> Intent:{} Confidence:{}%\n".format(i+1, intent, conf)
        
        out = {"prediction":best,"breakdown":breakdown}
        return out

    def predict_loop(self):
        while 1:
            print("Please enter an input:")
            raw_inp = input()
            inp = self.tokenize(raw_inp)
            # print("pro in",inp)
            out = self.pmodel.predict([inp])
            self.pred_to_word(out)


if __name__ == "__main__":

    
    test_ins = ["我在上海","我要付社保","交公积金","您好","哦了解", "拍好了", "怎么拍", "一共多少钱啊", "我好爱您哦", "代缴社保", "落户苏州", "上海社保可以吗", "我不太懂哦","社保可以补交吗","需要我提供什东西吗","要啥材料吗","请问可以代缴上海社保吗"]
    # for testin in testins:
    #     print(jb.lcut(testin,cut_all=True))
    # exit()

    pp = Predictor()

    for testin in test_ins:
        out = pp.predict(testin)
        print("In:",testin,"Predicted Intent:",out)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")