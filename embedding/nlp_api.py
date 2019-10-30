import numpy as np
import jieba as jb
# from embedding.unzipper import get_vector_dict
from unzipper import get_vector_dict

from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences 

# model_filename = 'embedding/241019_1600_model.h5'
model_filename = '251019_JB_model.h5'
w2v_filepath = "/Users/davidgoh/Desktop/sgns.weibo.bigram-char.bz2"
VDLIMIT = 50000

reverse_word_map = {1: 0, 2: 'complicated', 3: 'no_intent', 4: 'purchase', 5: 'affirm', 6: 'unknown', 7: 'chitchat', 8: 'inform_paid', 9: 'query_pay_process', 10: 'ask_can_topup', 11: 'doublecheck', 12: 'ask_shebao_status', 13: 'purchase_wxyj', 14: 'greet', 15: 'thankyou', 16: 'ask_amt_month_fee_total', 17: 'query_req_resources', 18: 'check_can_pay_current_month', 19: 'confused', 20: 'inform_payment_history', 21: 'deny', 22: 'check_is_possible', 23: 'ask_verify', 24: 'get_back_later', 25: 'query_pay_deadline', 26: 'gongjijin_only', 27: 'query_when_check_shebao_status', 28: 'complain', 29: 'request_link', 30: 'query_how_check_shebao_status', 31: 'how_to_pai', 32: 'ask_for_phone', 33: 'affirm#thankyou', 34: 'inform_info_filled', 35: 'apology', 36: 'query_pay_part_only', 37: 'clarify', 38: 'report_issue', 39: 'ask_amt_service_fee', 40: 'query_product_explain', 41: 'question_why', 42: 'query_refund', 43: 'ask_for_refund', 44: 'reassure', 45: 'ask_discount', 46: 'query_weixin', 47: 'ask_turnaround_time', 48: 'missing_info', 49: 'req_check', 50: 'query_have_service_fee', 
51: 'purchase_gjj', 52: 'check_anything_else', 53: 'ask_kai_piao', 54: 'query_payment_schedule', 55: 'query_canzhangjin', 56: 'pay_query', 57: 'affirm#chitchat', 58: 'next_step', 59: 'check_procedure_card', 60: 'query_wxyj_included', 61: 'request_future_notify', 62: 'query_pregnant', 63: 'check_procedure_shouce', 64: 'total_amt_query', 65: 'ask_for_details', 66: 'ask_how_now', 67: 'question_reliability'}

class Predictor:
    def __init__(self):
        self.max_review_length = 20
        print("Initalizing Predictor...")
        self.pmodel = load_model(model_filename)
        self.pmodel.summary()
        self.w2v = get_vector_dict(w2v_filepath, limit = VDLIMIT)
        self.word2int = self._buildWordToInt()
        self.ignore_chars = {" ", ",", "?","？","。","，"}
        print("Finished initalizing Predictor")

    def _buildWordToInt(self):
        w2v = self.w2v
        count = 0
        d = {}
        for c in w2v:
            if not c in d:
                d[c] = count
                count += 1
        print("Found {} unique tokens".format(count+1))
        return d
    
    def predict(self, raw):
        arr = self.tokenize(raw)
        raw_pred = self.pmodel.predict(arr)[0] # We want a single prediction
        outdict = self.pred_to_word(raw_pred)
        return outdict

    # Tokenizes and converts to int
    def tokenize(self, string):
        jbstring = jb.cut(string,cut_all=True)
        word2int = self.word2int
        out = []
        for c in jbstring:
            if c in word2int:
                t = word2int[c]
            else:
                t = 0
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

    
    test_ins = ["我在上海","我要付社保","您好","哦了解", "拍好了", "怎么拍", "一共多少钱啊", "我好爱您哦", "代缴社保", "落户苏州", "上海社保可以吗", "我不太懂哦","社保可以补交吗","需要我提供什东西吗","要啥材料吗","请问可以代缴上海社保吗"]
    # for testin in testins:
    #     print(jb.lcut(testin,cut_all=True))
    # exit()

    pp = Predictor()

    for testin in test_ins:
        out = pp.predict(testin)
        print("In:",testin,"Predicted Intent:",out)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")