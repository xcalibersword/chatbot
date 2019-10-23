import csv
import numpy as np
from keras.optimizers import Adam
from keras.models import Sequential
from keras.layers import Embedding, LSTM, Dense, Conv1D, Flatten,BatchNormalization
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences 
from keras.utils import to_categorical

max_review_length = 20 #maximum length of the sentence
embedding_vector_length = 16
top_words = 400
intents = 64

#read csv
dataset_fp = "data_in.csv"
with open(dataset_fp, 'r',encoding='gb18030') as f:
    rows = csv.reader(f, delimiter = ',')
    data = []
    for r in rows:
        data.append(r)
    npdata = np.array(data)

xval = npdata[:,0]
yval = npdata[:,1]

intent_tokenizer = Tokenizer(intents,filters='',oov_token=0)
intent_tokenizer.fit_on_texts(yval)
ints_yval = intent_tokenizer.texts_to_sequences(yval)
cat_yval = to_categorical(ints_yval)

num_intents = len(intent_tokenizer.word_index)
print('Found %s unique intents.' %num_intents)

reverse_word_map = dict(map(reversed, intent_tokenizer.word_index.items()))

def pred_to_word(pred):
    best = max(pred)
    total = np.sum(pred)
    (idx,), = np.where(pred == best)
    intent = reverse_word_map[idx]
    print("Intent:{} Confidence:{}%".format(intent,best*100/total))

print("testing for",yval[415])
test_reverse = cat_yval[415]

print(pred_to_word(test_reverse))

#num_words is tne number of unique words in the sequence, if there's more top count words are taken
tokenizer = Tokenizer(top_words)
tokenizer.fit_on_texts(xval)
sequences = tokenizer.texts_to_sequences(xval)
word_index = tokenizer.word_index
input_dim = len(word_index) + 1
print('Found %s unique tokens.' % len(word_index))

prep_xvals = pad_sequences(sequences, max_review_length)
print('Shape of data tensor:', prep_xvals.shape)
print("xval smaple", prep_xvals[156][0])

exit()

# MODEL CONSTRUCTION

model = Sequential()
model.add(Embedding(top_words, embedding_vector_length, input_length=max_review_length))
model.add(BatchNormalization(momentum=0.99))
# model.add(Conv2D(128,2,strides=1,padding="same",activation='relu')) # Future?
model.add(Conv1D(64,2,strides=1,padding="same",activation='relu'))
# model.add(LSTM(units=128))
model.add(Flatten())
model.add(Dense(units=512,activation='relu'))
model.add(Dense(units=256,activation='relu'))
model.add(Dense(units=intents,activation='sigmoid'))

LEARN_RATE = 0.0003
optimizer = Adam(learning_rate=LEARN_RATE)
model.compile(optimizer, 'categorical_crossentropy', metrics=['accuracy'])

model.summary()

model.fit(x=prep_xvals,y=cat_yval,epochs=50,verbose=1,validation_split=0.1,batch_size=8)

# Post Training
model.save('231019_1600_model.h5')

test_in = ["我 很 爱 您","我 在 上 海","我 要 付 社 保","您 好","拍 好 了", "怎 么 拍", "社 保 可 以 补 交 吗","需 要 我 提 供 什 东 西 吗", "要 啥 材 料 吗", "请 问 可 以 代 缴 上 海 社 保 吗"]
ti = tokenizer.texts_to_sequences(test_in)
input_array = pad_sequences(ti, max_review_length)
print("input",test_in)

output_array = model.predict(input_array)
# print("raw",output_array)

for bleh in output_array:
    pred_to_word(bleh)
