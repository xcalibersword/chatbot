import nltk
from nltk.stem.lancaster import LancasterStemmer
stemmer = LancasterStemmer()

import numpy as np
import tflearn
import tensorflow as tf
import random

import json
with open('intents.json') as json_data:
    intents = json.load(json_data)
    classes = []
    documents = []
    ignore_words = ['?']