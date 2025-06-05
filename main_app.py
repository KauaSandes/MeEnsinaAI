import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
import google.generativeai as genai
import os
import json
import toml
from datetime import datetime

# --- Configuração da API Gemini ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Chave de API GEMINI não encontrada. Verifique .streamlit/secrets.toml ou a variável de ambiente GEMINI_API_KEY.")
    st.stop()

# Inicializa o modelo da IA para o site (verificação de jogo, download, geração de prompt)
model = genai.GenerativeModel('gemini-1.5-pro-latest') # Modelo correto do Gemini

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

# --- Função de Verificação de Jogo com IA ---
def verify_game_with_ai(game_name: str) -> bool:
    try:
        prompt = f"O jogo '{game_name}' é um videogame conhecido e amplamente reconhecido? Responda apenas 'Sim' ou 'Não'."
        response = model.generate_content(prompt)
        if response and response.text:
            cleaned_response = response.text.strip().lower().replace('.', '')
            return "sim" in cleaned_response
        return False
    except Exception as e:
        st.error(f"Erro ao verificar o jogo com a IA: {e}")
        return False

# --- Obter Sugestão de Executável com IA (simplificado) ---
def get_game_exe_suggestion_with_ai(game_name: str):
    try:
        # Mapeamento direto para os executáveis mais comuns
        executaveis_padrao = {
            "Counter-Strike 2": "cs2.exe",
            "Street Fighter 6": "StreetFighter6.exe",
            "FIFA 23": "FIFA23.exe"
        }

        # Se o jogo está no mapeamento direto, retorna o executável padrão
        if game_name in executaveis_padrao:
            return executaveis_padrao[game_name]

        # Se não estiver no mapeamento, usa o Gemini para sugerir
        prompt = f"""Para o jogo '{game_name}', qual é o nome do arquivo executável mais comum?
        Considere as seguintes regras:
        1. Responda APENAS o nome do arquivo executável (ex: 'game.exe')
        2. Não inclua aspas, pontos ou explicações
        3. Se for um jogo de console ou não tiver executável, responda "N/A"
        4. Use o formato mais comum encontrado em instalações padrão
        5. Inclua a extensão .exe no final
        """
        
        response = model.generate_content(prompt)
        if response and response.text:
            cleaned_response = response.text.strip().replace('"', '').replace('.', '')
            if cleaned_response.lower() in ["n/a", "não disponível", "não aplicável"]:
                return "N/A"
            # Garante que a resposta termine com .exe
            if not cleaned_response.lower().endswith('.exe'):
                cleaned_response += '.exe'
            return cleaned_response
        return "N/A"
    except Exception as e:
        st.error(f"Erro ao obter sugestão de executável com a IA: {e}")
        return "N/A"

# --- Gerar Prompt de Análise de Gameplay com IA ---
def generate_gameplay_analysis_prompt(game_name: str) -> str:
    try:
        # Criar um prompt base mais específico para o Gemini
        base_prompt = f"""Você é um especialista em análise de gameplay de {game_name}. Crie um prompt detalhado e técnico para analisar um frame de gameplay deste jogo.

        O prompt deve:
        1. Definir seu papel como analista especializado em {game_name}
        2. Listar 4-5 aspectos técnicos específicos do jogo para analisar
        3. Para cada aspecto, incluir 3-4 critérios de avaliação específicos
        4. Solicitar dicas práticas e objetivas para melhorar cada aspecto identificado

        O prompt deve ser focado em aspectos que podem ser observados em um único frame de gameplay.
        Use linguagem técnica e específica do jogo.
        Não inclua aspas ou formatação extra no prompt gerado.
        Responda APENAS com o prompt, sem explicações adicionais."""

        # Usar o Gemini para gerar o prompt personalizado
        response = model.generate_content(base_prompt)
        
        if response and response.text:
            generated_prompt = response.text.strip()
            # Remover aspas se presentes
            if generated_prompt.startswith('"') and generated_prompt.endswith('"'):
                generated_prompt = generated_prompt[1:-1]
            # Verificar se o prompt gerado é válido
            if len(generated_prompt) > 50:  # Garantir que o prompt tenha um tamanho mínimo
                return generated_prompt
        
        # Fallback para prompts pré-definidos se o Gemini falhar
        if game_name == "Counter-Strike 2":
            return """Você é um especialista em Counter-Strike 2. Analise este frame de gameplay e forneça feedback técnico e específico sobre:
            1. Posicionamento e Movimento:
               - O jogador está em uma posição vantajosa?
               - O movimento está fluido e eficiente?
               - Há exposição desnecessária?

            2. Uso de Armas e Equipamentos:
               - A arma escolhida é apropriada para a situação?
               - O uso de granadas está eficiente?
               - Há economia adequada de munição?

            3. Tomada de Decisão:
               - As decisões táticas são apropriadas?
               - Há comunicação efetiva com a equipe?
               - O jogador está ajudando a equipe?

            4. Mecânicas Básicas:
               - A mira está precisa?
               - O controle de spray está adequado?
               - O jogador está usando o recoil corretamente?

            Forneça dicas práticas e objetivas para melhorar cada aspecto identificado."""

        elif game_name == "Street Fighter 6":
            return """Você é um especialista em Street Fighter 6. Analise este frame de gameplay e forneça feedback técnico e específico sobre:
            1. Combos e Sequências:
               - Os combos estão sendo executados corretamente?
               - Há oportunidades perdidas para combos?
               - A sequência de ataques está otimizada?

            2. Defesa e Bloqueio:
               - O jogador está bloqueando corretamente?
               - Há exposição desnecessária?
               - O uso de recursos defensivos está adequado?

            3. Uso de Recursos:
               - O Drive Rush está sendo usado eficientemente?
               - O Drive Parry está sendo aplicado no momento certo?
               - Os recursos especiais estão sendo gerenciados bem?

            4. Estratégia de Personagem:
               - O estilo de jogo combina com o personagem?
               - As técnicas específicas do personagem estão sendo usadas?
               - Há adaptação ao oponente?

            Forneça dicas práticas e objetivas para melhorar cada aspecto identificado."""

        elif game_name == "FIFA 23":
            return """Você é um especialista em FIFA 23. Analise este frame de gameplay e forneça feedback técnico e específico sobre:
            1. Controle de Bola:
               - O jogador está mantendo a posse de bola eficientemente?
               - Os passes estão precisos e bem direcionados?
               - O controle de espaço está adequado?

            2. Tática e Posicionamento:
               - A formação está sendo mantida?
               - Os jogadores estão bem posicionados?
               - Há pressão efetiva no ataque/defesa?

            3. Finalizações:
               - As finalizações estão sendo bem executadas?
               - Há oportunidades perdidas de gol?
               - O posicionamento para finalização está correto?

            4. Defesa:
               - A marcação está eficiente?
               - O posicionamento defensivo está correto?
               - A pressão está sendo aplicada adequadamente?

            Forneça dicas práticas e objetivas para melhorar cada aspecto identificado."""

        return ""

    except Exception as e:
        st.error(f"Erro ao gerar o prompt de análise de gameplay com a IA: {e}")
        return ""

# --- Importa a função de análise de gameplay ---
from gameplay_analyzer import run_gameplay_analysis

# --- Lógica de sessão e telas ---
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
        if 'exe_input_received' not in st.session_state:
            st.session_state.exe_input_received = False
        if 'game_exe_name' not in st.session_state:
            st.session_state.game_exe_name = ""
        if 'gameplay_analysis_prompt' not in st.session_state:
            st.session_state.gameplay_analysis_prompt = ""
        if 'analysis_report' not in st.session_state:
            st.session_state.analysis_report = ""
        if 'prompt_edited' not in st.session_state:
            st.session_state.prompt_edited = False
        if 'analysis_started' not in st.session_state:
            st.session_state.analysis_started = False
        if 'retry_count' not in st.session_state:
            st.session_state.retry_count = 0
            
        # Limpar o estado de login_success após o rerun
        if st.session_state.get("login_success"):
            st.session_state.pop("login_success")
            st.rerun()
            
        # Limpar o texto de introdução se não estiver na tela de login
        if st.session_state.logged_in:
            st.session_state.pop("intro_text_shown", None)

        # Navegação entre telas
        try:
            if not st.session_state.logged_in:
                show_auth_screen()
            elif not st.session_state.game_selected:
                show_game_selection()
            elif not st.session_state.prompt_edited:
                show_prompt_editing_screen()
            elif not st.session_state.exe_input_received:
                show_exe_input_screen()
            elif not st.session_state.analysis_started:
                show_start_analysis_screen()
            else:
                show_analysis_results_screen()
        except Exception as e:
            error_message = str(e)
            if "NotFoundError" in error_message or "removeChild" in error_message:
                # Implementar mecanismo de retry
                if st.session_state.retry_count < 3:
                    st.session_state.retry_count += 1
                    st.rerun()
                else:
                    st.session_state.retry_count = 0
                    st.warning("Por favor, recarregue a página.")
            else:
                st.warning("Ocorreu um erro inesperado. Por favor, tente recarregar a página.")
                print(f"Erro interno: {error_message}")

    except Exception as e:
        error_message = str(e)
        if "NotFoundError" in error_message or "removeChild" in error_message:
            # Implementar mecanismo de retry
            if st.session_state.retry_count < 3:
                st.session_state.retry_count += 1
                st.rerun()
            else:
                st.session_state.retry_count = 0
                st.warning("Por favor, recarregue a página.")
        else:
            st.warning("Ocorreu um erro inesperado. Por favor, tente recarregar a página.")
            print(f"Erro interno: {error_message}")

def show_auth_screen():
    st.title("CONHEÇA O ME ENSINA A.I")
    st.write("""
    Em meio ao crescimento acelerado do universo gamer, um site brasileiro vem se destacando ao unir inteligência artificial e paixão por jogos. A plataforma foi criada com um propósito claro: ajudar jogadores de todos os níveis a melhorarem suas habilidades por meio de análises inteligentes e treinos personalizados com apoio de IA.
    Com ferramentas que analisam o desempenho em tempo real, o site oferece feedbacks estratégicos, dicas de posicionamento, tempo de reação, mira e tomada de decisão. Tudo isso baseado em dados precisos, o que torna o treinamento muito mais eficiente do que os métodos tradicionais.
    Essa inovação não só eleva o nível dos jogadores casuais, mas também abre portas para que mais talentos brasileiros cheguem ao cenário competitivo. O resultado é uma nova geração de gamers cada vez mais preparada e profissionalizada, contribuindo diretamente para o crescimento do público e da relevância dos eSports no Brasil.
    Combinando tecnologia de ponta com acessibilidade, essa plataforma está transformando o jeito de jogar — e o futuro dos jogos no país.
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
    try:
        st.title("Selecione o Jogo")
        st.write(f"Usuário: **{st.session_state.user_email}** \n")
        st.write("Escolha um dos jogos disponíveis para análise:")

        # Lista pré-definida de jogos
        jogos_disponiveis = {
            "CS2": "Counter-Strike 2",
            "SF6": "Street Fighter 6",
            "FIFA23": "FIFA 23"
        }

        # Criar colunas para os jogos
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("CS2", use_container_width=True):
                st.session_state.game_selected = True
                st.session_state.current_game = jogos_disponiveis["CS2"]
                st.session_state.prompt_edited = False
                # Gerar o prompt inicial para o jogo selecionado
                with st.spinner("Gerando prompt de análise para CS2..."):
                    prompt = generate_gameplay_analysis_prompt(jogos_disponiveis["CS2"])
                    if prompt:
                        st.session_state.gameplay_analysis_prompt = prompt
                    else:
                        st.error("Não foi possível gerar o prompt. Usando prompt padrão.")
                        st.session_state.gameplay_analysis_prompt = """Você é um especialista em Counter-Strike 2. Analise este frame de gameplay e forneça feedback técnico e específico sobre:
                        1. Posicionamento e Movimento:
                           - O jogador está em uma posição vantajosa?
                           - O movimento está fluido e eficiente?
                           - Há exposição desnecessária?

                        2. Uso de Armas e Equipamentos:
                           - A arma escolhida é apropriada para a situação?
                           - O uso de granadas está eficiente?
                           - Há economia adequada de munição?

                        3. Tomada de Decisão:
                           - As decisões táticas são apropriadas?
                           - Há comunicação efetiva com a equipe?
                           - O jogador está ajudando a equipe?

                        4. Mecânicas Básicas:
                           - A mira está precisa?
                           - O controle de spray está adequado?
                           - O jogador está usando o recoil corretamente?

                        Forneça dicas práticas e objetivas para melhorar cada aspecto identificado."""
                st.rerun()

        with col2:
            if st.button("Street Fighter 6", use_container_width=True):
                st.session_state.game_selected = True
                st.session_state.current_game = jogos_disponiveis["SF6"]
                st.session_state.prompt_edited = False
                # Gerar o prompt inicial para o jogo selecionado
                with st.spinner("Gerando prompt de análise para Street Fighter 6..."):
                    prompt = generate_gameplay_analysis_prompt(jogos_disponiveis["SF6"])
                    if prompt:
                        st.session_state.gameplay_analysis_prompt = prompt
                    else:
                        st.error("Não foi possível gerar o prompt. Usando prompt padrão.")
                        st.session_state.gameplay_analysis_prompt = """Você é um especialista em Street Fighter 6. Analise este frame de gameplay e forneça feedback técnico e específico sobre:
                        1. Combos e Sequências:
                           - Os combos estão sendo executados corretamente?
                           - Há oportunidades perdidas para combos?
                           - A sequência de ataques está otimizada?

                        2. Defesa e Bloqueio:
                           - O jogador está bloqueando corretamente?
                           - Há exposição desnecessária?
                           - O uso de recursos defensivos está adequado?

                        3. Uso de Recursos:
                           - O Drive Rush está sendo usado eficientemente?
                           - O Drive Parry está sendo aplicado no momento certo?
                           - Os recursos especiais estão sendo gerenciados bem?

                        4. Estratégia de Personagem:
                           - O estilo de jogo combina com o personagem?
                           - As técnicas específicas do personagem estão sendo usadas?
                           - Há adaptação ao oponente?

                        Forneça dicas práticas e objetivas para melhorar cada aspecto identificado."""
                st.rerun()

        with col3:
            if st.button("FIFA 23", use_container_width=True):
                st.session_state.game_selected = True
                st.session_state.current_game = jogos_disponiveis["FIFA23"]
                st.session_state.prompt_edited = False
                # Gerar o prompt inicial para o jogo selecionado
                with st.spinner("Gerando prompt de análise para FIFA 23..."):
                    prompt = generate_gameplay_analysis_prompt(jogos_disponiveis["FIFA23"])
                    if prompt:
                        st.session_state.gameplay_analysis_prompt = prompt
                    else:
                        st.error("Não foi possível gerar o prompt. Usando prompt padrão.")
                        st.session_state.gameplay_analysis_prompt = """Você é um especialista em FIFA 23. Analise este frame de gameplay e forneça feedback técnico e específico sobre:
                        1. Controle de Bola:
                           - O jogador está mantendo a posse de bola eficientemente?
                           - Os passes estão precisos e bem direcionados?
                           - O controle de espaço está adequado?

                        2. Tática e Posicionamento:
                           - A formação está sendo mantida?
                           - Os jogadores estão bem posicionados?
                           - Há pressão efetiva no ataque/defesa?

                        3. Finalizações:
                           - As finalizações estão sendo bem executadas?
                           - Há oportunidades perdidas de gol?
                           - O posicionamento para finalização está correto?

                        4. Defesa:
                           - A marcação está eficiente?
                           - O posicionamento defensivo está correto?
                           - A pressão está sendo aplicada adequadamente?

                        Forneça dicas práticas e objetivas para melhorar cada aspecto identificado."""
                st.rerun()

        # Adicionar informações sobre os jogos
        st.markdown("---")
        st.subheader("Sobre os Jogos Disponíveis")
        
        with st.expander("CS2 - Counter-Strike 2"):
            st.write("""
            Counter-Strike 2 é um jogo de tiro em primeira pessoa tático multiplayer. 
            A análise focará em:
            - Posicionamento e movimento
            - Precisão de mira
            - Uso de granadas
            - Comunicação em equipe
            - Economia e compra de armas
            """)

        with st.expander("Street Fighter 6"):
            st.write("""
            Street Fighter 6 é um jogo de luta competitivo. 
            A análise focará em:
            - Combos e sequências
            - Defesa e bloqueio
            - Uso de recursos especiais
            - Timing e punição
            - Estratégia de personagem
            """)

        with st.expander("FIFA 23"):
            st.write("""
            FIFA 23 é um simulador de futebol. 
            A análise focará em:
            - Controle de bola
            - Posicionamento tático
            - Finalizações
            - Defesa e marcação
            - Estratégia de equipe
            """)

    except Exception as e:
        st.error(f"Erro ao processar a seleção do jogo: {e}. Tente novamente.")

# --- Nova tela para solicitar o nome do executável ---
def show_exe_input_screen():
    st.title("Informe o Executável do Jogo")
    st.write(f"Você selecionou o jogo: **{st.session_state.current_game}**.")
    
    # Container para a sugestão do executável
    with st.container():
        st.subheader("Sugestão de Executável")
        st.write("A IA sugeriu o seguinte executável para seu jogo:")
        
    if 'suggested_exe_from_ai' not in st.session_state:
        with st.spinner(f"Consultando a IA para sugerir o executável de '{st.session_state.current_game}'..."):
            suggested_exe = get_game_exe_suggestion_with_ai(st.session_state.current_game)
            st.session_state.suggested_exe_from_ai = suggested_exe
    else:
        suggested_exe = st.session_state.suggested_exe_from_ai

    if suggested_exe and suggested_exe != "N/A":
        st.info(f"Executável sugerido: `{suggested_exe}`")
        st.write("Você pode usar esta sugestão ou informar um executável diferente abaixo.")
    else:
        st.warning("Não foi possível obter uma sugestão automática. Por favor, insira o nome do executável manualmente.")
        
    st.markdown("---")
    
    # Container para entrada do executável
    with st.container():
        st.subheader("Nome do Executável")
        st.write("Digite o nome do arquivo executável do jogo (ex: `game.exe`):")

    game_exe_name = st.text_input(
        "Nome do executável",
        value=suggested_exe if suggested_exe != "N/A" else "",
        key="exe_input",
        help="O nome do arquivo .exe que inicia o jogo"
    )

    if st.button("Confirmar Executável", type="primary"):
        if game_exe_name.strip() and game_exe_name.lower() != "n/a":
            st.session_state.game_exe_name = game_exe_name.strip()
            st.session_state.exe_input_received = True
            st.session_state.analysis_started = False
            st.rerun()
        else:
            st.warning("Por favor, digite um nome de executável válido.")

    # Botão para voltar
    if st.button("Voltar para seleção de jogo"):
        st.session_state.game_selected = False
        st.session_state.exe_input_received = False
        st.session_state.current_game = ""
        st.session_state.suggested_exe_from_ai = ""
        st.session_state.gameplay_analysis_prompt = ""  # Limpa o prompt ao voltar
        st.rerun()


# --- Nova tela para iniciar a análise ---
def show_start_analysis_screen():
    st.title("Análise de Gameplay")
    st.markdown("---")
    
    st.subheader(f"Jogo selecionado: {st.session_state.current_game}")
    st.write(f"Executável: {st.session_state.game_exe_name}")
    
    st.info("""
    Instruções:
    1. Abra o jogo em tela cheia
    2. Certifique-se de que a janela do jogo está visível
    3. Clique no botão abaixo para iniciar a gravação
    """)
    
    # Expansor para visualização do prompt
    with st.expander("Ver prompt de análise (Avançado)"):
        st.code(st.session_state.gameplay_analysis_prompt)
    
    # Inicializa o estado de gravação se não existir
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.is_recording:
            if st.button("Começar Gravação", type="primary"):
                if not st.session_state.game_exe_name:
                    st.error("Nome do executável não encontrado. Por favor, selecione outro jogo.")
                    return
                    
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
                    st.session_state.game_exe_name,
                    st.session_state.gameplay_analysis_prompt,
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


# --- Nova tela para exibir os resultados da análise ---
def show_analysis_results_screen():
    st.title("Relatório de Análise de Gameplay")
    st.markdown("---")
    
    st.subheader(f"Jogo: {st.session_state.current_game}")
    st.write(f"Executável analisado: {st.session_state.game_exe_name}")
    
    if st.session_state.analysis_report:
        # Verifica se o relatório é um dicionário com a chave 'report'
        if isinstance(st.session_state.analysis_report, dict) and 'report' in st.session_state.analysis_report:
            st.markdown(st.session_state.analysis_report['report'])
            report_text = st.session_state.analysis_report['report']
        else:
            st.markdown(st.session_state.analysis_report)
            report_text = st.session_state.analysis_report
            
        # Adiciona botão para baixar o relatório
        st.download_button(
            label="Baixar Relatório",
            data=report_text,
            file_name=f"analise_{st.session_state.current_game.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    else:
        st.warning("Nenhum relatório de análise disponível. Algo pode ter dado errado durante a gravação ou processamento.")
        st.info("Verifique os logs no terminal para mais detalhes.")
        
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Fazer nova análise para este jogo"):
            st.session_state.analysis_started = False
            st.session_state.analysis_report = ""
            st.rerun()
    
    with col2:
        if st.button("Escolher outro jogo"):
            st.session_state.clear()
            st.rerun()

def show_prompt_editing_screen():
    st.title("Edição do Prompt de Análise")
    st.write(f"Jogo selecionado: **{st.session_state.current_game}**")
    
    st.subheader("Prompt Gerado pela IA")
    st.write("""
    A IA gerou um prompt personalizado para analisar sua gameplay. 
    Você pode revisar e editar este prompt antes de prosseguir.
    """)
    
    # Verificar se o prompt existe e gerar um novo se necessário
    if not st.session_state.gameplay_analysis_prompt:
        with st.spinner(f"Gerando prompt para {st.session_state.current_game}..."):
            prompt = generate_gameplay_analysis_prompt(st.session_state.current_game)
            if prompt:
                st.session_state.gameplay_analysis_prompt = prompt
            else:
                st.error("Não foi possível gerar o prompt. Por favor, tente novamente.")
                if st.button("Tentar Gerar Prompt Novamente"):
                    st.rerun()
                return
    
    # Exibir o prompt atual
    edited_prompt = st.text_area(
        "Edite o prompt de análise (opcional)",
        value=st.session_state.gameplay_analysis_prompt,
        height=300,
        help="Modifique o prompt para focar em aspectos específicos do seu gameplay"
    )
    
    if edited_prompt != st.session_state.gameplay_analysis_prompt:
        st.session_state.gameplay_analysis_prompt = edited_prompt
        st.success("Prompt atualizado com sucesso!")

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Confirmar e Continuar", type="primary"):
            if st.session_state.gameplay_analysis_prompt:
                st.session_state.prompt_edited = True
                st.rerun()
            else:
                st.error("O prompt não pode estar vazio. Por favor, edite ou gere um novo prompt.")
    
    with col2:
        if st.button("Voltar para Seleção de Jogo"):
            st.session_state.game_selected = False
            st.session_state.current_game = ""
            st.session_state.gameplay_analysis_prompt = ""
            st.session_state.prompt_edited = False
            st.rerun()

if __name__ == "__main__":
    main()
