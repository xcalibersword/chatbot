import csv, time, os, re
import pandas as pd

#Funnel for all forms of data to the different pipeline
class RawDataProcessor:
    def __init__(self,date_of_entry,data_path):
        self.sentlist = []
        self.cso_list = []
        self.cust_list = []
        self.id_list = {}
        self.pattern_timestamp = '[(][0-9-: ]*[): ]*'
        dirpath = os.getcwd()
        savepath = os.path.join(str(dirpath),"data") + date_of_entry + ".csv"    
        self.savepath = savepath
        self.datapath = data_path

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
        try:
            if store2id == True:
                self.id_list[speaker][-1] = self.id_list[speaker][-1] + " " + convo
        except Exception:
            print(speaker,convo)

        if isCSO:
            self.cso_list[-1] = self.cso_list[-1] + " " + convo
        else:
            self.cust_list[-1] = self.cust_list[-1] + " " + convo

    def loadQNtxt(self):
        file_name_list = os.listdir(path=self.datapath)
        for file_name in file_name_list:
            filePath = os.path.join(self.datapath,file_name)

            with open(filePath,encoding="gb18030") as f:
                print("Loading {}".format(filePath))
                temp_sent_list = f.readlines()
            
            if 'n' in file_name: 
                for sent in temp_sent_list[7:-4]:
                    sent = sent.strip()
                    if not sent == '':
                        self.sentlist.append(sent)
            else:
                for sent in temp_sent_list[7:]:
                    sent = sent.strip()
                    if not sent == '':
                        self.sentlist.append(sent)
    

date_of_entry = "290919"        
data_path = r"C:\Users\Administrator\Desktop\data (unsorted)\QianNiu_Conv_FanFan"
w = RawDataProcessor(date_of_entry,data_path)
w.loadQNtxt()

prevs_id = ""
for sent in w.sentlist:
    if sent[0] == '-':       
        try:
            if prevs_id == startTalk:
                if prevs_id == cust_id:
                    w.storeConvo(" ",cust_id,True,store2id=False)
                    #for q,a in zip(w.cso_list[-5:],w.cust_list[-5:]):
                        #print("cso: {0} cust: {1}".format(q,a))
                        #time.sleep(1)
                else:
                    #print("Start: {0}, Prevs: {1}".format(startTalk,prevs_id))       
                    #print("padded cust")
                    w.storeConvo(" ",cso_id,False,store2id=False)
                    # for q,a in zip(w.cso_list[-5:],w.cust_list[-5:]):
                    #     print("cso: {0} cust: {1}".format(q,a))
                    #     time.sleep(1)
        except Exception:
            pass

        cust_id = re.sub('-*','',sent).replace("\r","").replace("\n","")
        new_cso_convo_chat = True
        new_cust_convo_chat = True
    
    elif re.match(cust_id,sent):
        convo = re.sub(cust_id+w.pattern_timestamp,"",sent.replace("\r","").replace("\n",""))
        #print("Getting {0}: {1}".format(cust_id,convo))
        if new_cso_convo_chat and new_cust_convo_chat:
            startTalk = cust_id
        try:
            if not cust_id == prevs_id or new_cust_convo_chat:
                w.storeConvo(convo,cust_id,False)
            else:
                w.stackConvo(convo,cust_id,False)
        except Exception:
            pass

        prevs_id = cust_id
        new_cust_convo_chat = False
    
    elif re.search(w.pattern_timestamp,sent):
        cso_id = re.sub(w.pattern_timestamp+".*","",sent.replace("\r","").replace("\n",""))
        convo = re.sub(cso_id+w.pattern_timestamp,"",sent.replace("\r","").replace("\n",""))
        #print("Getting {0}: {1}".format(cso_id,convo))
        if new_cso_convo_chat and new_cust_convo_chat:
            startTalk = cso_id
        try:
            if cust_id == prevs_id or new_cso_convo_chat:
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


    # if i == 80:
    #     # for sent in sent_list[7:]:
    #     #     print(sent)
    #     #     time.sleep(1)
    #     for q,a in zip(w.cso_list[-8:],w.cust_list[-8:]):
    #         print("cso: {0} cust: {1}".format(q,a))
    #         time.sleep(1)



#save QA & ID to csv
cso_dict = {}
cust_dict = {}
cso_dict["CSO"] = w.cso_list
cust_dict["Customer"] = w.cust_list
cso_df = pd.DataFrame(data = cso_dict)
cust_df = pd.DataFrame(data = cust_dict)

QA_df = pd.concat([cso_df,cust_df],ignore_index=True,axis=1)
QA_df.to_csv(r"C:\Users\Administrator\Desktop\code (unsorted)\chatbot\data\raw_QA_list.csv",index=False,encoding="utf-8")

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


#stack problem