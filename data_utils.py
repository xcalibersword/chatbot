import csv, time, os, re, random
import pandas as pd
from cbsv import *
import jieba_fast as jieba
import numpy as np

os.getcwd()

#add in words to detect [], html, error with set dictionary and user dict function, have to reset init.py for posseg
#and jieba to allow detection of special character
#remove repeated inputs from unique query

#Funnel for all forms of data to the different pipeline
class RawDataProcessor:
    def __init__(self):
        self.sentlist = []
        self.cso_list = []
        self.cust_list = []
        self.id_list = {}
        
        self.pattern_timestamp = r'[(]\d*-\d*-\d* \d*:\d*:\d*[)]:'
        self.pattern_startline = r'-{28}.*-{28}'
        self.pattern_image = r"[[].{2}[]]"
        self.pattern_link = r"(http:.*|https:.*)"

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

            with open(filePath,"r",encoding="gb18030") as f:
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

    def label_slot(self,msg_list):
        b_tag = "B-"
        i_tag = "I-"
        o_tag = "O"
        msg_slot = ["O"]*len(msg_list)
        # manually label for slot
        # for slot_label, v in self.bot_resource["info_parser"]["slots"].items():
        #     for _,pattern_list in v.items():
        #         if pattern_list != [] or pattern_list != [".*"]:
        #             pattern = list_to_regexList(pattern_list)                    
        token_pos = 0
        for token in msg_list:
            if self.hasLink(token):
                tag = b_tag + "link"
            elif self.hasImage(token):
                tag = b_tag + "image"
            elif self.isNumber(token):
                tag = b_tag + "number"
            else:
                tag = o_tag
            msg_slot[token_pos] = tag
            token_pos += 1
        return(" ".join(msg_slot))    

    def hasLink(self,phrase):
        if re.search(self.pattern_link,phrase):
            return True
        return False

    def hasImage(self,phrase):
        if re.search(self.pattern_image,phrase):
            return True
        return False

    def isNumber(self,phrase):
        for char in phrase:
            if str.isnumeric(char):
                return True
        return False

    def is_all_chinese(self,strs):
        for _char in strs:
            if not '\u4e00' <= _char <= '\u9fa5':
                return False
        return True

    def preprocess(self,sent_list):
        clean_list = []
        for word in sent_list:
            clean_word = re.sub(r'\W+', '', word.strip()).replace("_", '')
            if clean_word != "":
                if self.is_all_chinese(clean_word):
                    for char in clean_word:
                        clean_list.append(char)
                else:                   
                    clean_list.append(clean_word)
        return clean_list

    def tokeniser(self,pattern,msg):
        msg_list = []
        a = re.finditer(pattern,msg)
        prev_start = 0
        prev_end = len(msg)
        
        for m in a:
            start = m.span()[0]
            end = m.span()[1]
            if start > prev_start:
                msg_list.append(msg[prev_start:start])
            # print("Prev:  ",prev_start,prev_end)
            # print("Now:  ",start,end)
            if not msg[start:end] == "":
                msg_list.append(msg[start:end])
            prev_start = end
        
        if prev_start < prev_end:
            msg_list.append(msg[prev_start:prev_end])
        return msg_list

    def save2QA(self):
        new_cso_list = [[sent] for sent in self.cso_list]
        cso_df = pd.DataFrame(columns=["CSO"],data=new_cso_list)
        new_cust_list = [[sent] for sent in self.cust_list]
        cust_df = pd.DataFrame(columns=["CUST"],data=new_cust_list)
        QA_df = pd.concat([cso_df,cust_df],ignore_index=True,axis=1)
        QA_df.to_csv(self.savepath,index=False,encoding="utf-8")
    
    def save2ID(self):
        list_list_list = []
        for id_key,sent_list in self.id_list.items():
            temp_df = pd.DataFrame(data=[[sent] for sent in sent_list])
            list_list_list.append(temp_df)
            temp_df.to_csv(r"D:\chatbot\id_data\{}.csv".format(id_key),index=False,encoding="utf-8")

    def save2label(self):
        custlist = []
        unique_query_list = []
        for q in self.cust_list:
            query_list = q.split(" ")
            #tokenising part need to be reviewed
            for query in query_list:
                if query.strip() != "" and query.strip() not in unique_query_list:
                    sent = query.strip()
                    tokenised_sent_list = []
                    #case of sent sticking together
                    if self.hasLink(sent) or self.hasImage(sent):
                        imageless_list = self.tokeniser(self.pattern_image,sent)
                        for msg in imageless_list:
                            if re.search(self.pattern_image,msg):
                                tokenised_sent_list.append(msg)
                            else:
                                linkless_list = self.tokeniser(self.pattern_link,msg)
                                for word in linkless_list:
                                    if not re.search(self.pattern_link,word):
                                        split_word = jieba.lcut(word)
                                        #not to remove decimal point from numbers
                                        #typo of jiao(teach) & jiao(hand in)
                                        split_word_list = self.preprocess(split_word)

                                        for splitword in split_word_list:
                                            tokenised_sent_list.append(splitword)
                                    else:
                                        tokenised_sent_list.append(word)
                    else:
                        tokenised_sent_list = jieba.lcut(sent)
                        tokenised_sent_list = self.preprocess(tokenised_sent_list)      
                    #empty sentence cases
                    tokenised_sent = " ".join(tokenised_sent_list)
                    if tokenised_sent != "": 
                        sent_intent = self.label_intent(sent)
                        sent_slots = self.label_slot(tokenised_sent_list)
                        labelled_sent = [tokenised_sent,sent_intent,sent_slots]
                        custlist.append(labelled_sent)

                unique_query_list.append(query.strip())

        # save labelled cleaned data
        new_df = pd.DataFrame(data=custlist)
        new_df.to_csv(self.labelpath,index=False,encoding="utf-8")
        
        return custlist

def split2train_valid_test(custlist,category,start,stop):
    text_input = []
    text_intent = []
    text_slot = []

    for label_sent_list in custlist[start:stop]:
        text_input.append(label_sent_list[0]+"\n")
        text_intent.append(label_sent_list[1]+"\n")
        text_slot.append(label_sent_list[2]+"\n")
    
    with open(r"D:\chatbot\test_NLU\data\test\{}\seq.in".format(category),"w",newline="\n",encoding="utf-8") as f:
        f.writelines(text_input)
        f.close()
    with open(r"D:\chatbot\test_NLU\data\test\{}\label".format(category),"w",newline="\n",encoding="utf-8") as f:
        f.writelines(text_intent)
        f.close()
    with open(r"D:\chatbot\test_NLU\data\test\{}\seq.out".format(category),"w",newline="\n",encoding="utf-8") as f:
        f.writelines(text_slot)
        f.close()

def train_test_eval(csv_path):
        custlist =  np.array(pd.read_csv(csv_path)).tolist()
        # split data into train,valid,test and the respective category | refer to sklearn | problem with size

        # errorlist = []
        # for row in custlist:
        #     if len(row[0].split(" ")) != len(row[2].split(" ")):
        #         errorlist.append([row[0]])
        # new_df = pd.DataFrame(data=errorlist)
        # new_df.to_csv("D:\chatbot\data\c.csv",index=False,encoding="utf-8")
        # exit(0)
        # custlist_length = len(custlist)
        # interval_first = round(custlist_length * 0.1)
        # interval_second = round(custlist_length * 0.3)
        interval_first = 1
        interval_second = 2
        random.shuffle(custlist)
        #test
        split2train_valid_test(custlist,"test",None,interval_first)
        #validation
        split2train_valid_test(custlist,"valid",interval_first,interval_second)
        #train
        split2train_valid_test(custlist,"train",interval_second,None)

def readData():
    w = RawDataProcessor()
    w.loadQNtxt()
    w.processQNdata()
    return w

#convert csv from wps online to data for training
def csv2data():
    csv_list_list = []
    #insert path
    df = pd.read_csv(r"D:\chatbot\data\test.csv",encoding="gb18030")
    list_list = df.values.tolist()
    label_list = list_list[0]
    length = len(label_list)
    for i in range(length):
        if str(label_list[i]) != "nan":
            for l in list_list[1:]:
                if str(l[i]) != "nan":
                    csv_list_list.append([l[i],label_list[i]])
    new_df = pd.DataFrame(data=csv_list_list)
    #insert path
    new_df.to_csv(r"D:\chatbot\data\test1.csv",index=False,encoding="gb18030")

#remove spaces
def remove_spaces():
    df = pd.read_csv(r"D:\chatbot\data\test.csv",encoding="gb18030",header=None)
    list_list=df.values.tolist()
    new_list_list = []
    for list1 in list_list:
        new_list = []
        for sent in list1:
            if str(sent) != "nan":
                new_list.append("".join(sent.split()))
            else:
                new_list.append("")
        new_list_list.append(new_list)
    new_df = pd.DataFrame(data=new_list_list)
    #insert path
    new_df.to_csv(r"D:\chatbot\data\test1.csv",index=False,encoding="gb18030")
#add slot and label
#json to csv
#csv to json


def main():
    #w = readData()
    #clist = w.save2label()
    #print("Label Done")
    #train_test_eval(clist)
    #train_test_eval(r"D:\chatbot\data\b.csv")

    remove_spaces()

if __name__ == "__main__":
    main()