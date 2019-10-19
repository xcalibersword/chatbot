> # **Project Q!i@a#n$N%i^u Chatbot**

## File directory
- chatbot_server : deploy bot for testing locally
- QNPlugin.py : test the plugin
- data_utils.py : data processor

## DONE
- QNPlugin
- data_utils
    - load qn data
    - process and save data by ID, QA and query
    - split labelled query into test,valid and train for intent-slot NLU
- dataset
    - build tools to help with labelling slot
    - set-up excel for collaboration

## In progress
- dataset
    - set-up template for labeling
    - manual label
- data_utils
    - process query for auto labelling (tokenise, word2vec, abstract)
- NLU_classifier (add word embedding, use best practise)

## For future
- Design Doc (for collabs)
- test bot (build up template for labels)
- Dialog State Tracking
    - state
    - database/json
- Policy (story)
- Action
    - api
    - template
    - kbQA for FAQ
    - GAN for chit chat
    - recommendation system using IR on customer profile database
- NLG
    - language 
    - emotion 
    - emoji 
    - pictures

## Art of conversation
- Understand Context

## Useful resources
- [Seq2Seq Chinese Chatbot on android](http://www.shareditor.com/blogshow/?blogId=63)

## SOTA Models to use
- DCNN for word embedding
- TCNN for intent classifier
- slot-gated for intent-slot classifier
- BiLSTM for entity classifier (seq labeling)
- BiLSTM for state prediction