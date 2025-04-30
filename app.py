import streamlit as st

# Configuração da página deve ser o primeiro comando Streamlit
st.set_page_config(
    page_title="Extrator de Texto de PDFs",
    page_icon="📄",
    layout="wide"
)

import numpy as np
import io
import os
import tempfile

# Configuração do ambiente para usar PyTorch
os.environ["USE_TORCH"] = "1"

# Título e descrição
st.title("Extrator de Texto de PDFs")
st.markdown("Esta aplicação extrai texto de PDFs usando docTR.")

# Tentativa de carregar bibliotecas necessárias
try:
    from pdf2image import convert_from_bytes
    from doctr.models import ocr_predictor
except Exception as e:
    st.error(f"Erro ao carregar bibliotecas: {e}")
    st.info("Certifique-se de instalar pdf2image: `pip install pdf2image`")
    st.stop()

# Verificar se o poppler está instalado
try:
    from pdf2image.exceptions import PDFInfoNotInstalledError
    # Tentativa básica de verificar o poppler
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(b"%PDF-1.7\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj xref 0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF\n")
        f.flush()
        try:
            convert_from_bytes(open(f.name, 'rb').read(), first_page=1, last_page=1)
        except PDFInfoNotInstalledError:
            st.error("Poppler não está instalado. Adicione 'poppler-utils' ao seu arquivo packages.txt")
            st.stop()
        except Exception as e:
            if "DPI" in str(e):  # Erro relacionado a DPI é aceitável para o teste
                pass
            else:
                st.warning(f"Aviso na verificação do poppler: {e}")
except Exception as e:
    st.warning(f"Não foi possível verificar o poppler: {e}")

# Função para carregar o modelo
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
        st.error("Detalhes: ", str(e))
        return []

# Upload de arquivo
st.header("Extração de Texto de PDF")
uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=["pdf"])

# Variável para armazenar todo o texto extraído
full_text = ""

if uploaded_file is not None:
    # Converter PDF para imagens
    with st.spinner("Convertendo PDF para imagens..."):
        images = convert_pdf_to_images(uploaded_file)
        
        if not images:
            st.warning("Não foi possível converter o PDF para imagens.")
            st.stop()
        else:
            st.success(f"PDF convertido em {len(images)} imagens.")
    
    # Carregar o modelo
    with st.spinner("Carregando modelo OCR..."):
        model = load_model()
        if model is None:
            st.error("Não foi possível carregar o modelo OCR.")
            st.stop()
    
    # Processar cada página do PDF
    for page_num, img in enumerate(images):
        # Processar OCR
        with st.spinner(f"Processando OCR na página {page_num + 1}..."):
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
                # Tratamento de erro para cada página
                st.error(f"Erro ao processar OCR na página {page_num + 1}: {e}")
                full_text += f"--- Página {page_num + 1} --- Erro na extração de texto\n\n"
        
    # Exibir texto completo extraído
    st.header("Texto Extraído")
    st.text_area("Conteúdo do PDF", full_text, height=400)

    # Botão para copiar texto
    st.download_button(
        label="Baixar texto extraído",
        data=full_text,
        file_name="texto_extraido.txt",
        mime="text/plain"
    )