#convert csv from wps online to data for training
#future plan is csv to json of intent : replies/condition-replies/condition-condition-replies etc

import pandas as pd
csv_list_list = []

#insert path
df = pd.read_csv(r"raw.csv",encoding="gb18030",header=None)
list_list = df.values.tolist()
#read to dict
a = {}
intent_row = 3
label_list = list_list[intent_row]
num_intents = len(label_list)

#intent example starts on the 2th row in excel (i=1 position when read)
for i in range(num_intents):
    if str(label_list[i]) != "nan":
        for l in list_list[intent_row+1:]:
            if str(l[i]) != "nan":
                csv_list_list.append([l[i],label_list[i]])



new_df = pd.DataFrame(data=csv_list_list)
#insert path
new_df.to_csv(r"generated_data.csv",index=0,header=0,encoding="gb18030")

print("Done converting. Processed", str(num_intents),"intents")