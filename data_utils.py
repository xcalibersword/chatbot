import csv, time, os, re, argparse, random
import pandas as pd
from test_label.bot_LeftBrain import intent_dict, slot_dict

parser = argparse.ArgumentParser(allow_abbrev=False)

parser.add_argument("--save_type", type=str, default="label", help="Type of file to save label,id or QA")
arg = parser.parse_args()

#Funnel for all forms of data to the different pipeline
class RawDataProcessor:
    def __init__(self):
        self.sentlist = []
        self.cso_list = []
        self.cust_list = []
        self.id_list = {}
        
        self.pattern_timestamp = r'[(]\d*-\d*-\d* \d*:\d*:\d*[)]:'
        self.pattern_startline = r'-{28}.*-{28}'

        #load      
        self.datapath = r"D:\data (unsorted)\QianNiu_Conv_FanFan"
        #save QA
        self.savepath = os.path.join(str(os.getcwd()),"data", "QA" + time.strftime(r'%Y-%m-%d', time.localtime(time.time())) + ".csv")
        #save label
        self.labelpath = os.path.join(str(os.getcwd()),"data", "input_intent_slot" + ".csv")  

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

    def split2train_valid_test(self,custlist,category,start,stop):
                text_input = []
                text_intent = []
                text_slot = []
                for label_sent_list in custlist[start:stop]:
                    text_input.append(label_sent_list[0]+"\n")
                    text_intent.append(label_sent_list[1]+"\n")
                    text_slot.append(label_sent_list[2]+"\n")
                with open(r"D:\chatbot\test_NLU\data\test\{}\seq.in".format(category),"w",newline="\n") as f:
                    f.writelines(text_input)
                    f.close()
                with open(r"D:\chatbot\test_NLU\data\test\{}\label".format(category),"w",newline="\n") as f:
                    f.writelines(text_intent)
                    f.close()
                with open(r"D:\chatbot\test_NLU\data\test\{}\seq.out".format(category),"w",newline="\n") as f:
                    f.writelines(text_slot)
                    f.close()

    def isChinese(self,char):
        if u'\u4e00' <= char <= u'\u9fff':
            return True
        return False

    def saveProcessed(self):
        #generate QA
        if arg.save_type == "QA":
            new_cso_list = [[sent] for sent in self.cso_list]
            cso_df = pd.DataFrame(columns=["CSO"],data=new_cso_list)
            new_cust_list = [[sent] for sent in self.cust_list]
            cust_df = pd.DataFrame(columns=["CUST"],data=new_cust_list)
            QA_df = pd.concat([cso_df,cust_df],ignore_index=True,axis=1)
            QA_df.to_csv(self.savepath,index=False,encoding="utf-8")
        #generate id
        if arg.save_type == "id":
            list_list_list = []
            for id_key,sent_list in self.id_list.items():
                temp_df = pd.DataFrame(data=[[sent] for sent in sent_list])
                list_list_list.append(temp_df)
                temp_df.to_csv(r"D:\chatbot\id_data\{}.csv".format(id_key),index=False,encoding="utf-8")

        #generate to be label
        if arg.save_type == "label":
            cust_query = []
            for q in self.cust_list:
                query_list = q.split(" ")
                for query in query_list:
                    if query.strip() != "":
                        cust_query.append(query)
            
            clean_cust_query = []
            #simple clean to keep only chinese character
            for unclean in cust_query:
                clean = unclean
                for char in unclean:
                    if not self.isChinese(char):
                        clean = clean.replace(char,"")
                if not clean == "":
                    clean_cust_query.append(clean)

            greet_pattern = r"(你好|在吗|hi|hello|hey|您好)"
            slot_pattern = r"(上海|北京|广州|长沙|苏州|杭州|成都)"

            custlist = []
            for sent in clean_cust_query:
                labelled_sent = [sent]

                #label intent
                if re.search(greet_pattern,sent):
                    labelled_sent.append("user.greet")
                else:
                    labelled_sent.append("none")
                
                #label slot
                slot_list = ["O"]*len(sent)
                m = re.finditer(slot_pattern,sent)
                for a in m:
                    slot_list[a.start()] = "B-" + "city"
                    if (a.end()-1) == a.start():
                        pass
                    else:
                        for i in range(a.end()-1-a.start()):
                            slot_list[a.start()+i+1] = "I-" + "city"
                slot_string = " ".join(slot_list)
                labelled_sent.append(slot_string)
                custlist.append(labelled_sent)

            #split data into train,valid,test and the respective columns -> may need to refer to sklearn cross validation notes

            custlist_length = len(custlist)
            interval_first = round(custlist_length * 0.1)
            interval_second = round(custlist_length * 0.3)

            random.shuffle(custlist)
            
            #test
            self.split2train_valid_test(custlist,"test",None,interval_first)
            #validation
            self.split2train_valid_test(custlist,"valid",interval_first,interval_second)
            #train
            self.split2train_valid_test(custlist,"train",interval_second,None)

            # new_df = pd.DataFrame(data=custlist)
            # new_df.to_csv(r"D:\chatbot\data\a.csv",index=False,encoding="utf-8")
            #new_df.to_csv(self.labelpath,index=False,encoding="utf-8")

def readData():
    w = RawDataProcessor()
    w.loadQNtxt()
    w.processQNdata()
    return w

if __name__ == "__main__":
    w = readData()
    w.saveProcessed()