#!/usr/bin/env bash
# Atualiza os pacotes do sistema
apt-get update
# Instala o motor do Tesseract e os idiomas (Português e Inglês)
apt-get install -y tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
# Instala as bibliotecas do Python
pip install -r requirements.txt
