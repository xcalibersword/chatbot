import csv, time, os, re
import pandas as pd

#Funnel for all forms of data to the different pipeline
class RawDataProcessor:
    def __init__(self):
        self.sentlist = []
        self.cso_list = []
        self.cust_list = []
        self.id_list = {}
        
        self.pattern_timestamp = r'[(]\d*-\d*-\d* \d*:\d*:\d*[)]:'
        self.pattern_startline = r'-{28}.*-{28}'

        self.savepath = os.path.join(str(os.getcwd()),"data", "QA" + time.strftime(r'%Y-%m-%d', time.localtime(time.time())) + ".csv")
        self.datapath = r"D:\data (unsorted)\QianNiu_Conv_FanFan"

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
        for sent in w.sentlist:
            if re.match(w.pattern_startline,sent):        
                if not prevs_id == "" and not startTalk == "":
                    if prevs_id == cust_id and startTalk == cust_id:
                        w.storeConvoQA(" ",True)
                    elif not prevs_id == cust_id and not startTalk == cust_id:
                        w.storeConvoQA(" ",False)
                cust_id = re.sub('-*','',sent)
                new_cso_convo_chat = True
                new_cust_convo_chat = True
                prevs_id = ""
                startTalk = ""    
            elif re.match(cust_id,sent):
                convo = re.sub(cust_id+w.pattern_timestamp,"",sent).strip()
                w.storeConvoID(convo,cust_id)
                if not cust_id == prevs_id:    
                    w.storeConvoQA(convo,False)
                elif new_cust_convo_chat:
                    w.storeConvoQA(convo,False)
                else:
                    w.stackConvoQA(convo,False)

                if new_cso_convo_chat and new_cust_convo_chat:
                    startTalk = cust_id
                prevs_id = cust_id
                new_cust_convo_chat = False
            elif re.search(w.pattern_timestamp,sent):
                cso_id = re.sub(w.pattern_timestamp+".*","",sent)
                convo = re.sub(cso_id+w.pattern_timestamp,"",sent).strip()
                w.storeConvoID(convo,cso_id)
                if prevs_id == cust_id:
                    w.storeConvoQA(convo,True)
                elif new_cso_convo_chat:
                    w.storeConvoQA(convo,True)
                else:
                    w.stackConvoQA(convo,True) 

                if new_cso_convo_chat and new_cust_convo_chat:
                    startTalk = cso_id
                prevs_id = cso_id
                new_cso_convo_chat = False
            else:
                if prevs_id == cust_id:
                    isCSO = False
                else:
                    isCSO = True
                w.stackConvoQA(sent,isCSO)
                w.stackConvoID(sent,prevs_id)

    def saveProcessed(self):
        new_cso_list = [[sent] for sent in w.cso_list]
        cso_df = pd.DataFrame(columns=["CSO"],data=new_cso_list)
        new_cust_list = [[sent] for sent in w.cust_list]
        cust_df = pd.DataFrame(columns=["CUST"],data=new_cust_list)
        QA_df = pd.concat([cso_df,cust_df],ignore_index=True,axis=1)
        QA_df.to_csv(w.savepath,index=False,encoding="utf-8")

        list_list_list = []
        for id_key,sent_list in w.id_list.items():
            temp_df = pd.DataFrame(data=[[sent] for sent in sent_list])
            list_list_list.append(temp_df)
            temp_df.to_csv(r"D:\chatbot\id_data\{}.csv".format(id_key),index=False,encoding="utf-8")

    def autoLabeler(self,template_dict,data_list):
        pass

    def word_embedding(self):
        pass

    def slot_gated_model(self):
        pass

w = RawDataProcessor()
w.loadQNtxt()
w.processQNdata()





#w.saveProcessed()

# cust_query = []
# for q in w.cust_list:
#     query_list = q.split(" ")
    
#     for query in query_list:
#         if query.strip() != "":
#            cust_query.append(query)
# custlist = [[sent] for sent in cust_query]
# new_df = pd.DataFrame(data=custlist)
# new_df.to_csv(r"D:\chatbot\data\a.csv",index=False,encoding="utf-8")

