import csv
import numpy as np

from unzipper import get_vector_dict
from keras.initializers import Constant
from keras.layers import Concatenate, Dropout, Embedding, LSTM, Dense, Conv1D, Flatten, BatchNormalization, MaxPooling1D
from keras.models import Model, Input
from keras.optimizers import Adam
from keras.preprocessing.text import Tokenizer, text_to_word_sequence
from keras.preprocessing.sequence import pad_sequences 
from keras.utils import to_categorical

w2v_filepath = "/Users/davidgoh/Desktop/sgns.weibo.bigram-char.bz2"

max_review_length = 20 #maximum length of the sentence
embedding_vector_length = 300
top_words = 1000
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
    top = 3
    total = np.sum(pred)
    s_pred = np.sort(pred,-1)

    for i in range(top):
        curr = s_pred[-1]
        if curr == 0:
            break
        s_pred = s_pred[:-1]
        idx = np.where(pred == curr)[0][0]
        print("idx",idx,"curr",curr)
        intent = reverse_word_map[idx]
        print("<{}> Intent:{} Confidence:{}%".format(i+1,intent,curr*100/total))

print("testing for",yval[415])
test_reverse = cat_yval[415]

print(pred_to_word(test_reverse))

#num_words is tne number of unique words in the sequence, if there's more top count words are taken
tokenizer = Tokenizer(top_words)
tokenizer.fit_on_texts(xval)
word_index = tokenizer.word_index

print('Found %s unique tokens.' % len(word_index))

print("WORD INDEX", word_index)

# Preprocessing
def myTokenize(arr):
    return tokenizer.texts_to_sequences(arr)
    # return text_to_word_sequence(arr,lower = False) # Lower causes problems

print("raw", xval[100:105])
prep_xvals = myTokenize(xval)
print("split",prep_xvals[100:105])

prep_xvals = pad_sequences(prep_xvals, maxlen = max_review_length, dtype = object, value="0")
print("padd",prep_xvals[100:105])
np.expand_dims(prep_xvals,axis=2)
print("shape", prep_xvals.shape)

# EMBEDDING
embed_dict = get_vector_dict(w2v_filepath,limit = 30000)
zero_vector = [0] * embedding_vector_length

# prepare embedding matrix
num_words = len(embed_dict) + 1
embedding_matrix = np.zeros((num_words, embedding_vector_length))
idx = 0
# word_to_int = {}
for word, i in word_index.items():
    if i >= num_words:
        continue

    if word in embed_dict:
        embedding_matrix[i] = embed_dict[word]
    else:
        # words not found in embedding index will be all-zeros.
        embedding_matrix[i] = zero_vector
    # word_to_int[word] = i
    idx += 1

print("embedding mat shape",embedding_matrix.shape)

embed_xvals = np.copy(prep_xvals)
# for k,v in word_to_int.items(): embed_xvals[prep_xvals==k] = v # Dict lookup for npArrays

my_embedding = Embedding(
    num_words,
    embedding_vector_length,
    embeddings_initializer=Constant(embedding_matrix),
    input_length=max_review_length,
    trainable = False
    )

print('Shape of data tensor:', embed_xvals.shape)
print("xval sample", embed_xvals[156])

# MODEL CONSTRUCTION

main_input = Input(shape=(max_review_length,), dtype='int32')

embed = my_embedding(main_input)

# 词窗大小分别为2,3,4
cnnunits = 64
cnn1 = Conv1D(cnnunits, 2, padding='same', strides=1, activation='relu')(embed)
cnn2 = Conv1D(cnnunits, 3, padding='same', strides=1, activation='relu')(embed)
cnn3 = Conv1D(cnnunits, 4, padding='same', strides=1, activation='relu')(embed)

# cnn1 = MaxPooling1D(pool_size=4)(cnn1)
# cnn2 = MaxPooling1D(pool_size=4)(cnn2)
# cnn3 = MaxPooling1D(pool_size=4)(cnn3)

# 合并三个模型的输出向量
# Concat 3 outputs into one
cnn = Concatenate(axis=-1)([cnn1, cnn2, cnn3])
cnn = BatchNormalization(momentum=0.99)(cnn)
flat = Flatten()(cnn)
# drop = Dropout(0.2)(flat)
# dense = Dense(units=128, activation='relu')(flat)
outs = Dense(units=64, activation='sigmoid')(flat)
model = Model(inputs=main_input, outputs=outs)

# model = Sequential()
# model.add(my_embedding)

# model.add(BatchNormalization(momentum=0.99))
# # model.add(Conv2D(128,3,strides=1,padding="same",activation='relu')) # Future?
# model.add(Conv1D(64,2,strides=1,padding="same",activation='relu'))
# model.add(BatchNormalization(momentum=0.99))
# # model.add(LSTM(units=128))
# model.add(Dense(units=256,activation='relu'))
# model.add(Dense(units=128,activation='relu'))
# model.add(Flatten())
# model.add(Dense(units=intents,activation='sigmoid'))

LEARN_RATE = 0.0001
optimizer = Adam(learning_rate=LEARN_RATE)
model.compile(optimizer, 'categorical_crossentropy', metrics=['accuracy'])

model.summary()

model.fit(x=embed_xvals,y=cat_yval,epochs=30,verbose=1,validation_split=0.1,batch_size=4)

# Post Training
model.save('241019_1600_model.h5')

test_in = ["我 很 爱 您","我 在 上 海","我 要 付 社 保","您 好","拍 好 了", "怎 么 拍", "社 保 可 以 补 交 吗","需 要 我 提 供 什 东 西 吗", "要 啥 材 料 吗", "请 问 可 以 代 缴 上 海 社 保 吗"]
ti = myTokenize(test_in)
input_array = pad_sequences(ti, max_review_length)
print("input",test_in)

output_array = model.predict(input_array)
# print("raw",output_array)

for bleh in output_array:
    pred_to_word(bleh)
