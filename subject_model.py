import pandas as pd
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Bidirectional, LSTM, Dense, Dropout
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Load dataset (abstract, subject columns required)
data = pd.read_csv("research_dataset.csv")

X = data['abstract']
y = data['subject'].apply(lambda x: x.split()[0])

label_encoder = LabelEncoder()
y = label_encoder.fit_transform(y)

tokenizer = Tokenizer(num_words=8000)
tokenizer.fit_on_texts(X)
X_seq = tokenizer.texts_to_sequences(X)
X_pad = pad_sequences(X_seq, maxlen=250)

X_train, X_test, y_train, y_test = train_test_split(X_pad, y, test_size=0.2)

model = Sequential()
model.add(Embedding(8000, 128, input_length=250))
model.add(Bidirectional(LSTM(128)))
model.add(Dropout(0.5))
model.add(Dense(64, activation='relu'))
model.add(Dense(len(set(y)), activation='softmax'))

model.compile(loss='sparse_categorical_crossentropy',
              optimizer='adam',
              metrics=['accuracy'])

model.fit(X_train, y_train, epochs=6, batch_size=32)

model.save("model/subject_model.h5")
pickle.dump(tokenizer, open("model/tokenizer.pkl", "wb"))
pickle.dump(label_encoder, open("model/label_encoder.pkl", "wb"))