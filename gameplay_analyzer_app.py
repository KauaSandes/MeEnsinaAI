import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
import requests
import base64
import os
from datetime import datetime
import warnings
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import tempfile

# Suppress warnings
warnings.filterwarnings("ignore")

# --- Configurações da API ---
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_GROK3 = "x-ai/grok-2-vision-1212"

DB_PATH = Path(__file__).parent / "users.db"

# --- Banco de usuários ---
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao inicializar o banco de dados: {e}")
    finally:
        conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def register_user(email: str, password: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        st.error(f"Erro ao registrar usuário: {e}")
        return False
    finally:
        conn.close()

def authenticate_user(email: str, password: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        return row and row[0] == hash_password(password)
    except Exception as e:
        st.error(f"Erro ao autenticar usuário: {e}")
        return False
    finally:
        conn.close()

# --- Validação de vídeo ---
def validate_video_file(video_path):
    if not os.path.exists(video_path):
        return False, "Vídeo não encontrado"
    
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb > 50:
        return False, f"Arquivo muito grande ({file_size_mb:.2f} MB). Limite: 50MB"
    
    return True, "OK"

# --- Análise de vídeo ---
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def make_openrouter_request(url, headers, payload, timeout):
    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def analyze_gameplay_video(video_path, game_name="Valorant"):
    is_valid, validation_msg = validate_video_file(video_path)
    if not is_valid:
        return f"Erro na validação: {validation_msg}"

    if not OPENROUTER_API_KEY or len(OPENROUTER_API_KEY) < 20:
        return "Erro: Chave de API inválida"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()
        base64_video = base64.b64encode(video_data).decode('utf-8')

        prompt = f"""
        Você é um analista especialista em {game_name} e coach de e-sports. Analise este vídeo de gameplay focando:

        1. **Posicionamento de Mira:**
           - Altura da mira (cabeça dos oponentes)
           - Pré-posicionamento em ângulos
           - Fluidez do movimento da mira

        2. **Movimentação e Posicionamento:**
           - Uso de ângulos vantajosos
           - Movimentação durante combate
           - Uso eficaz de cobertura

        3. **Uso de Habilidades:**
           - Timing das habilidades
           - Posicionamento dos utilitários
           - Economia de recursos

        4. **Tomada de Decisão:**
           - Decisões táticas
           - Engajamentos
           - Consciência do mapa

        **Formato da resposta:**
        - Seja específico e construtivo
        - Organize por categorias
        - Forneça dicas acionáveis
        - Use exemplos práticos

        Analise o vídeo e forneça feedback detalhado para ajudar o jogador a melhorar.
        """

        payload = {
            "model": MODEL_GROK3,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "video_url", "video_url": f"data:video/mp4;base64,{base64_video}"}
                    ]
                }
            ],
            "max_tokens": 1500
        }

        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=60)
        response.raise_for_status()

        data = response.json()
        analysis = data['choices'][0]['message']['content']
        
        # Formatar o relatório
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report = f"""# Análise de Gameplay - {game_name}
        
**Data da análise:** {timestamp}

{analysis}

---
*Análise gerada automaticamente por IA especializada em {game_name}*
"""
        return report

    except requests.exceptions.HTTPError as e:
        return f"Erro HTTP: {str(e)}"
    except requests.exceptions.ConnectionError:
        return "Erro de conexão. Verifique sua internet."
    except requests.exceptions.Timeout:
        return "Timeout na conexão com a API"
    except Exception as e:
        return f"Erro geral: {str(e)}"

# --- Interface Streamlit ---
def main():
    st.set_page_config(
        page_title="Me Ensina A.I - Análise de Gameplay",
        page_icon="🎮",
        layout="wide"
    )

    init_db()

    # Estados de sessão
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""
    if 'analysis_report' not in st.session_state:
        st.session_state.analysis_report = ""

    if not st.session_state.logged_in:
        show_auth_screen()
    else:
        show_gameplay_analysis_screen()

def show_auth_screen():
    st.title("🎮 ME ENSINA A.I")
    st.markdown("""
    ### Análise Inteligente de Gameplay
    
    Transforme sua gameplay com análises detalhadas por IA! Nossa plataforma analisa seus vídeos de jogo e fornece:
    
    - 🎯 **Análise de Mira**: Posicionamento e técnica
    - 🏃 **Movimentação**: Posicionamento estratégico  
    - ⚡ **Habilidades**: Uso otimizado de utilitários
    - 🧠 **Decisões**: Melhor tomada de decisão tática
    
    Melhore seu desempenho e alcance novos patamares no seu jogo favorito!
    """)

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            login_btn = st.form_submit_button("Entrar", use_container_width=True)
            
            if login_btn:
                if authenticate_user(email, password):
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.rerun()
                else:
                    st.error("Email ou senha inválidos.")

    with col2:
        st.subheader("📝 Criar Conta")
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_password = st.text_input("Senha", type="password")
            pwd_confirm = st.text_input("Confirme a senha", type="password")
            signup_btn = st.form_submit_button("Cadastrar", use_container_width=True)
            
            if signup_btn:
                if not new_email or not new_password:
                    st.warning("Preencha todos os campos.")
                elif new_password != pwd_confirm:
                    st.warning("As senhas devem ser iguais.")
                else:
                    if register_user(new_email, new_password):
                        st.success("Conta criada! Faça login para continuar.")
                    else:
                        st.warning("Já existe uma conta com esse email.")

def show_gameplay_analysis_screen():
    st.title("🎮 Análise de Gameplay")
    st.write(f"👤 **Usuário:** {st.session_state.user_email}")
    
    # Sidebar com informações
    with st.sidebar:
        st.header("ℹ️ Informações")
        st.info("""
        **Formatos aceitos:** MP4
        **Tamanho máx:** 50MB
        **Duração recomendada:** 30s - 2min
        
        **Dicas para melhor análise:**
        - Use qualidade HD
        - Inclua momentos de combate
        - Evite menus/lobbies
        """)
        
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Upload e seleção de jogo
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📹 Upload do Vídeo")
        uploaded_file = st.file_uploader(
            "Escolha seu vídeo de gameplay",
            type=['mp4'],
            help="Selecione um arquivo MP4 com até 50MB"
        )
    
    with col2:
        st.subheader("🎯 Jogo")
        game_name = st.selectbox(
            "Selecione o jogo:",
            ["Valorant", "CS2/CS:GO", "Apex Legends", "Overwatch 2", "Rainbow Six Siege", "Outro"]
        )
        
        if game_name == "Outro":
            game_name = st.text_input("Digite o nome do jogo:")

    # Análise
    if uploaded_file and game_name:
        st.subheader("🔍 Análise")
        
        if st.button("🚀 Analisar Gameplay", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
            
            try:
                with st.spinner("🤖 Analisando seu vídeo... Isso pode levar alguns minutos."):
                    progress_bar = st.progress(0)
                    
                    # Simular progresso
                    import time
                    for i in range(100):
                        time.sleep(0.02)
                        progress_bar.progress(i + 1)
                    
                    analysis_result = analyze_gameplay_video(tmp_file_path, game_name)
                    st.session_state.analysis_report = analysis_result
                
                st.success("✅ Análise concluída!")
                
            except Exception as e:
                st.error(f"❌ Erro durante a análise: {str(e)}")
            finally:
                # Limpar arquivo temporário
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

    # Exibir resultados
    if st.session_state.analysis_report:
        st.subheader("📊 Relatório de Análise")
        
        # Botões de ação
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 Download Relatório"):
                st.download_button(
                    label="Baixar como Markdown",
                    data=st.session_state.analysis_report,
                    file_name=f"analise_gameplay_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
        with col2:
            if st.button("🔄 Nova Análise"):
                st.session_state.analysis_report = ""
                st.rerun()
        with col3:
            if st.button("📋 Copiar Texto"):
                st.code(st.session_state.analysis_report)
        
        # Exibir relatório
        st.markdown("---")
        st.markdown(st.session_state.analysis_report)

if __name__ == "__main__":
    main()