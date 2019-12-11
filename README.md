> # **Project Q!i@a#n$N%i^u Chatbot**

## Project Dependencies
- tensorflow 1.14
- pywin32
- Jpype1
- jieba
- pandas
- keras
- pymssql<3.0
- aiohttp
- python-socketio
- JAVA VERSION
- jdk 12.0.2

## Key Features to be built for
- Calculate product price
- Check regional payment deadline
- Check product benefit coverage
- Check region coverage

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
    - process query for auto labelling (tokenise, word2vec, abstract)
- dataset
    - build tools to help with labelling slot
    - set-up excel for collaboration
    - set-up template for labeling

## In progress
- dataset
    - manual label
- feature
    - context
    - product details

## For future
- Design Doc (for collabs)
- test bot (build up template for labels)
- NLU_classifier (add word embedding, use best practise)
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
- Sentiment analysis (identify complains, tone)

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