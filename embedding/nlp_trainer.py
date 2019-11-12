#encoding = utf-8
import csv
import json
import numpy as np
import jieba as jb

from unzipper import get_vector_dict
from keras.constraints import MaxNorm
from keras.initializers import Constant, RandomNormal, RandomUniform, glorot_normal, glorot_uniform
from keras.layers import Concatenate, Dropout, Embedding, LSTM, Dense, Conv1D, Flatten, BatchNormalization, MaxPooling1D
from keras.models import Model, Input
from keras.optimizers import Adam, RMSprop
from keras.preprocessing.text import Tokenizer, text_to_word_sequence
from keras.preprocessing.sequence import pad_sequences 
from keras.regularizers import l1,l2
from keras.utils import to_categorical

#### NOTES ####
# Run from 'embedding' folder

# Helpful functions
def save_to_json(filename, data):
    try:
        with open(filename,'w', encoding='utf8') as f:
            json.dump(data, f, indent = 4, ensure_ascii=0)
    except FileNotFoundError as fnf_error:
        print(fnf_error)

    print("Finished writing to " + str(filename))

def save_tokenizer(t, filename):
    json_yval = t.to_json()
    save_to_json(filename,json_yval)

# Word 2 vec
USE_WORD2VECTOR = False
VDLIMIT = 30000
w2v_filepath = "/Users/davidgoh/Desktop/sgns.weibo.bigram-char.bz2"

# Dataset and save location
dataset_fp = "generated_data.csv"
save_model_name = 'trained.h5'

# Parameters
max_review_length = 30 #maximum length of the sentence
embedding_vector_length = 128
max_intents = 120

### Information preprocessing ###
count = 0
with open(dataset_fp, 'r',encoding='gb18030') as f:
    rows = csv.reader(f, delimiter = ',')
    data = []
    for r in rows:
        if count > 0:
            data.append(r)
        count += 1
    print("Read {} rows".format(count))
    npdata = np.array(data,dtype=str)

xval = npdata[:,0]
yval = npdata[:,1]
yval = np.reshape(yval,(count-1))

intent_tokenizer = Tokenizer(max_intents,filters="",oov_token=0)
intent_tokenizer.fit_on_texts(yval)
ints_yval = intent_tokenizer.texts_to_sequences(yval)
# print(ints_yval[:50])
cat_yval = to_categorical(ints_yval)

# SAVE Y VAL TOKENIZER
save_tokenizer(intent_tokenizer, "yval_tokens.json")

num_intents = len(intent_tokenizer.word_index) + 1
print('Found %s unique intents.' %num_intents)

reverse_word_map = dict(map(reversed, intent_tokenizer.word_index.items()))

def pred_to_word(pred):
    top = 3
    total = np.sum(pred)
    s_pred = np.sort(pred,-1)
    best = None
    breakdown = ""

    for i in range(top):
        curr = s_pred[-1]
        if curr == 0:
            break
        s_pred = s_pred[:-1]
        idx = np.where(pred == curr)[0][0]
        intent = reverse_word_map[idx]
        if (best == None): best = intent 
        conf = round(curr*100/total,2)
        breakdown = breakdown + "<{}> Intent:{} Confidence:{}%\n".format(i+1, intent, conf)
    out = {"prediction":best,"breakdown":breakdown}
    print(out)

### Test reverse lookup for intent
# print("testing for",yval[415])
# test_reverse = cat_yval[415]
# print(pred_to_word(test_reverse))

#num_words is tne number of unique words in the sequence, if there's more top count words are taken

# Preprocessing
def get_unique_tokens(nparr):
    d = []
    for seq in nparr:
        for c in seq[0]:
            if not c in d:
                d.append(c)
    print("Found {} unique tokens".format(len(d)))
    return d

# BUILDS DICTIONARY
def buildWordToInt(w2v,ut):
    count = 1
    d = {"_NA":0}
    for c in w2v:
        if not c in d:
            d[c] = count
            count += 1
    for t in ut:
        if not t in d:
            d[t] = count
            count += 1
    print("Built a map of {} unique tokens".format(count))
    return d


def arrayWordToInt(nparr, d, dbg=False):
    nparr = np.array(nparr)
    newArray = np.copy(nparr)
    for k, v in d.items(): newArray[nparr==k] = v
    newArray[isinstance(newArray,str)] = 0
    if dbg: print(newArray)
    return newArray

# Returns an nparray of sequences, padded
def myTokenize(nparr):
    pyarr = nparr.tolist() if isinstance(nparr, np.ndarray) else nparr
    outarr = []
    for seq in pyarr:
        if isinstance(seq, np.ndarray):
            seq = nparr.tolist()

        seq = seq.replace(" ", "")
        jbseq = jb.lcut(seq, cut_all=True)
        jbseq = pad_sequences([jbseq,], maxlen = max_review_length, dtype = object, value="_NA")
        outarr.append(jbseq)
    return outarr

def tokenizer_fit_xvals(t_xvals):
    t = Tokenizer(num_words=None,lower=False, oov_token="_NA")
    t.fit_on_sequences(t_xvals)
    return t

def convert_txvals(t_xvals):
    t = tokenizer_fit_xvals(t_xvals)
    ints_xvals = t.texts_to_sequences(t_xvals)
    return (ints_xvals, t)

# EMBEDDING
prep_xvals = myTokenize(xval)
# embed_xvals, xvt = convert_txvals(prep_xvals)
# save_tokenizer(xvt, "xval_tokens.json")
# embed_xvals = np.array(embed_xvals)

ut = get_unique_tokens(prep_xvals)
# if USE_WORD2VECTOR:
    # embed_dict = get_vector_dict(w2v_filepath,limit = VDLIMIT)
    # zero_vector = [0] * embedding_vector_length
    # word2int = buildWordToInt(embed_dict,ut)
    # prep_xvals = arrayWordToInt(prep_xvals,word2int)
    # print("split",prep_xvals[100:105])
    # # prep_xvals = pad_sequences(prep_xvals, maxlen = max_review_length, dtype = object, value="0")
    # # print("padd",prep_xvals[100:105])
    # embed_xvals = np.reshape(prep_xvals,(prep_xvals.shape[0],prep_xvals.shape[2])) # Remove the 1 in the middle
    # print("shape", prep_xvals.shape)

    # # prepare embedding matrix
    # num_words = len(embed_dict) + embed_xvals.shape[0]
    # embedding_matrix = np.zeros((num_words, embedding_vector_length))
    # idx = 0

    # # Build dict for VECTORS
    # for word, i in word2int.items():
    #     if word in embed_dict:
    #         embedding_matrix[i] = embed_dict[word]
    #     else:
    #         # words not found in embedding index will be all-zeros.
    #         embedding_matrix[i] = zero_vector
    #     # word_to_int[word] = i
    #     idx += 1

    # print("embedding mat shape",embedding_matrix.shape)
    # # for k,v in word_to_int.items(): embed_xvals[prep_xvals==k] = v # Dict lookup for npArrays

    # my_embedding = Embedding(
    #     num_words,
    #     embedding_vector_length,
    #     embeddings_initializer=Constant(embedding_matrix),
    #     input_length=max_review_length,
    #     trainable = False
    #     )
# else:
num_words = len(ut)
word_index = buildWordToInt(ut,[])
prep_xvals = arrayWordToInt(prep_xvals,word_index)
embed_xvals = np.reshape(prep_xvals,(prep_xvals.shape[0],prep_xvals.shape[2])) # Remove the 1 in the middle

save_to_json("xval_man_tokens.json",str(word_index))

reg = l2(0.01)
# embed_init = glorot_uniform(seed=714)
embed_init = RandomUniform(seed=313)

my_embedding = Embedding(
    num_words,
    embedding_vector_length,
    embeddings_initializer = embed_init,
    activity_regularizer = None,
    embeddings_constraint = MaxNorm(max_value=2,axis=0),
    input_length=max_review_length,
    trainable = True
    )

print('Shape of data tensor:', embed_xvals.shape)
print("xval sample", embed_xvals[156])

# MODEL CONSTRUCTION

main_input = Input(shape=(max_review_length,), dtype='int32')

embed = my_embedding(main_input)
embed = BatchNormalization(momentum=0.99)(embed)

# 词窗大小分别为 2 3 4
cnnUnits = 128 # 
cnn1 = Conv1D(cnnUnits, 2, padding='same', strides=1, activation='relu')(embed)
cnn2 = Conv1D(cnnUnits, 3, padding='same', strides=1, activation='relu')(embed)
cnn3 = Conv1D(cnnUnits, 4, padding='same', strides=1, activation='relu')(embed)

# cnn1 = MaxPooling1D(pool_size=4)(cnn1)
# cnn2 = MaxPooling1D(pool_size=4)(cnn2)
# cnn3 = MaxPooling1D(pool_size=4)(cnn3)

# 合并三个模型的输出向量
# Concat 3 outputs into one
cnn = Concatenate(axis=-1)([cnn1, cnn2, cnn3])
cnn = BatchNormalization(momentum=0.99)(cnn)

flat = Flatten()(cnn)
flat = Dropout(0.2)(flat)
# flat = Dense(units=256, activation='relu')(flat) # 
outs = Dense(units=num_intents, activation='sigmoid')(flat)
model = Model(inputs=main_input, outputs=outs)


LEARN_RATE = 3e-5
optimizer = Adam(learning_rate=LEARN_RATE)
# optimizer = RMSprop(learning_rate = 3e-5)
model.compile(optimizer, 'categorical_crossentropy', metrics=['accuracy'])

model.summary()

model.fit(x=embed_xvals,y=cat_yval,epochs=100,verbose=1,validation_split=0.0,batch_size=16,shuffle=True)

# Post Training
model.save(save_model_name)
print("This Model has been saved! Rejoice")

test_in = ["我在苏州的不是首次","我是要付社保行吗","您好","哦了解了", "我已经填好了", "我拍好了", "流程到底是怎么样的？", "苏州社保可以交吗", "可以交昆山社保吗", "交卡行吗哦", "代缴社保", "落户上海", "上海社保可以吗", "这个我不太懂哦","社保可以补交吗","公积金可以补交吗","需要我提供什东西吗","要啥材料吗","社保卡怎么弄"]

ti = myTokenize(test_in)
# print("input",test_in)
input_array = arrayWordToInt(ti,word_index,1)
input_array = np.reshape(input_array,(input_array.shape[0],input_array.shape[2])) # Remove the 1 in the middle
output_array = model.predict(input_array)
# print("raw",output_array)

i = 0
for bleh in output_array:
    print(test_in[i])
    print(input_array[i])
    i+=1
    pred_to_word(bleh)
