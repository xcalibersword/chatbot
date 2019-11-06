#convert csv from wps online to data for training


import pandas as pd
csv_list_list = []
#insert path
df = pd.read_csv(r"raw.csv",encoding="gb18030")
list_list = df.values.tolist()
#read to dict
a = {}
label_list = list_list[0]
length = len(label_list)
for i in range(length):
    if str(label_list[i]) != "nan":
        for l in list_list[1:]:
            if str(l[i]) != "nan":
                csv_list_list.append([l[i],label_list[i]])
new_df = pd.DataFrame(data=csv_list_list)
#insert path
new_df.to_csv(r"generated_data.csv",index=False,encoding="gb18030")

print("Done")