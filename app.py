import streamlit as st
import numpy as np
import io
import os
import tempfile
import flask
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

# Configuração da página Streamlit
st.set_page_config(
    page_title="Extrator de Texto de PDFs",
    page_icon="📄",
    layout="wide"
)

# Configuração do ambiente para usar PyTorch
os.environ["USE_TORCH"] = "1"

# Bibliotecas necessárias para OCR
try:
    from pdf2image import convert_from_bytes
    from doctr.models import ocr_predictor
except Exception as e:
    st.error(f"Erro ao carregar bibliotecas: {e}")
    st.stop()

# Verificação de poppler
try:
    from pdf2image.exceptions import PDFInfoNotInstalledError
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(b"%PDF-1.7\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj xref 0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF\n")
        f.flush()
        try:
            convert_from_bytes(open(f.name, 'rb').read(), first_page=1, last_page=1)
        except PDFInfoNotInstalledError:
            st.error("Poppler não está instalado. Adicione 'poppler-utils' ao seu arquivo packages.txt")
            st.stop()
        except Exception as e:
            if "DPI" not in str(e):
                st.warning(f"Aviso na verificação do poppler: {e}")
except Exception as e:
    st.warning(f"Não foi possível verificar o poppler: {e}")

# Função para carregar o modelo (com cache)
@st.cache_resource
def load_model():
    try:
        return ocr_predictor(pretrained=True)
    except Exception as e:
        st.error(f"Erro ao carregar o modelo: {e}")
        return None

# Função para converter PDF em imagens
def convert_pdf_to_images(pdf_file):
    try:
        return convert_from_bytes(pdf_file.getvalue(), dpi=200)
    except Exception as e:
        st.error(f"Erro ao converter PDF para imagens: {e}")
        return []

# Função de extração de texto
def extract_text_from_pdf(pdf_file):
    # Converter PDF para imagens
    images = convert_pdf_to_images(pdf_file)
    
    if not images:
        return "Não foi possível converter o PDF para imagens."
    
    # Carregar modelo
    model = load_model()
    if model is None:
        return "Não foi possível carregar o modelo OCR."
    
    # Processar cada página do PDF
    full_text = ""
    for page_num, img in enumerate(images):
        try:
            # Converter para numpy array
            img_np = np.array(img)
            
            # Executar OCR
            result = model([img_np])
            
            # Extrair texto
            page_text = ""
            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        line_text = ""
                        for word in line.words:
                            line_text += word.value + " "
                        page_text += line_text.strip() + "\n"
                    page_text += "\n"
            
            # Adicionar texto da página ao texto completo
            full_text += f"--- Página {page_num + 1} ---\n{page_text}\n\n"
        
        except Exception as e:
            full_text += f"--- Página {page_num + 1} --- Erro na extração de texto\n\n"
    
    return full_text

# Configuração da API Flask
app_flask = Flask(__name__)
CORS(app_flask)

@app_flask.route('/api/extract-text', methods=['POST'])
def extract_text_api():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    pdf_file = request.files['file']
    
    if pdf_file.filename == '':
        return jsonify({"error": "Arquivo inválido"}), 400
    
    try:
        full_text = extract_text_from_pdf(pdf_file)
        
        return jsonify({
            "text": full_text
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Interface Streamlit
st.title("Extrator de Texto de PDFs")
st.markdown("Esta aplicação extrai texto de PDFs usando docTR.")

# Upload de arquivo na interface Streamlit
uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("Extraindo texto..."):
        text = extract_text_from_pdf(uploaded_file)
        
        # Exibir texto completo extraído
        st.header("Texto Extraído")
        st.text_area("Conteúdo do PDF", text, height=400)

        # Botão para copiar texto
        st.download_button(
            label="Baixar texto extraído",
            data=text,
            file_name="texto_extraido.txt",
            mime="text/plain"
        )

# Função para iniciar o servidor Flask em uma thread separada
def run_flask():
    app_flask.run(port=8501, host='0.0.0.0')

# Iniciar o servidor Flask em uma thread separada
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Manter a aplicação Streamlit rodando
    st.write("Servidor API Flask iniciado na porta 8501")