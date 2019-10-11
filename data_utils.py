import csv, time, os, re, random, string
import pandas as pd
from cbsv import *
import jieba_fast as jieba

os.getcwd()

#add in words to detect [], html, error with set dictionary and user dict function, have to reset init.py for posseg
#and jieba to allow detection of special character
jieba.add_word("http://item.taobao.com/item.htm?id=")
jieba.add_word("[emoji]")
jieba.add_word("[表情]")
jieba.add_word("[卡片]")
jieba.add_word("[图片]")
jieba.add_word("[未知]")

#Funnel for all forms of data to the different pipeline
class RawDataProcessor:
    def __init__(self):
        self.sentlist = []
        self.cso_list = []
        self.cust_list = []
        self.id_list = {}
        
        self.pattern_timestamp = r'[(]\d*-\d*-\d* \d*:\d*:\d*[)]:'
        self.pattern_startline = r'-{28}.*-{28}'
        self.pattern_punctuation = r"！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾\
            ＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧.﹏" + string.punctuation

        #load raw data   
        self.datapath = r"D:\data (unsorted)\QianNiu_Conv_FanFan"
        #save QA
        self.savepath = os.path.join(str(os.getcwd()),"data", "QA" + time.strftime(r'%Y-%m-%d', time.localtime(time.time())) + ".csv")
        #save label
        self.labelpath = os.path.join(str(os.getcwd()),"data", "input_intent_slot" + ".csv")  

        #bot_resource for intent and slot pattern
        self.bot_resource = read_json(os.path.join(str(os.getcwd()),"chatbot_resource.json"))

    def storeConvoID(self,convo,speaker):
        try:
            self.id_list[speaker].append(convo)
        except:
            self.id_list[speaker] = [convo]

    def storeConvoQA(self,convo,isCSO):
        if isCSO:
            self.cso_list.append(convo)
        else:
            self.cust_list.append(convo)

    def stackConvoID(self,convo,speaker):
        self.id_list[speaker][-1] = self.id_list[speaker][-1] + " " + convo
    
    def stackConvoQA(self,convo,isCSO):
        if isCSO:
            self.cso_list[-1] = self.cso_list[-1] + " " + convo
        else:
            self.cust_list[-1] = self.cust_list[-1] + " " + convo

    def loadQNtxt(self):
        file_name_list = os.listdir(path=self.datapath)
        for file_name in file_name_list:
            filePath = os.path.join(self.datapath,file_name)

            with open(filePath,encoding="gb18030") as f:
                #print("Loading {}".format(filePath))
                temp_sent_list = f.readlines()
            
            if 'n' in file_name: 
                for sent in temp_sent_list[7:-4]:
                    sent = sent.strip()
                    if not sent == '':
                        # if re.search("fufen871023",sent):
                        #     print(file_name)
                        #     break
                        self.sentlist.append(sent)
            else:
                for sent in temp_sent_list[7:]:
                    sent = sent.strip()
                    if not sent == '':
                        
                        # if re.search("fufen871023",sent):
                        #     print(file_name)
                        #     break
                        self.sentlist.append(sent)
    
    def processQNdata(self):
        prevs_id = ""
        startTalk = ""
        for sent in self.sentlist:
            if re.match(self.pattern_startline,sent):        
                if not prevs_id == "" and not startTalk == "":
                    if prevs_id == cust_id and startTalk == cust_id:
                        self.storeConvoQA(" ",True)
                    elif not prevs_id == cust_id and not startTalk == cust_id:
                        self.storeConvoQA(" ",False)
                cust_id = re.sub('-*','',sent)
                new_cso_convo_chat = True
                new_cust_convo_chat = True
                prevs_id = ""
                startTalk = ""    
            elif re.match(cust_id,sent):
                convo = re.sub(cust_id+self.pattern_timestamp,"",sent).strip()
                self.storeConvoID(convo,cust_id)
                if not cust_id == prevs_id:    
                    self.storeConvoQA(convo,False)
                elif new_cust_convo_chat:
                    self.storeConvoQA(convo,False)
                else:
                    self.stackConvoQA(convo,False)

                if new_cso_convo_chat and new_cust_convo_chat:
                    startTalk = cust_id
                prevs_id = cust_id
                new_cust_convo_chat = False
            elif re.search(self.pattern_timestamp,sent):
                cso_id = re.sub(self.pattern_timestamp+".*","",sent)
                convo = re.sub(cso_id+self.pattern_timestamp,"",sent).strip()
                self.storeConvoID(convo,cso_id)
                if prevs_id == cust_id:
                    self.storeConvoQA(convo,True)
                elif new_cso_convo_chat:
                    self.storeConvoQA(convo,True)
                else:
                    self.stackConvoQA(convo,True) 

                if new_cso_convo_chat and new_cust_convo_chat:
                    startTalk = cso_id
                prevs_id = cso_id
                new_cso_convo_chat = False
            else:
                if prevs_id == cust_id:
                    isCSO = False
                else:
                    isCSO = True
                self.stackConvoQA(sent,isCSO)
                self.stackConvoID(sent,prevs_id)
    
    def label_intent(self,msg):
        msg_intent = "no_intent"
        for intent, v in self.bot_resource["intents"].items():
            if v["matchdb"] != []:
                pattern = list_to_regexList(v["matchdb"])
                if re.search(pattern,msg):
                    msg_intent = intent
                    break
        return msg_intent

    def label_slot(self,msg):
        msg_slot = ["0"]*len(msg)
        for slot_label, v in self.bot_resource["info_parser"].items():
            for _,pattern_list in v.items():
                if pattern_list != []:
                    pattern = list_to_regexList(pattern_list)
                    word_pos = 0
                    for word in msg:
                        #missing for "I-"
                        if re.search(pattern,word):
                            msg_slot[word_pos] = "B-" + slot_label
                        word_pos += 1

        # label slot by character
        # slot_pattern = r"(上海|台湾)"
        # sent = "上海按时打算"
        # slot_list = ["O"]*len(sent)
        # m = re.finditer(slot_pattern,sent)
        # for a in m:
        #     slot_list[a.start()] = "B-" + "city"
        #     if (a.end()-1) == a.start():
        #         pass
        #     else:
        #         for i in range(a.end()-1-a.start()):
        #             slot_list[a.start()+i+1] = "I-" + "city"
        # slot_string = " ".join(slot_list)
        # print(slot_string)

        return(" ".join(msg_slot))    
        
    def split2train_valid_test(self,custlist,category,start,stop):
                text_input = []
                text_intent = []
                text_slot = []

                for label_sent_list in custlist[start:stop]:
                    #format chinese input into english format (tokenising)
                    # msg = label_sent_list[0]
                    # new_msg = ""
                    # for char in msg:
                    #     new_msg = (new_msg + char + " ").rstrip()
                    text_input.append(label_sent_list[0]+"\n")
                    text_intent.append(label_sent_list[1]+"\n")
                    text_slot.append(label_sent_list[2]+"\n")
                
                with open(r"D:\chatbot\test_NLU\data\test\{}\seq.in".format(category),"w",newline="\n",encoding="gb18030") as f:
                    f.writelines(text_input)
                    f.close()
                with open(r"D:\chatbot\test_NLU\data\test\{}\label".format(category),"w",newline="\n",encoding="gb18030") as f:
                    f.writelines(text_intent)
                    f.close()
                with open(r"D:\chatbot\test_NLU\data\test\{}\seq.out".format(category),"w",newline="\n",encoding="gb18030") as f:
                    f.writelines(text_slot)
                    f.close()
    
    def rm_punctuation(self,phrase_list):
        clean_phrase_list = []
        for phrase in phrase_list:
            if not phrase in self.pattern_punctuation:
                clean_phrase_list.append(phrase)
        return clean_phrase_list

    def isChinese(self,char):
        if u'\u4e00' <= char <= u'\u9fff':
            return True
        return False

    def save2QA(self):
        new_cso_list = [[sent] for sent in self.cso_list]
        cso_df = pd.DataFrame(columns=["CSO"],data=new_cso_list)
        new_cust_list = [[sent] for sent in self.cust_list]
        cust_df = pd.DataFrame(columns=["CUST"],data=new_cust_list)
        QA_df = pd.concat([cso_df,cust_df],ignore_index=True,axis=1)
        QA_df.to_csv(self.savepath,index=False,encoding="gb18030")
    
    def save2ID(self):
        list_list_list = []
        for id_key,sent_list in self.id_list.items():
            temp_df = pd.DataFrame(data=[[sent] for sent in sent_list])
            list_list_list.append(temp_df)
            temp_df.to_csv(r"D:\chatbot\id_data\{}.csv".format(id_key),index=False,encoding="gb18030")

    def save2label(self):
        cust_query = []
        for q in self.cust_list:
            query_list = q.split(" ")
            for query in query_list:
                if query.strip() != "":
                    cust_query.append(query)
        
        # save raw query only
        # new_df = pd.DataFrame(data=custlist)
        # new_df.to_csv(self.labelpath,index=False,encoding="gb18030")

        # remove non chinese words
        # clean_cust_query = []
        # for unclean in cust_query:
            # clean = unclean
            # for char in unclean:
            #     if not self.isChinese(char):
            #         clean = clean.replace(char,"")
            # if clean != "":
            #     clean_cust_query.append(clean)

        #tokenise chinese word and labelling
        custlist = []
        for sent in cust_query:
            tokenised_sent_list = jieba.lcut(sent)
            tokenised_sent_list = self.rm_punctuation(tokenised_sent_list)
            tokenised_sent = " ".join(tokenised_sent_list)
            sent_intent = self.label_intent(sent)
            sent_slots = self.label_slot(tokenised_sent_list)
            labelled_sent = [tokenised_sent,sent_intent,sent_slots]
            custlist.append(labelled_sent)

        # save labelled cleaned data
        new_df = pd.DataFrame(data=custlist)
        new_df.to_csv(r"D:\chatbot\data\a.csv",index=False,encoding="gb18030")

        # split data into train,valid,test and the respective category | refer to sklearn | problem with size

        # custlist_length = len(custlist)
        # interval_first = round(custlist_length * 0.1)
        # interval_second = round(custlist_length * 0.3)

        interval_first = 483
        interval_second = 1231
        end = 4890
        random.shuffle(custlist)
        
        #test
        self.split2train_valid_test(custlist,"test",None,interval_first)
        #validation
        self.split2train_valid_test(custlist,"valid",interval_first,interval_second)
        #train
        self.split2train_valid_test(custlist,"train",interval_second,end)

def readData():
    w = RawDataProcessor()
    w.loadQNtxt()
    w.processQNdata()
    return w

def main():
    w = readData()
    w.save2label()


if __name__ == "__main__":
    main()