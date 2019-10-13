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
    - process query for auto labelling
    - auto label query
    - split labelled query into test,valid and train for intent-slot NLU
- set-up excel for collaboration
    

## In progress
- dataset (manual label)
    - build tools to help with labelling slot (refer to chatbot_resource, bot_Arm, bot_LeftBrain and excels when labelling) (kiv test label for now)
- NLU_classifier (problem with large dataset, add word embedding, rebuild from scratch using tf2.0, break into function)

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