# 1. Puxa uma máquina Linux padrão com Python já instalado
FROM python:3.10-slim

# 2. Instala o Tesseract e os idiomas (como administrador)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# 3. Define a pasta principal
WORKDIR /app

# 4. Copia os seus arquivos (requirements, servidor.py, joblib, etc) para a máquina
COPY . /app

# 5. Instala as bibliotecas do Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Comando automático de inicialização (substitui o Start Command)
CMD ["uvicorn", "servidor_api_imagem:app", "--host", "0.0.0.0", "--port", "10000"]
