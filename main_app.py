import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from gameplay_analyzer import run_gameplay_analysis

# Configurações de banco de dados
DB_PATH = Path(__file__).parent / "users.db"

# Mapeamento de jogos para executáveis padrão
GAME_EXECUTABLES = {
    "Counter-Strike 2": "cs2.exe",
    "Street Fighter 5": "StreetFighter5.exe"
}

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

def show_auth_screen():
    st.title("CONHEÇA O ME ENSINA A.I")
    st.write("""
    Em meio ao crescimento acelerado do universo gamer, um site brasileiro vem se destacando ao unir inteligência artificial e paixão por jogos. A plataforma foi criada com um propósito claro: ajudar jogadores de todos os níveis a melhorarem suas habilidades por meio de análises inteligentes e treinos personalizados com apoio de IA.
    Com ferramentas que analisam o desempenho em tempo real, o site oferece feedbacks estratégicos, dicas de posicionamento, tempo de reação, mira e tomada de decisão. Tudo isso baseado em dados precisos, o que torna o treinamento muito mais eficiente do que os métodos tradicionais.
    """)

    tab1, tab2 = st.tabs(["Login", "Criar Conta"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            login_btn = st.form_submit_button("Entrar")
            if login_btn:
                try:
                    if authenticate_user(email, password):
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.login_success = True
                    else:
                        st.warning("Email ou senha inválidos.")
                except Exception as e:
                    st.error(f"Erro ao tentar fazer login: {e}. Tente novamente mais tarde.")

    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("Email de cadastro", key="signup_email")
            new_password = st.text_input("Senha", type="password", key="signup_pwd")
            pwd_confirm = st.text_input("Confirme a senha", type="password", key="signup_confirm")
            signup_btn = st.form_submit_button("Cadastrar")
            if signup_btn:
                try:
                    if not new_email or not new_password:
                        st.warning("Preencha todos os campos.")
                    elif new_password != pwd_confirm:
                        st.warning("As senhas devem ser iguais.")
                    else:
                        success = register_user(new_email, new_password)
                        if success:
                            st.success("Conta criada! Faça login para continuar.")
                        else:
                            st.warning("Já existe uma conta com esse email.")
                except Exception as e:
                    st.error(f"Erro ao tentar criar conta: {e}. Tente novamente mais tarde.")

def show_game_selection():
    st.title("Selecione o Jogo")
    st.write(f"Usuário: **{st.session_state.user_email}** \n")
    st.write("Escolha um dos jogos disponíveis para análise:")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Counter-Strike 2", use_container_width=True):
            st.session_state.game_selected = True
            st.session_state.current_game = "Counter-Strike 2"
            st.session_state.game_exe = GAME_EXECUTABLES["Counter-Strike 2"]
            st.session_state.analysis_started = False
            st.rerun()

    with col2:
        if st.button("Street Fighter 5", use_container_width=True):
            st.session_state.game_selected = True
            st.session_state.current_game = "Street Fighter 5"
            st.session_state.game_exe = GAME_EXECUTABLES["Street Fighter 5"]
            st.session_state.analysis_started = False
            st.rerun()

    st.markdown("---")
    st.subheader("Sobre os Jogos Disponíveis")
    
    with st.expander("Counter-Strike 2"):
        st.write("""
        Counter-Strike 2 é um jogo de tiro em primeira pessoa tático multiplayer. 
        A análise focará em:
        - Posicionamento e movimento
        - Precisão de mira
        - Uso de granadas
        - Comunicação em equipe
        - Economia e compra de armas
        """)

    with st.expander("Street Fighter 5"):
        st.write("""
        Street Fighter 5 é um jogo de luta competitivo. 
        A análise focará em:
        - Combos e sequências
        - Defesa e bloqueio
        - Uso de recursos especiais
        - Timing e punição
        - Estratégia de personagem
        """)

def show_analysis_screen():
    st.title("Análise de Gameplay")
    st.markdown("---")
    
    st.subheader(f"Jogo selecionado: {st.session_state.current_game}")
    st.write(f"Executável: {st.session_state.game_exe}")
    
    st.info("""
    Instruções:
    1. Abra o jogo em tela cheia
    2. Certifique-se de que a janela do jogo está visível
    3. Clique no botão abaixo para iniciar a gravação
    """)
    
    # Inicializa o estado de gravação se não existir
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.is_recording:
            if st.button("Começar Gravação", type="primary"):
                st.session_state.is_recording = True
                st.rerun()
    
    with col2:
        if st.session_state.is_recording:
            if st.button("Interromper Gravação", type="secondary"):
                st.session_state.is_recording = False
                st.rerun()
    
    if st.session_state.is_recording:
        with st.spinner("Gravando gameplay..."):
            try:
                result = run_gameplay_analysis(
                    st.session_state.game_exe,
                    st.session_state.current_game
                )
                
                if result.get('success'):
                    st.session_state.analysis_report = result
                    st.session_state.analysis_started = True
                    st.session_state.is_recording = False
                    st.rerun()
                else:
                    st.error(f"Erro na análise: {result.get('message', 'Erro desconhecido')}")
                    st.session_state.is_recording = False
                    if st.button("Tentar novamente"):
                        st.rerun()
                    
            except Exception as e:
                st.error(f"Erro ao executar análise: {str(e)}")
                st.session_state.is_recording = False
                if st.button("Tentar novamente"):
                    st.rerun()

def show_results_screen():
    st.title("Relatório de Análise de Gameplay")
    st.markdown("---")
    
    st.subheader(f"Jogo: {st.session_state.current_game}")
    
    if st.session_state.analysis_report:
        if isinstance(st.session_state.analysis_report, dict) and 'report' in st.session_state.analysis_report:
            st.markdown(st.session_state.analysis_report['report'])
            report_text = st.session_state.analysis_report['report']
        else:
            st.markdown(st.session_state.analysis_report)
            report_text = st.session_state.analysis_report
            
        st.download_button(
            label="Baixar Relatório",
            data=report_text,
            file_name=f"analise_{st.session_state.current_game.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    else:
        st.warning("Nenhum relatório de análise disponível.")
        
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Fazer nova análise para este jogo"):
            st.session_state.analysis_started = False
            st.session_state.analysis_report = ""
            st.rerun()
    
    with col2:
        if st.button("Escolher outro jogo"):
            st.session_state.game_selected = False
            st.session_state.current_game = ""
            st.session_state.game_exe = ""
            st.session_state.analysis_started = False
            st.session_state.analysis_report = ""
            st.rerun()

def main():
    try:
        init_db()

        # Inicialização dos estados da sessão
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False
        if 'user_email' not in st.session_state:
            st.session_state.user_email = ""
        if 'game_selected' not in st.session_state:
            st.session_state.game_selected = False
        if 'current_game' not in st.session_state:
            st.session_state.current_game = ""
        if 'game_exe' not in st.session_state:
            st.session_state.game_exe = ""
        if 'analysis_started' not in st.session_state:
            st.session_state.analysis_started = False
        if 'analysis_report' not in st.session_state:
            st.session_state.analysis_report = ""
            
        # Limpar o estado de login_success após o rerun
        if st.session_state.get("login_success"):
            st.session_state.pop("login_success")
            st.rerun()

        # Navegação entre telas
        if not st.session_state.logged_in:
            show_auth_screen()
        elif not st.session_state.game_selected:
            show_game_selection()
        elif not st.session_state.analysis_started:
            show_analysis_screen()
        else:
            show_results_screen()

    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        if st.button("Reiniciar aplicação"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
