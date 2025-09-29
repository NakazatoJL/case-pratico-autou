from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List
from contextlib import asynccontextmanager
from joblib import load
import httpx
import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer
import re
import unicodedata
import os
import asyncio # Necessário para o httpx e retry logic
from google.cloud import storage

# # --- GEMINI API Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") # Para rodar em docker
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key="
# ------------------------------

# --- GLOBAL MODEL VARIABLES ---
CLASSIFIER_MODEL = None
TFIDF_VECTORIZER = None
MODEL_PATH = 'model.joblib'
VECTORIZER_PATH = 'vectorizer.joblib'
# --- REGRA DE NEGÓCIO ---
WORD_COUNT_THRESHOLD = 4 # Mensagens com 4 palavras ou menos serão classificadas como 'unproductive'
# ------------------------------

MODEL_PATH = 'model.joblib'
VECTORIZER_PATH = 'vectorizer.joblib'
GCS_BUCKET = os.environ.get('MODEL_BUCKET', '')

async def download_from_gcs(bucket_name, blob_name, dest_path):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(dest_path)

# --- NLP SETUP ---
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
    Aplica o pré-processamento NLP (normalização, remoção de stopwords, stemming RSLP).
    """
    tokens = text.lower().split()
    processed_tokens = []
    
    for token in tokens:
        normalized_token = unicodedata.normalize('NFKD', token).encode('ascii', 'ignore').decode('utf-8')
        clean_token = normalized_token.strip(".,;!?\"'()[]{}") 
        clean_token = re.sub(r'[^a-z]', '', clean_token)

        if not clean_token:
            continue
        
        if clean_token in PORTUGUESE_STOP_WORDS:
            continue
        
        stemmed_token = PORTUGUESE_STEMMER.stem(clean_token)
        processed_tokens.append(stemmed_token)
        
    return " ".join(processed_tokens)
# --- END OF PREPROCESSING SETUP ---

# --- MODEL LOADING LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    if GCS_BUCKET and (not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH)):
        try:
            download_from_gcs(GCS_BUCKET, MODEL_PATH, MODEL_PATH)
            download_from_gcs(GCS_BUCKET, VECTORIZER_PATH, VECTORIZER_PATH)
        except Exception as e:
            print("Failed to download models from GCS:", e)

    # Load the models when the application starts
    global CLASSIFIER_MODEL, TFIDF_VECTORIZER
    print("Loading classification models...")
    
    if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH):
        print(f"WARNING: Model files ({MODEL_PATH} or {VECTORIZER_PATH}) not found.")
        print("Please run the training script first.")
    else:
        try:
            CLASSIFIER_MODEL = load(MODEL_PATH)
            TFIDF_VECTORIZER = load(VECTORIZER_PATH)
            print("Models loaded successfully. Classification enabled.")
        except Exception as e:
            print(f"ERROR: Failed to load models with joblib: {e}")
            CLASSIFIER_MODEL = None
            TFIDF_VECTORIZER = None
            
    yield
    print("Shutting down application...")
# -------------------------------------


# 1. Pydantic Model for Request Body
class StringListRequest(BaseModel):
    message: List[str] = Field(
        default_factory=list,
        description="A list of strings (email bodies) to be classified."
    )

# 2. FastAPI Application Initialization
app = FastAPI(
    title="Express-FastAPI Communication Service",
    description="Classifies Portuguese emails (local ML) and generates response suggestions (Gemini API).",
    version="1.0.4",
    lifespan=lifespan
)

# --- GEMINI API CALLER WITH RETRY LOGIC (Using httpx) ---
async def generate_suggestion(email_text: str, classification: str) -> str:
    """Calls the Gemini API to generate a response suggestion with retry logic."""
    
    # Define a clear System Instruction for the LLM persona
    system_prompt = (
        "You are an AI assistant specialized in professional email responses in Portuguese. "
        f"The user provides an email which you have classified as '{classification}'. "
        "Your task is to generate a concise, professional, and actionable draft response (maximum 3 sentences) in Portuguese. "
        "Do not include any introductory text or commentary, just the suggested reply."
    )
    
    user_query = f"O e-mail para responder é:\n---\n{email_text}\n---"
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    
    # Verifica a chave antes de iniciar a chamada
    if not GEMINI_API_KEY:
        return "Erro: Chave de API Gemini não configurada. Serviço de sugestão desativado."

    # Lógica de Retry com Exponential Backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{GEMINI_API_URL}{GEMINI_API_KEY}",
                    headers={"Content-Type": "application/json"},
                    json=payload
                )

                # Levanta HTTPStatusError para status 4xx/5xx (exceto 429)
                response.raise_for_status() 

                result = response.json()
                
                # Extrai o texto gerado
                candidate = result.get('candidates', [{}])[0]
                generated_text = candidate.get('content', {}).get('parts', [{}])[0].get('text', 'Nenhuma sugestão gerada.')
                
                return generated_text

        except httpx.HTTPStatusError as e:
            # Se for um erro do servidor (5xx) ou erro de requisição que pode ser temporário
            if e.response.status_code == 429 or e.response.status_code >= 500:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Tentativa {attempt + 1} falhou (Status {e.response.status_code}). Tentando novamente em {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Erro final (Status {e.response.status_code}) após {max_retries} tentativas.")
                    return f"Erro ao gerar sugestão: Limite de tentativas excedido (Status {e.response.status_code})."
            else:
                # Erros que não são temporários (400 Bad Request, 401 Unauthorized, etc.)
                print(f"Erro de requisição não recuperável (Status {e.response.status_code}). Detalhes: {e.response.text}")
                return f"Erro ao gerar sugestão: Requisição inválida (Status {e.response.status_code})."

        except httpx.RequestError as e:
            print(f"Erro de conexão/timeout: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Tentativa {attempt + 1} falhou (Erro de conexão). Tentando novamente em {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                return "Erro de conexão: Limite de tentativas excedido."

    return "Erro desconhecido ao processar a sugestão."


# 3. POST Endpoint for Classification and Suggestion
@app.post("/processText")
async def classify_and_suggest(request_data: StringListRequest):
    """
    Recebe uma lista de strings (emails), classifica cada um usando o 
    modelo local (ou regra de negócio) e gera uma sugestão de resposta.
    """
    
    if CLASSIFIER_MODEL is None or TFIDF_VECTORIZER is None:
        # Se os modelos não carregaram (arquivos .joblib faltando)
        raise HTTPException(
            status_code=503, 
            detail="Modelos ML não carregados. Por favor, garanta que 'model.joblib' e 'vectorizer.joblib' existam."
        )

    results = []
    
    if not request_data.message:
        return {
            "status": "success",
            "processed_count": 0,
            "results": [],
            "detail": "Lista vazia recebida, nenhum processamento realizado."
        }

    for text in request_data.message:
        # 1. Verificação de Limite de Palavras (Regra de Negócio)
        word_count = len(text.split())
        
        classification = None
        processed_text = ""

        if word_count <= WORD_COUNT_THRESHOLD:
            # Regra: Se a mensagem for muito curta, force a classificação para improdutiva.
            classification = 'unproductive'
            processed_text = "N/A (Poucas palavras)"
        else:
            # 2. Pré-processamento e Classificação (Usando o Modelo ML)
            processed_text = preprocess_text(text)
            text_vectorized = TFIDF_VECTORIZER.transform([processed_text])
            
            # Preditção:
            classification = CLASSIFIER_MODEL.predict(text_vectorized)[0] # 'productive' ou 'unproductive'
            # prediction_proba = CLASSIFIER_MODEL.predict_proba(text_vectorized) 
            # confidence = prediction_proba.max()

        # 3. Geração de Sugestão (Usando Gemini API)
        suggestion = await generate_suggestion(text, classification)
        
        #Traduz a classfificacao
        if(classification == 'productive'):
            classification = 'Produtivo' 
        elif(classification == 'unproductive'):
            classification = 'Improdutivo' 

        results.append({
            "original_text": text,
            "classification": classification,
            "processed_text": processed_text,
            "suggestion": suggestion
        })

    return {
        "status": "success",
        "processed_count": len(results),
        "results": results
    }