> # **Project Q!i@a#n$N%i^u Chatbot**

## File directory
- chatbot_server : deploy bot for testing locally
- QNPlugin.py : test the plugin
- utils.py : data processor

## DONE
- QNPlugin
- data_utils
    - load,save qn data by ID and QA
    - set-up excel for collaboration

## In progress
- data_utils (manual label 50 input everyday)
    - use test bot to build up template for labels
    - auto label input
    - build NLU model data pipeline
- train_NLU
- NLU_classifier
- Design Doc (for collabs)
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
- BiLSTM for entity classifier

- BiLSTM for state prediction