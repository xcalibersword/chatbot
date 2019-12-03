#convert csv from wps online to data for training
#future plan is csv to json of intent : replies/condition-replies/condition-condition-replies etc

import pandas as pd
csv_list_list = []

#insert path
df = pd.read_csv(r"raw.csv",encoding="gb18030")
list_list = df.values.tolist()
#read to dict
a = {}
label_list = list_list[4]
num_intents = len(label_list)

#intent example starts on the 6th row in excel (i=5 position when read)
for i in range(num_intents):
    if str(label_list[i]) != "nan":
        for l in list_list[5:]:
            if str(l[i]) != "nan":
                csv_list_list.append([l[i],label_list[i]])

#get intent-reply pairs
# ans_list = list_list[2]
# bot_resource = {}        
# for intent,answer in zip(label_list,ans_list):
#     bot_resource["intent"] = {"replies":[answer]}
# print(bot_resource)


new_df = pd.DataFrame(data=csv_list_list)
#insert path
new_df.to_csv(r"generated_data.csv",index=False,encoding="gb18030")

print("Done converting. Processed", str(num_intents),"intents")