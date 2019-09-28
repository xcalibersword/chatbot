import re
import csv
import pandas as pd
import time
import os

#help to extract the info from raw data into list
class RawDataProcessor:
    def __init__(self):
        self.cso_list = []
        self.cust_list = []
        self.id_list = {}
    
    def storeConvo(self,convo,speaker,isCSO,store2id = True):
        #print("Storing {0}: {1}".format(speaker,convo))
        if store2id == True:
            try:
                self.id_list[speaker].append(convo)
            except:
                self.id_list[speaker] = [convo]

        if isCSO:
            self.cso_list.append(convo)
        else:
            self.cust_list.append(convo)

    def stackConvo(self,convo,speaker,isCSO,store2id = True):
        #print("Stacking {0}: {1}".format(speaker,convo))
        if store2id == True:
            self.id_list[speaker][-1] = self.id_list[speaker][-1] + " " + convo

        if isCSO:
            self.cso_list[-1] = self.cso_list[-1] + " " + convo
        else:
            self.cust_list[-1] = self.cust_list[-1] + " " + convo

def filter_data(sent_list,w,pattern_timestamp):
    prevs_id = ""
    for sent in sent_list[7:-4]:
        #print(sent)
        if not sent == "\r\n": 
            if sent[0] == '-':              
                try:
                    if (prevs_id == cust_id and startTalk == cust_id) or (prevs_id != cust_id and startTalk != cust_id):
                        if prevs_id == cust_id:
                            w.storeConvo("",cust_id,True,store2id=False)
                        else:
                            w.storeConvo("",cso_id,False,store2id=False)
                except Exception:
                    pass

                cust_id = re.sub('-*','',sent).replace("\r","").replace("\n","")
                new_cso_convo_chat = True
                new_cust_convo_chat = True
            
            elif re.match(cust_id,sent):
                convo = re.sub(cust_id+pattern_timestamp,"",sent.replace("\r","").replace("\n",""))
                #print("Getting {0}: {1}".format(cust_id,convo))
                if new_cso_convo_chat and new_cust_convo_chat:
                    startTalk = cust_id
                if not cust_id == prevs_id or new_cust_convo_chat:
                    w.storeConvo(convo,cust_id,False)
                else:
                    w.stackConvo(convo,cust_id,False)

                prevs_id = cust_id
                new_cust_convo_chat = False
            
            elif re.search(pattern_timestamp,sent):
                cso_id = re.sub(pattern_timestamp+".*","",sent.replace("\r","").replace("\n",""))
                convo = re.sub(cso_id+pattern_timestamp,"",sent.replace("\r","").replace("\n",""))
                #print("Getting {0}: {1}".format(cso_id,convo))
                if new_cso_convo_chat and new_cust_convo_chat:
                    startTalk = cso_id
                try:
                    if prevs_id == cust_id or new_cso_convo_chat:
                        w.storeConvo(convo,cso_id,True)
                    else:
                        w.stackConvo(convo,cso_id,True)
                except Exception:
                    pass

                prevs_id = cso_id
                new_cso_convo_chat = False

            else:
                #print("{0}: {1}".format(prevs_id,convo))
                if prevs_id == cust_id:
                    isCSO = False
                else:
                    isCSO = True
                w.stackConvo(sent,prevs_id,isCSO)
    return w

pattern_timestamp = '[(][0-9-: ]*[): ]*'
w = RawDataProcessor()

for i in range(99):
    i +=1
    filePath = os.path.join(r"C:\Users\Administrator\Desktop\data (unsorted)\QianNiu_Conv_FanFan",str(i)) + ".txt"
    with open(filePath,newline="\n",encoding="gbk") as f:
        #print("Opening {}".format(filePath))
        #time.sleep(3)
        sent_list = f.readlines()
    w = filter_data(sent_list,w,pattern_timestamp)

    # if i == 99:
    #     for sent in sent_list:
    #         print(sent)
    #         time.sleep(1)

count = 1
for q,a in zip(w.cso_list,w.cust_list):
    count += 1
    if count > 1100:
        print("cso: {0} cust: {1}".format(q,a))
        time.sleep(1)

#save QA & ID to csv
cso_dict = {}
cust_dict = {}
cso_dict["CSO"] = w.cso_list
cust_dict["Customer"] = w.cust_list
cso_df = pd.DataFrame(data = cso_dict)
cust_df = pd.DataFrame(data = cust_dict)

QA_df = pd.concat([cso_df,cust_df],ignore_index=True,axis=1)
QA_df.to_csv(r"C:\Users\Administrator\Desktop\code (unsorted)\chatbot\data\raw_QA_list.csv",index=False,encoding="utf-8")

#maybe error towards the end of the conversation and the loading of files not all loaded
#file 99 for the cso and file 93 for the cust
# prev_df = pd.DataFrame.from_dict(w.id_list,orient="index")
# prev_df.transpose()
# prev_df.to_csv(r"C:\Users\Administrator\Desktop\code (unsorted)\chatbot\data\raw_QA_list1.csv",index=False,encoding="utf-8")

#funnel data (intents)
intent = {
    "greeting":[],
    "clarify":[],
    "bye":[],
    "yes":[],
    "no":[],
    "others":[]
}

intent2idx = enumerate(intent.keys())

#funnel data (slots)
slot = {
    "country.in":[],
    "country.of":[],
    "fee.for":[],
    "fee.due":[],
    "others":[]
}

slot2idx = enumerate(slot.keys())