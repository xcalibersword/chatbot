import numpy as np
import tensorflow as tf
import os
from utils import loadVocabulary, sentenceToIds

main_path = r'D:\chatbot\test_NLU(intent-slot)'            
ckpt_path = os.path.join(main_path,'model')
meta_path = os.path.join(main_path,'model\_step_1424_epochs_9.ckpt.meta')
input_vocab_path = os.path.join(main_path,'vocab\in_vocab')
intent_vocab_path = os.path.join(main_path,'vocab\intent_vocab')
slot_vocab_path = os.path.join(main_path,'vocab\slot_vocab')

def view_variables(aa):
    if aa == "tvs":
        tvs = [v for v in tf.trainable_variables()]
        for v in tvs:
            print(v.name)
            print(sess.run(v))
    if aa == "gv":
        gv = [v for v in tf.global_variables()]
        for v in gv:
            print(v.name)
    if aa == "ops":
        ops = [o for o in sess.graph.get_operations()]
        for o in ops:
            print(o.name)
            
sess=tf.Session()    
#load model and impt parameters
saver = tf.train.import_meta_graph(meta_path)
saver.restore(sess,tf.train.latest_checkpoint(ckpt_path))

graph = tf.get_default_graph()
msg = graph.get_tensor_by_name("inputs:0")
seq_len = graph.get_tensor_by_name("sequence_length:0")
intent = graph.get_tensor_by_name("intent_output:0")
#if never use crf
slot = graph.get_tensor_by_name("slot_output:0")
#if use crf

in_vocab = loadVocabulary(input_vocab_path)
intent_vocab = loadVocabulary(intent_vocab_path)
slot_vocab = loadVocabulary(slot_vocab_path)

idx2word = in_vocab['rev']
while True:
    message = input("Enter message: ")
    if message == "stop":
        print("The End!")
        break
    else:
        #preprocess new data for prediction
        message = message.rstrip()
        
        #input idx
        #
        inp = sentenceToIds(message, in_vocab)
        a = np.array(inp)
        b = []
        b.append(a)
        c = np.array(b)
        #print(c)

        #seq_len
        j = []
        k = len(inp)
        j.append(k)
        l = np.array(j)
        #print(l)

        #predict intent
        pred_intent_array = sess.run(intent, feed_dict={msg:c,seq_len:l})
        #print(pred_intent_array)
        pred_intent_idx = np.argmax(pred_intent_array)
        #print(pred_intent_idx)
        #
        idx2intent = intent_vocab["rev"]
        pred_intent_word = idx2intent[pred_intent_idx]
        print(pred_intent_word)
        #predict slots
        pred_slot_array_array = sess.run(slot, feed_dict={msg:c,seq_len:l})
        #print(pred_slot_array_array)
        #pred_slot_array_array = pred_slot_array_array.reshape(16, 33, -1)

        #if use crf
        #pred_slot_array = pred_slot_array_array.reshape([-1])
        #if never use crf
        pred_slot_array = np.argmax(pred_slot_array_array,1)
        #print(pred_slot_array)
        #
        pred_slot_word = []
        for idx in range(k):
            pred_slot_word.append(slot_vocab['rev'][pred_slot_array[idx]])
        print(pred_slot_word)

        slot_details = {}
        for i in range(k):
            if pred_slot_word[i][0] == 'B':
                slot_details[pred_intent_word[i][2:]] = idx2word[inp[i]]
            if pred_slot_word[i][0] == 'I':
                slot_details[pred_intent_word[i][2:]] += idx2word[inp[i]]
        print(slot_details)

#convert to slot value pair

#get chinese data, chinese word embedding if necessary


#improve to the model, see how rule based can come in to improve the effect
#read up on xgboost

#new method of retriving data from qianniu, sikuli or qianniu api
#new method of preprocessing data from qianniu, pattern matching of user
#new method of using small model to tag data and feed it back