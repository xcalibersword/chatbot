#encoding = utf-8
import csv
import json
import numpy as np
import jieba as jb

from unzipper import get_vector_dict
from keras.constraints import MaxNorm
from keras.callbacks import callbacks
from keras.initializers import Constant, RandomNormal, RandomUniform, glorot_normal, glorot_uniform
from keras.layers import Concatenate, Dropout, Embedding, LSTM, Dense, Conv1D, Flatten, BatchNormalization, MaxPooling1D, Reshape, ReLU
from keras.models import Model, Input
from keras.optimizers import Adam, RMSprop
from keras.backend import clear_session, expand_dims
from keras.preprocessing.text import Tokenizer, text_to_word_sequence
from keras.preprocessing.sequence import pad_sequences 
from keras.regularizers import l1,l2
from keras.utils import to_categorical
from nlp_utils import preprocess_sequence, postprocess_sequence, get_test_set

#### NOTES ####
# Run from 'embedding' folder

clear_session() # CLEAR KERAS SESSION

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
max_review_length = 32 # maximum length of the sentence
embedding_vector_length = 128 # Note that new/unseen words will have a n sized zero-vector
max_intents = 150

### Information preprocessing ###
count = 0
with open(dataset_fp, 'r',encoding='gb18030') as f:
    rows = csv.reader(f, delimiter = ',')
    data = []
    for r in rows:
        data.append(r)
        count += 1
    print("Read {} rows".format(count))
    npdata = np.array(data,dtype=str)

xval = npdata[:,0]
yval = npdata[:,1]
yval = np.reshape(yval,count)

intent_tokenizer = Tokenizer(max_intents,filters="",oov_token=0)
intent_tokenizer.fit_on_texts(yval)

def intents_to_categorical(raw_y):    
    ints_yval = intent_tokenizer.texts_to_sequences(raw_y)
    return to_categorical(ints_yval)

cat_yval = intents_to_categorical(yval)

# SAVE Y VAL TOKENIZER
save_tokenizer(intent_tokenizer, "yval_tokens.json")

num_intents = len(intent_tokenizer.word_index) + 1
print('Found %s unique intents.' %len(intent_tokenizer.word_index))

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


def arrayWordToInt(nparr, d):
    nparr = np.array(nparr)
    newArray = np.copy(nparr)
    for k, v in d.items(): newArray[nparr==k] = v
    for i in range(len(newArray)):
        row = newArray[i]
        for j in range(len(row)):
            if isinstance(row[j], str):
                newArray[i][j] = 0
    return newArray

# Returns an nparray of sequences, padded
def myTokenize(nparr):
    pyarr = nparr.tolist() if isinstance(nparr, np.ndarray) else nparr
    outarr = []
    for seq in pyarr:
        if isinstance(seq, np.ndarray):
            seq = nparr.tolist()

        seq = seq.replace(" ", "")
        seq = preprocess_sequence(seq) # REMOVES STOPWORDS
        jbseq = jb.lcut(seq, cut_all=True)
        jbseq = postprocess_sequence(jbseq)
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

def reshape_xvals(xvals):
    # Remove the column (x, 1 ,x') in the middle
    return np.reshape(xvals,(xvals.shape[0],xvals.shape[2]))

def prep_feed_model(x, wordindex):
    x = np.array(x)
    mid = reshape_xvals(x)
    out = arrayWordToInt(mid, wordindex)
    return out

# EMBEDDING
prep_xvals = myTokenize(xval)
# embed_xvals, xvt = convert_txvals(prep_xvals)
# save_tokenizer(xvt, "xval_tokens.json")
# embed_xvals = np.array(embed_xvals)

ut = get_unique_tokens(prep_xvals)
num_words = len(ut)
word_index = buildWordToInt(ut,[])

embed_xvals = prep_feed_model(prep_xvals,word_index)
rawtest_x, rawtest_y = get_test_set()
rawtest_x = myTokenize(rawtest_x)
test_x = prep_feed_model(rawtest_x,word_index)
test_y = intents_to_categorical(rawtest_y)

save_to_json("xval_man_tokens.json",str(word_index))

reg = l2(0.01)
# embed_init = RandomUniform(seed=313)
embed_init = RandomUniform(seed=15)

my_embedding = Embedding(
    num_words,
    embedding_vector_length,
    embeddings_initializer = embed_init,
    activity_regularizer = reg,
    embeddings_constraint = MaxNorm(max_value=2,axis=0),
    input_length=max_review_length,
    trainable = True
    )

print('Shape of data tensor:', embed_xvals.shape)
print("xval sample", embed_xvals[156])
print('Shape of test tensor:', test_x.shape)
print("test xval sample", test_x[0])

# MODEL CONSTRUCTION

main_input = Input(shape=(max_review_length,), dtype='int32')

embed = my_embedding(main_input)
embed = Dropout(0.2)(embed)
embed = BatchNormalization(momentum=0.99)(embed)

# 词窗大小分别为 2, 3, 4, 5
base_units = 64
cnnUnits_multi = [2, 2, 2, 2]
pool_multi = [4, 4, 4, 4]
filter_sizes = [3, 4, 6, 8] # Original was 3,4,5
cnn_activ = 'relu'

# Pool size is the sliding window length.
# Strides is the number of indices that are moved between each pool sample.
# No sense having pool_size bigger than stride because its MaxPool.
# Having a bigger pool than stride means each max point will obscure the results more.
# Originally, all were size 4.
fcnns = []
for i in range(0,4):
    cl = Conv1D(cnnUnits_multi[i]*base_units, filter_sizes[i], padding='same', strides=1, activation=cnn_activ, kernel_regularizer=None)(embed)
    pool_unit = int(cnnUnits_multi[i]*pool_multi[i])
    pl = MaxPooling1D(pool_size=pool_unit, strides=pool_unit)(cl)
    fl = Flatten()(pl)
    fcnns.append(fl)

flat = Concatenate(axis=-1)(fcnns) # 合并4个模型的输出向量

flat = BatchNormalization(momentum=0.9)(flat)
flat = Dropout(0.2)(flat)

flat = Dense(units=256, activation='relu')(flat) # 
flat = Dropout(0.1)(flat)

flat = Dense(units=2048, activation='relu')(flat) # 
flat = Dropout(0.2)(flat)

# flat = Dense(units=512, activation='relu')(flat) # 
# flat = Dropout(0.2)(flat)

# LSTM takes forever
# LSTM_shape = (256, 1)
# flat = Reshape(LSTM_shape)(flat)
# flat = LSTM(units=128, activation='tanh', dropout=0.2)(flat) #

outs = Dense(units=num_intents, activation='softmax')(flat) # Sigmoid or softmax?
model = Model(inputs=main_input, outputs=outs)

# VAl accuracy of 0.94 is good

INITIAL_LEARN_RATE = 4e-4 
optimizer = Adam(learning_rate=INITIAL_LEARN_RATE)
# optimizer = RMSprop(learning_rate = 3e-5)
model.compile(optimizer, 'categorical_crossentropy', metrics=['accuracy'])

cbks = [
    callbacks.TerminateOnNaN(),
    callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=7, verbose=1),
    callbacks.EarlyStopping(monitor='loss', min_delta=0, patience=10, verbose=1, baseline=None, restore_best_weights=True)
]

model.summary()

test_set = (test_x, test_y)
# Can't have validation split because too many intents.
model.fit(x=embed_xvals,y=cat_yval,epochs=100,verbose=1,validation_split=0.0,batch_size=16,shuffle=True,validation_data=test_set,callbacks=cbks) 

# Post Training
model.save(save_model_name)
print("This Model has been saved! Rejoice")


# ti = myTokenize(test_in)
# input_array = arrayWordToInt(ti,word_index)
# input_array = np.reshape(input_array,(input_array.shape[0],input_array.shape[2])) # Remove the 1 in the middle
# output_array = model.predict(input_array)

# i = 0
# for bleh in output_array:
#     print(test_in[i])
#     i+=1
#     pred_to_word(bleh)