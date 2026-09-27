FROM python:3.11-slim

WORKDIR /app

# Dipendenze di sistema per SQLCipher
RUN apt-get update && apt-get install -y \
    libsqlcipher-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codice
COPY . .

# Porta standard Fly.io
EXPOSE 8080

# Avvia FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
