FROM python:3.11-slim

# install build deps (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy your code into the container
COPY . /app

# install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# download NLTK data at build time
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('rslp')"

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]