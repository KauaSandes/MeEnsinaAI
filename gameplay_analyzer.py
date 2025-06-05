import requests
import base64
import os
from datetime import datetime
import warnings
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import win32gui
import win32con
import pygetwindow as gw
import time
import mss
import streamlit as st

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Configurações globais
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
temp_video = f"temp_recording_{timestamp}.mp4"
synthesis_file = f"SINTESE_{timestamp}.md"

# Configurações das APIs
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_VISION = "opengvlab/internvl3-14b:free"
MODEL_SYNTHESIS = "anthropic/claude-opus-4"

def record_game_window(game_name, duration=60):
    """Grava a tela do jogo por um período específico"""
    try:
        # Tenta encontrar a janela do jogo
        try:
            game_window = gw.getWindowsWithTitle(game_name)[0]
            if not game_window:
                return False, f"Janela do jogo '{game_name}' não encontrada", 0
        except:
            print(f"Não foi possível encontrar a janela do jogo '{game_name}'. Gravando tela inteira...")
            screen = gw.getActiveWindow()
            if screen:
                game_window = screen
            else:
                return False, "Não foi possível iniciar a gravação", 0

        # Configurações de gravação
        fps = 30.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        # Obtém as dimensões da janela
        left, top = game_window.left, game_window.top
        width, height = game_window.width, game_window.height
        
        # Inicializa o gravador
        out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
        
        # Inicializa o capturador de tela
        with mss.mss() as sct:
            # Define a região de captura
            monitor = {"top": top, "left": left, "width": width, "height": height}
            
            print(f"Iniciando gravação por {duration} segundos...")
            start_time = time.time()
            actual_duration = 0
            
            while (time.time() - start_time) < duration:
                # Verifica se a gravação foi interrompida
                if hasattr(st.session_state, 'is_recording') and not st.session_state.is_recording:
                    print("\nGravação interrompida pelo usuário!")
                    actual_duration = time.time() - start_time
                    break
                
                # Captura a tela usando mss
                screenshot = np.array(sct.grab(monitor))
                
                # Converte BGRA para BGR
                frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                
                # Grava o frame
                out.write(frame)
                
                # Mostra tempo restante
                remaining = int(duration - (time.time() - start_time))
                print(f"\rTempo restante: {remaining} segundos...", end="")
                
                # Pequeno delay para reduzir uso de CPU
                time.sleep(1/fps)
            
            # Se não foi interrompido, usa a duração completa
            if actual_duration == 0:
                actual_duration = time.time() - start_time
        
        # Libera recursos
        out.release()
        print(f"\nGravação concluída! Duração real: {actual_duration:.1f} segundos")
        return True, "Gravação concluída com sucesso", actual_duration
        
    except Exception as e:
        error_msg = f"Erro durante a gravação: {str(e)}"
        print(f"\n{error_msg}")
        return False, error_msg, 0

def validate_video_file(video_path):
    """Validação do vídeo"""
    if not os.path.exists(video_path):
        print(f"Vídeo não encontrado: {video_path}")
        return False
    if not video_path.lower().endswith('.mp4'):
        print(f"Formato inválido: O arquivo deve ser .mp4")
        return False
    return True

def extract_key_frames(video_path, num_frames=15):
    """Extrai frames-chave do vídeo para análise detalhada"""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    duration = total_frames / fps
    
    intervals = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = []
    timestamps = []
    
    for frame_num in intervals:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            base64_frame = base64.b64encode(buffer).decode('utf-8')
            frames.append(base64_frame)
            timestamps.append(frame_num / fps)
            
    cap.release()
    return frames, timestamps

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def make_openrouter_request(url, headers, payload, timeout):
    """Request no OpenRouter"""
    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def analyze_frame(frame_base64, frame_number, total_frames, timestamp, custom_prompt):
    """Análise aprofundada de cada frame usando o prompt personalizado"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Gameplay Analysis",
        "OpenAI-Organization": "openrouter"
    }

    # Usa o prompt personalizado fornecido pelo usuário
    prompt = f"""
    {custom_prompt}
    
    Frame {frame_number}/{total_frames} (timestamp: {timestamp:.1f}s)
    """

    payload = {
        "model": MODEL_VISION,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{frame_base64}"
                        }
                    }
                ]
            }
        ]
    }

    try:
        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"Erro na API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro na análise do frame: {str(e)}")
        return None

def generate_final_report(analyses):
    """Gera um relatório consolidado com dicas baseadas na análise de todos os quadros"""
    if not analyses:
        return "Nenhuma análise disponível."
    
    # Combina todas as análises em um único texto
    combined_analysis = "\n".join([analysis for analysis in analyses if analysis])
    
    # Gera um prompt para o modelo criar um relatório consolidado
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Gameplay Analysis Report",
        "OpenAI-Organization": "openrouter"
    }

    prompt = f"""
    Com base nas seguintes análises de gameplay, crie um relatório consolidado com dicas e recomendações:

    {combined_analysis}

    Por favor, organize o relatório da seguinte forma:

    # Relatório de Análise de Gameplay

    ## Pontos Fortes
    - Liste os principais pontos fortes observados durante o gameplay

    ## Áreas de Melhoria
    - Liste as principais áreas que precisam de atenção

    ## Dicas e Recomendações
    - Forneça dicas práticas e específicas para melhorar o gameplay
    - Inclua sugestões de treinamento e prática

    ## Observações Gerais
    - Adicione qualquer observação relevante que possa ajudar no desenvolvimento
    """

    payload = {
        "model": MODEL_SYNTHESIS,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"Erro na API: {response.status_code}")
            return "Erro ao gerar relatório consolidado."
    except Exception as e:
        print(f"Erro na geração do relatório: {str(e)}")
        return "Erro ao gerar relatório consolidado."

def generate_synthesis(analysis_content):
    """Gera uma síntese das análises usando o modelo de síntese"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Gameplay Analysis Synthesis",
        "OpenAI-Organization": "openrouter"
    }

    prompt = f"""
    Analise as seguintes observações de gameplay e crie uma síntese detalhada e estruturada:

    {analysis_content}

    Forneça:
    1. Pontos fortes identificados
    2. Áreas que precisam de melhoria
    3. Recomendações específicas para cada área
    4. Sugestões de treinamento prático
    """

    payload = {
        "model": MODEL_SYNTHESIS,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"Erro na API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro na geração da síntese: {str(e)}")
        return None

def analyze_gameplay(game_name, custom_prompt, output_file=None):
    """Função principal que coordena todo o processo de análise"""
    try:
        # Grava o gameplay
        success, message, actual_duration = record_game_window(game_name)
        if not success:
            return {"success": False, "message": message, "report": None}

        # Valida o vídeo
        if not validate_video_file(temp_video):
            return {"success": False, "message": "Erro na validação do vídeo", "report": None}

        # Ajusta o número de frames baseado na duração real
        num_frames = max(5, min(15, int(actual_duration / 4)))  # 1 frame a cada 4 segundos, mínimo 5, máximo 15
        
        # Extrai frames-chave
        frames, timestamps = extract_key_frames(temp_video, num_frames=num_frames)
        if not frames:
            return {"success": False, "message": "Erro na extração dos frames", "report": None}

        # Analisa cada frame
        analyses = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i, (frame, timestamp) in enumerate(zip(frames, timestamps)):
                future = executor.submit(
                    analyze_frame,
                    frame,
                    i + 1,
                    len(frames),
                    timestamp,
                    custom_prompt
                )
                futures.append(future)

            for future in futures:
                result = future.result()
                if result:
                    analyses.append(result)

        # Gera o relatório final
        report = generate_final_report(analyses)
        
        # Salva o relatório se um arquivo de saída for especificado
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\nRelatório salvo em: {output_file}")

        # Gera e salva a síntese
        synthesis = generate_synthesis(report)
        if synthesis:
            with open(synthesis_file, "w", encoding="utf-8") as f:
                f.write(synthesis)
            print(f"\nSíntese salva em: {synthesis_file}")
        
        # Remove o vídeo temporário
        if os.path.exists(temp_video):
            os.remove(temp_video)
            
        return {"success": True, "message": "Análise concluída com sucesso", "report": report}

    except Exception as e:
        error_msg = f"Erro durante a análise: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg, "report": None}

def run_gameplay_analysis(jogo_alvo, gameplay_prompt, game_name):
    """Função wrapper para integração com Streamlit"""
    try:
        # Gera nome do arquivo de saída baseado no nome do jogo
        output_file = f"analise_{game_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # Executa a análise
        result = analyze_gameplay(jogo_alvo, gameplay_prompt, output_file)
        
        # Verifica se o resultado é um dicionário
        if isinstance(result, dict):
            return result
        else:
            # Se não for um dicionário, converte para o formato esperado
            return {
                'success': True,
                'message': 'Análise concluída com sucesso',
                'report': result
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Erro durante a análise: {str(e)}',
            'report': None
        }
