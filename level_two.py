import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import nltk
from nltk.tokenize import WhitespaceTokenizer
from nltk.corpus import stopwords
import string
import pymc as pm
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import root_mean_squared_error
from sklearn.metrics import r2_score

# *** PART ONE ***
tk = WhitespaceTokenizer()
nltk.download('stopwords')
nltk.download('punkt_tab')
stop_words = set(stopwords.words('english'))
pd.set_option('display.max_columns', 100) 
vectorizer = TfidfVectorizer()


FILE_PATHS = ['export_harrypotter.csv']
DATAFRAMES = []
for path in FILE_PATHS:
    DATAFRAMES.append(pd.read_csv(path,  sep=','))

analyze_df = pd.DataFrame(columns=DATAFRAMES[0].columns.tolist() + ['month'])

# CLEAN DATA
# Helper method to extract keywords
def get_keywords(text):
    if type(text) == str:
        arr = nltk.word_tokenize(text) # get keywords
        arr = [word.lower() for word in arr if word.isalpha()] 
        arr = [x for x in arr if not x.lower() in stop_words] # remove stopwords
        return ' '.join(arr)
    return ''

def get_month(text):
    return text.split('-')[1]

for df in DATAFRAMES:
    # **A. Get keywords (from 'text')
    df['text'] = df['text'].apply(lambda x: get_keywords(x))

    # **B. Month (from 'date')
    df['month'] = df['date'].apply(lambda x: get_month(x))  

    # Append df to analyze_df
    analyze_df = pd.concat([analyze_df, df])

analyze_df = analyze_df[['ratings', 'month', 'text']]
#print(analyze_df.head(5))

# Check for NaN values
print(np.unique(analyze_df['ratings']))

# *** PART TWO ***
# goal: predict star rating distribution using bayesian regression
# DETERMINE PRIORS
# Ratings distribution
unique, counts = np.unique(analyze_df['ratings'], return_counts=True)
print("Ratings Data: ")
for a, b in zip(unique, counts):
    print(a, ": ", b)

# Result: Highly skewed left
print('\n')

unique, counts = np.unique(analyze_df['month'], return_counts=True)
print("Month Data: ")
for a, b in zip(unique, counts):
    print(a, ": ", b)

# Result: Peak in winter, low in summer/fall
print('\n')

subset = analyze_df[['text', 'ratings']]
stars_to_words = {1: [], 2: [], 3: [], 4: [], 5: []}
def gather_keywords(stars, words):
    stars_to_words[int(stars)] += words.split(' ')
subset.apply(lambda x: gather_keywords(x.ratings, x.text), axis=1)
for i in range(1,6):
    unique, counts = np.unique(stars_to_words[i], return_counts=True)
    tmp = pd.DataFrame({'word': unique, 'count': counts})
    tmp = tmp.sort_values(by='count', ascending=False)
    print("Top 20 for", str(i), "- STAR")
    print(tmp.head(20))

print('\n')

# CHECK ASSUMPTIONS

# *** PREDICT RATINGS BY MONTH ***
X = analyze_df['text'] 
y = analyze_df['ratings']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# *** PREDICT RATINGS BY KEYWORD ***
print('*****')
print('PREDICT BY KEYWORD')

from transformers import AutoTokenizer, AutoModelForSequenceClassification, DataCollatorWithPadding
from torch.utils.data import DataLoader
from datasets import load_metric

BASE_MODEL = "camembert-base"
LEARNING_RATE = 2e-5
MAX_LENGTH = 256
BATCH_SIZE = 16
EPOCHS = 20

X = analyze_df['text'] 
y = analyze_df['ratings']
train, validate, test = np.split(analyze_df.sample(frac=1, random_state=42), 
                                 [int(.6*len(analyze_df)), int(.8*len(analyze_df))])

# Classes 1-5 correspond to star numbers
id2label = {k:k for k in range(1, 6)}
label2id = {k:k for k in range(1, 6)}

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL, id2label=id2label, label2id=label2id)

ds = {"train": train, "validation": validate, "test": test}

def preprocess_function(text):
    label = text["ratings"] 
    text = tokenizer(text["text"], truncation=True, padding="max_length", max_length=256)
    text["label"] = label
    return text

for split in ds:
    ds[split] = ds[split].map(preprocess_function, remove_columns=["text", "ratings"])

# *** MODEL EVALUATION ***
print('*****')
print('MODEL ACCURACY')
rmse = root_mean_squared_error(y_test, y_preds)
print('RMSE:', rmse)

r2 = r2_score(y_test,y_preds)
print('R^2:', r2)