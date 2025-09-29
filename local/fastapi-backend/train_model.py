import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression # MUDANÇA: Importando Regressão Logística
from sklearn.metrics import classification_report
from joblib import dump
import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer
import re
import unicodedata
from contextlib import suppress

# --- PREPROCESSING FUNCTIONS (COPIED FROM main.py FOR CONSISTENCY) ---

# Download necessary NLTK data (only runs if data is missing)
with suppress(LookupError):
    stopwords.words('portuguese')
    RSLPStemmer()
    
# Attempt to download resources if missing
try:
    stopwords.words('portuguese')
    RSLPStemmer()
except LookupError:
    print("Downloading NLTK resources: 'stopwords' and 'rslp'...")
    nltk.download('stopwords')
    nltk.download('rslp')

PORTUGUESE_STOP_WORDS = set(stopwords.words('portuguese'))
PORTUGUESE_STEMMER = RSLPStemmer()

def preprocess_text(text: str) -> str:
    """
    Applies standard NLP preprocessing for Portuguese:
    1. Tokenization (basic split)
    2. Lowercasing
    3. Accent Removal (Crucial for RSLP consistency)
    4. Stop word removal
    5. Stemming
    6. Joining tokens back into a string
    """
    tokens = text.lower().split()
    processed_tokens = []
    
    for token in tokens:
        
        # 3. Accent Removal (Normalization)
        normalized_token = unicodedata.normalize('NFKD', token).encode('ascii', 'ignore').decode('utf-8')

        # Simple removal of punctuation and cleanup
        clean_token = normalized_token.strip(".,;!?\"'()[]{}") 

        # Remove any remaining non-alphabetic characters (including digits)
        clean_token = re.sub(r'[^a-z]', '', clean_token)

        if not clean_token:
            continue
        
        # 4. Stop word removal
        if clean_token in PORTUGUESE_STOP_WORDS:
            continue
        
        # 5. Stemming
        stemmed_token = PORTUGUESE_STEMMER.stem(clean_token)
        
        processed_tokens.append(stemmed_token)
        
    return " ".join(processed_tokens)

# --- END OF PREPROCESSING FUNCTIONS ---


def train_and_save_model(data_path: str = 'emails.csv'):
    """
    Loads data, preprocesses it, trains a Logistic Regression classifier,
    and saves the model and vectorizer using Joblib.
    """
    print(f"--- Starting Model Training for '{data_path}' ---")

    # 1. Load Data
    try:
        # Use sep=',' and quotechar='"' to handle the corrected CSV file
        df = pd.read_csv(data_path, sep=',', quotechar='"')
        # Ensure the expected columns exist
        if 'text' not in df.columns or 'label' not in df.columns:
            raise ValueError("CSV must contain 'text' and 'label' columns.")
    except FileNotFoundError:
        print(f"Error: Dataset file '{data_path}' not found.")
        print("Please ensure 'emails.csv' is in the same directory.")
        return
    except Exception as e:
        print(f"Data loading error: {e}")
        print("Please ensure your CSV is correctly formatted with 'text' and 'label' columns.")
        return

    print(f"Loaded {len(df)} samples.")
    
    # 2. Apply Preprocessing to Text Data
    print("Applying NLP preprocessing (Stemming, Stop Word Removal)...")
    df['processed_text'] = df['text'].apply(preprocess_text)
    
    # 3. Split Data
    X = df['processed_text']
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. Feature Engineering (TF-IDF Vectorization)
    print("Training TF-IDF Vectorizer...")
    # NOTE: The vectorizer learns the vocabulary ONLY from the training set.
    vectorizer = TfidfVectorizer()
    X_train_vectorized = vectorizer.fit_transform(X_train)
    X_test_vectorized = vectorizer.transform(X_test)
    
    # 5. Model Training (Logistic Regression)
    print("Training Logistic Regression Classifier...")
    # Logistic Regression é um ótimo modelo de baseline que dá maior robustez que o MNB
    classifier = LogisticRegression(solver='liblinear', random_state=42) 
    classifier.fit(X_train_vectorized, y_train)

    # 6. Evaluation
    print("\n--- Model Evaluation ---")
    y_pred = classifier.predict(X_test_vectorized)
    print(classification_report(y_test, y_pred))

    # 7. Persistence (Saving Model and Vectorizer)
    model_path = 'model.joblib'
    vectorizer_path = 'vectorizer.joblib'
    
    dump(classifier, model_path)
    dump(vectorizer, vectorizer_path)
    
    print("\n--- Training Complete ---")
    print(f"Classifier saved to: {model_path}")
    print(f"Vectorizer saved to: {vectorizer_path}")
    print("You can now integrate these files into your FastAPI application.")


if __name__ == '__main__':
    # Dependencies required: pip install pandas scikit-learn joblib nltk
    
    # The script now expects 'emails.csv' to be present in the working directory.
    train_and_save_model()
