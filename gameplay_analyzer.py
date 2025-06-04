import streamlit as st
import cv2
import numpy as np
from mss import mss
import time
from datetime import datetime
import subprocess
import os
import requests
import base64
from PIL import Image
import io
import warnings
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# --- Variáveis Globais de Configuração (Padrões) ---
monitor_settings = {
    "top": 0,
    "left": 0,
    "width": 1920,
    "height": 1080
}
fps = 10.0

# As chaves de API devem ser carregadas de forma segura em ambiente de produção.
# Assumindo que OPENROUTER_API_KEY será carregada de alguma forma segura no ambiente real
OPENROUTER_API_KEY = "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" # A chave do seu exemplo
# GEMINI_API_KEY será carregada de st.secrets no main_app.py

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.2-11b-vision-instruct:free"

# Configure Gemini para a síntese de dicas
# A chave Gemini é carregada em main_app e passada implicitamente, ou diretamente configurada aqui se for usada apenas neste arquivo.
# Para manter a simplicidade e consistência com o exemplo, vamos configurar aqui também.
# É importante que a API key esteja disponível no ambiente onde este script é executado.
try:
    # Tenta carregar do ambiente ou de st.secrets se o script for executado via Streamlit
    if "GEMINI_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    elif "GEMINI_API_KEY" in st.secrets: # Só funcionará se for chamado dentro de um contexto Streamlit
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        # Fallback para a chave codificada se nenhuma outra for encontrada (para testes locais sem Streamlit)
        genai.configure(api_key='AIzaSyBco-5bq8-o_0adSTuktqf6c6-xui0hDcU') 
except Exception as e:
    print(f"Erro ao configurar a API Gemini em gameplay_analyzer: {e}")
    # Considerar levantar um erro ou parar a execução se a chave for crítica

def jogo_esta_rodando(jogo_alvo_exe: str) -> bool:
    """Check if the target game process is running."""
    if not jogo_alvo_exe or jogo_alvo_exe.lower() == "n/a":
        print("Aviso: Nenhum executável de jogo foi fornecido ou é 'N/A'. Prosseguindo com a captura de tela.")
        return True # Assumimos que o jogo está rodando se não houver EXE alvo específico
    try:
        result = subprocess.run(['tasklist', '/fi', f'IMAGENAME eq {jogo_alvo_exe}'], capture_output=True, text=True, check=False)
        return jogo_alvo_exe.lower() in result.stdout.lower()
    except Exception as e:
        print(f"Erro ao verificar processo do jogo: {e}")
        return False

def capturar_tela(sct, monitor):
    """Capture the screen with robust error handling."""
    try:
        screenshot = sct.grab(monitor)
        if not screenshot:
            print("⚠️ A captura retornou None")
            return None
        frame = np.array(screenshot)
        if frame.size == 0:
            print("⚠️ Frame vazio capturado")
            return None
        return frame
    except Exception as e:
        print(f"❌ Erro na captura: {str(e)}")
        return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError))
)
def make_openrouter_request(url, headers, payload, timeout):
    """Make a request to OpenRouter with retry logic."""
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if response.status_code != 200:
        print(f"OpenRouter HTTP Error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return response

def analyze_gameplay_with_llama(frames, gameplay_prompt: str, sample_size=5):
    """Analyze gameplay frames using Llama via OpenRouter."""
    tips = []
    if not gameplay_prompt:
        return ["Erro: Prompt de análise de gameplay não fornecido. A IA não pode analisar."]

    if not OPENROUTER_API_KEY or len(OPENROUTER_API_KEY) < 20:
        return ["Erro: Chave de API do OpenRouter inválida ou muito curta"]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    total_frames = len(frames)
    step = max(1, total_frames // sample_size)
    selected_frames = [frames[i * step] for i in range(min(sample_size, total_frames // step))]

    for i, frame in enumerate(selected_frames):
        try:
            img_pil = Image.fromarray(frame)
            buffered = io.BytesIO()
            img_pil.save(buffered, format="JPEG", quality=85)
            base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

            payload = {
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": gameplay_prompt},
                            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                        ]
                    }
                ],
                "max_tokens": 500
            }

            response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=30)
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0 and 'message' in data['choices'][0]:
                tip = data['choices'][0]['message']['content']
                tips.append(f"Frame {i+1}: {tip}")
            else:
                tips.append(f"Frame {i+1}: Resposta inesperada da API: {data}")

        except requests.exceptions.HTTPError as http_err:
            tips.append(f"Frame {i+1}: Erro HTTP - {str(http_err)} - Detalhes: {http_err.response.text if http_err.response else 'N/A'}")
        except requests.exceptions.ConnectionError as conn_err:
            tips.append(f"Frame {i+1}: Erro de conexão - Verifique sua internet ou DNS ({str(conn_err)})")
        except requests.exceptions.Timeout:
            tips.append(f"Frame {i+1}: Timeout na conexão com a API")
        except (KeyError, json.JSONDecodeError) as parse_err:
            tips.append(f"Frame {i+1}: Resposta inválida da API (JSON/KeyError): {parse_err}. Resposta bruta: {response.text[:200] if 'response' in locals() else 'N/A'}")
        except Exception as e:
            tips.append(f"Frame {i+1}: Erro geral - {str(e)}")

    return tips if tips else ["Nenhuma análise foi possível"]

def synthesize_tips_with_gemini(raw_tips, game_name: str):
    """Synthesize raw tips into a polished report using Gemini."""
    try:
        model_synth = genai.GenerativeModel('models/gemini-2.0-flash')
        
        prompt = (
            f"Você é um assistente de jogos especializado em {game_name}. Recebi as seguintes análises de gameplay de um modelo de visão: \n\n"
            f"{'\n'.join(raw_tips)}\n\n"
            "Sua tarefa é sintetizar essas dicas em um relatório claro, conciso e objetivo. Estruture o relatório em Markdown com: "
            "- Uma introdução resumindo o desempenho geral do jogador. "
            "- Uma lista de dicas específicas, organizadas por categoria (ex.: Posicionamento, Uso de Habilidades, Gestão de Recursos). "
            "- Uma conclusão com recomendações gerais para melhoria. "
            "Use linguagem direta e exemplos práticos. Máximo de 500 palavras."
        )
        response = model_synth.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao sintetizar dicas com Gemini: {str(e)}"

# --- Função Principal que será chamada pelo Streamlit ---
def run_gameplay_analysis(jogo_alvo: str, gameplay_prompt: str, game_name: str, duration_seconds=30):
    """
    Executa a captura de tela, análise e síntese de gameplay.
    Args:
        jogo_alvo (str): Nome do arquivo executável do jogo (ex: "game.exe").
        gameplay_prompt (str): O prompt gerado pela IA para análise de gameplay.
        game_name (str): O nome do jogo selecionado pelo usuário.
        duration_seconds (int): Duração da gravação em segundos.
    Returns:
        str: O relatório final de análise da gameplay.
    """
    st.write(f"Iniciando gravação de gameplay para {game_name} (executável: {jogo_alvo}). Por favor, jogue por {duration_seconds} segundos...")
    st.write("A gravação será encerrada automaticamente.")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # --- 1. Gravação dos Frames na Memória ---
    sct = mss()
    frames_brutos = []
    start_time = time.time()
    last_capture_time = time.time()
    frame_count = 0

    st.info("Verificando se o jogo está rodando...")
    if not jogo_esta_rodando(jogo_alvo):
        if jogo_alvo.lower() != "n/a": # Se um executável foi fornecido e não é "N/A"
            st.error(f"Erro: O executável '{jogo_alvo}' não foi detectado. Por favor, certifique-se de que o jogo está aberto e rodando.")
            return "Erro: O jogo não foi detectado rodando. Por favor, inicie o jogo antes de iniciar a análise."
        else:
            st.warning("Aviso: Nenhum executável específico foi fornecido, mas tentaremos capturar a tela. Certifique-se de que seu jogo está em tela cheia.")

    st.success("Jogo detectado (ou prosseguindo sem verificação de executável). Iniciando captura de tela...")
    progress_text = "Gravando gameplay... Aguarde."
    my_bar = st.progress(0, text=progress_text)

    try:
        while True:
            current_time = time.time()
            if current_time - start_time > duration_seconds:
                break

            if current_time - last_capture_time >= (1.0 / fps):
                frame = capturar_tela(sct, monitor_settings)
                if frame is not None:
                    frames_brutos.append(frame)
                    frame_count += 1
                last_capture_time = current_time
            
            # Atualiza a barra de progresso
            progress_percent = min(100, int(((current_time - start_time) / duration_seconds) * 100))
            my_bar.progress(progress_percent, text=f"Gravando gameplay... {progress_percent}% concluído.")
            time.sleep(0.01) # Pequeno atraso para evitar consumo excessivo de CPU

        my_bar.progress(100, text="Gravação concluída! Processando frames...")
        st.success(f"Capturados {len(frames_brutos)} frames em {duration_seconds} segundos.")

        if not frames_brutos:
            return "Erro: Não foi possível capturar frames. Certifique-se de que a tela principal está visível e não há sobreposições."

        # --- 2. Análise dos Frames com Llama ---
        st.info("Enviando frames para análise da IA (Llama)... Isso pode levar alguns minutos.")
        raw_tips = analyze_gameplay_with_llama(frames_brutos, gameplay_prompt)
        
        if not raw_tips or "Erro" in raw_tips[0]:
            return f"Erro na análise de gameplay com Llama: {raw_tips[0] if raw_tips else 'Nenhum feedback da IA.'}"

        st.success("Análise dos frames concluída. Sintetizando dicas...")
        
        # --- 3. Síntese das Dicas com Gemini ---
        final_report = synthesize_tips_with_gemini(raw_tips, game_name)

        return final_report

    except Exception as e:
        st.error(f"Ocorreu um erro durante a análise de gameplay: {e}")
        return f"Erro fatal durante a análise: {e}"
    finally:
        # Fechar o sct e liberar recursos
        sct.close()
