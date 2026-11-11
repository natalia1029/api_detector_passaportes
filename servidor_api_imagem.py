import base64
import io
import re
import requests
import joblib
import pandas as pd
import pytesseract
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image, ImageOps

app = FastAPI()

# 1) Carrega o modelo treinado (Garante que "meu_modelo.joblib" está no GitHub)
modelo = joblib.load("modelo.joblib")

# Dicionário mapeando os rótulos do seu LabelEncoder no Colab
dicionario_classes = {
    0: "brasileiro",
    1: "estrangeiro",
    2: "invalido"
}

class Entrada(BaseModel):
    fonte: str

def carregar_imagem(fonte):
    fonte = fonte.strip()
    if fonte.startswith("http://") or fonte.startswith("https://"):
        resposta = requests.get(fonte, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resposta.raise_for_status()
        dados = resposta.content
    else:
        if fonte.startswith("data:"):
            fonte = fonte.split(",", 1)[1]
        dados = base64.b64decode(fonte)

    return Image.open(io.BytesIO(dados)).convert("RGB")

def corrigir_orientacao(imagem):
    """Gira a imagem para a posição correta antes da leitura, igual no Colab."""
    imagem = ImageOps.exif_transpose(imagem)
    try:
        dados_osd = pytesseract.image_to_osd(imagem, config="--psm 0")
        rotacao = int(dados_osd.split("Rotate:")[1].split("\n")[0].strip())
        if rotacao != 0:
            imagem = imagem.rotate(rotacao, expand=True)
    except Exception:
        # Se o Tesseract não conseguir detectar a orientação, mantém a imagem original
        pass
    return imagem

@app.post("/detectar-documento")
def detectar_documento(entrada: Entrada):
    # 1. Carregar a imagem
    try:
        imagem_pil = carregar_imagem(entrada.fonte)
    except Exception as erro:
        raise HTTPException(status_code=400, detail=f"Erro ao carregar a imagem: {erro}")

    # 2. Corrigir orientação
    imagem_corrigida = corrigir_orientacao(imagem_pil)

    # 3. Extrair texto (OCR) usando os mesmos idiomas do Colab
    texto_ocr = pytesseract.image_to_string(imagem_corrigida, lang="por+eng")
    texto_ocr = str(texto_ocr).strip()
    texto_ocr_vazio_corrigido = texto_ocr if texto_ocr else ""

    # 4. Calcular as Features exatas do Colab
    republica_brasil = int(bool(re.search(r"REPUBLICA|FEDERATIVA|BRASIL", texto_ocr_vazio_corrigido, re.IGNORECASE)))
    quantidade_texto = len(texto_ocr_vazio_corrigido)
    quantidade_mrz = texto_ocr_vazio_corrigido.count("<")
    presenca_mrz = int(quantidade_mrz > 10)
    presenca_passaporte = int(bool(re.search(r"\b(PASSAPORTE|PASSPORT)\b", texto_ocr_vazio_corrigido, re.IGNORECASE)))
    
    linhas = [linha for linha in texto_ocr_vazio_corrigido.splitlines() if linha.strip()]
    quantidade_linhas = len(linhas)
    quantidade_digitos = len(re.findall(r"\d", texto_ocr_vazio_corrigido))
    presenca_p_bra = int("P<BRA" in texto_ocr_vazio_corrigido.upper())

    # 5. Criar DataFrame numérico para o XGBoost
    dados_para_previsao = pd.DataFrame([{
        "republica_brasil": republica_brasil,
        "quantidade_texto": quantidade_texto,
        "presenca_mrz": presenca_mrz,
        "presenca_passaporte": presenca_passaporte,
        "quantidade_linhas": quantidade_linhas,
        "quantidade_digitos": quantidade_digitos,
        "quantidade_mrz": quantidade_mrz,
        "presenca_p_bra": presenca_p_bra
    }])

    # 6. Realizar a previsão
    previsao_numerica = modelo.predict(dados_para_previsao)[0]
    classe_final = dicionario_classes.get(int(previsao_numerica), "desconhecido")

    return {
        "status": "sucesso",
        "documento_detectado": classe_final,
        "texto_extraido": texto_ocr_vazio_corrigido
    }
