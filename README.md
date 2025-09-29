# Case Prático AutoU - Desenvolvimento

Este projeto é composto por duas aplicações: um backend baseado em Python com FastAPI e um frontend baseado em Node.js com Express. Abaixo estão as instruções para configurar e executar o projeto localmente, implantá-lo usando Docker e treinar o modelo de classificação.

## Pré-requisitos

- **Python 3.8+** (para FastAPI e treinamento do modelo)
- **Node.js 16+** (para Express)
- **Docker** (para implantação em contêineres)
- **Google Cloud SDK** (para implantação com Docker)
- **Projeto no Google Cloud** com faturamento ativado (para implantação com Docker)

## Configuração Local

### Backend FastAPI

1. **Navegue até o diretório do FastAPI**:
   ```bash
   cd fastapi-backend
   ```

2. **Instale as dependências**:
   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

3. **Crie um arquivo `.env`** no diretório `fastapi-backend` com o seguinte conteúdo:
   ```plaintext
   GEMINI_API_KEY=sua-chave-api-gemini
   ```

4. **Verifique os arquivos do modelo**:
   Certifique-se de que os arquivos `model.joblib` e `vectorizer.joblib` estão presentes no diretório `fastapi-backend`. Esses arquivos são necessários para a classificação de e-mails.

5. **Execute o servidor FastAPI**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   O backend FastAPI estará disponível em `http://localhost:8000`.

### Frontend Express

1. **Navegue até o diretório do Express**:
   ```bash
   cd express-frontend
   ```

2. **Instale as dependências**:
   ```bash
   npm install
   ```

3. **Crie um arquivo `.env`** no diretório `express-frontend` com o seguinte conteúdo:
   ```plaintext
   FAST_API=http://localhost:8000
   ```

4. **Execute o servidor Express**:
   ```bash
   npm start
   ```

   O frontend Express estará disponível em `http://localhost:8080`.

## Implantação com Docker

### Backend FastAPI

1. **Verifique os arquivos do modelo**:
   Certifique-se de que os arquivos `model.joblib` e `vectorizer.joblib` estão incluídos no diretório `fastapi-backend` antes de construir a imagem Docker.

2. **Construa e envie a imagem Docker**:
   ```bash
   PROJECT_ID=$(gcloud config get-value project)
   gcloud builds submit --tag gcr.io/$PROJECT_ID/fastapi-email-classifier:v1
   ```

3. **Implante no Google Cloud Run**:
   ```bash
   gcloud run deploy fastapi-email-classifier \
     --image gcr.io/$PROJECT_ID/fastapi-email-classifier:v1 \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
     --set-env-vars MODEL_BUCKET=seu-nome-de-bucket \
     --memory=512Mi \
     --concurrency=50
   ```

   Substitua `seu-nome-de-bucket` pelo nome do seu bucket do Google Cloud Storage.

### Frontend Express

1. **Construa e envie a imagem Docker**:
   ```bash
   PROJECT_ID=$(gcloud config get-value project)
   SERVICE_NAME="case-autou-express-app"
   NEW_TAG="v1"
   docker build -t $SERVICE_NAME:$NEW_TAG .
   docker tag $SERVICE_NAME:$NEW_TAG gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG
   docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG
   ```

2. **Implante no Google Cloud Run**:
   ```bash
   gcloud run deploy $SERVICE_NAME \
     --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG \
     --set-secrets FAST_API=fast-api-route:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080
   ```

## Observações

- Certifique-se de ter o Google Cloud SDK instalado e autenticado com `gcloud auth login` antes de implantar no Google Cloud Run.
- Configure os segredos necessários (`gemini-api-key:latest` e `fast-api-route:latest`) no seu projeto do Google Cloud antes da implantação.
- Para execuções locais, verifique se os arquivos `.env` estão configurados corretamente com as chaves de API e rotas apropriadas.
- O backend FastAPI precisa estar em execução e acessível para que o frontend Express funcione corretamente.

## Treinamento do Modelo de Classificação

Para reproduzir o treinamento do modelo de classificação utilizado pelo backend FastAPI, siga os passos abaixo:

1. **Navegue até o diretório do FastAPI**:
   ```bash
   cd fastapi-backend
   ```

2. **Verifique o arquivo de dados**:
   Certifique-se de que o arquivo `emails.csv` está presente no diretório `fastapi-backend`. Este arquivo contém os dados necessários para o treinamento do modelo.

3. **Execute o script de treinamento**:
   ```bash
   python -m train_model
   ```

   Isso gerará os arquivos `model.joblib` e `vectorizer.joblib` no diretório `fastapi-backend`, que são necessários para a execução do backend.
