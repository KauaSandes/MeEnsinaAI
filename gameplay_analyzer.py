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
import time
import mss
import psutil
import csv
import re

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

# Prompts pré-definidos para cada jogo
GAME_PROMPTS = {
    "Counter-Strike 2": """Você é um analista profissional de CS2 (Counter-Strike 2) especializado em coaching. 
    Analise este frame e forneça feedback técnico e específico sobre:
    
    1. Identificação Precisa:
    
    a) Identificação do Lado (procure especificamente na região inferior central da tela):
    - Procure pelo ícone do time no centro do HUD inferior
    - Se o ícone for AZUL com formato de alicate com asas: Lado CT
    - Se o ícone for AMARELO com duas facas cruzadas e estrela: Lado T
    - Indique o lado com 100% de certeza apenas se visualizar o ícone
    
    b) Identificação do Mapa (analise o minimapa no canto superior esquerdo):
    Baseado no layout do minimapa, compare com esta referência de minimapas do CS2:
    
    - Ancient: Formato quadrado com estrutura central circular e três caminhos principais
    - Anubis: Layout em H com área central aberta e sites triangulares
    - Inferno: Formato de 8 com banana à esquerda e apps à direita
    - Mirage: Layout em T com mid conectando A ramp e B apps
    - Nuke: Dois níveis sobrepostos com rampa exterior
    - Overpass: Formato em Y com área de CT elevada
    - Vertigo: Dois níveis com heliporto e área de construção
    
    Indique o mapa apenas se tiver alta confiança baseado no layout do minimapa.
    
    c) Informações Adicionais:
    - Qual arma principal está sendo usada?
    - Qual a fase do round (pistol, eco, semi-buy, full-buy)?
    - Qual o estado econômico da equipe (baseado no HUD)?
    
    2. Análise Técnica (identifique explicitamente UM erro principal):
    a) Posicionamento e Ângulos:
    - O posicionamento oferece cobertura adequada?
    - Os ângulos estão sendo segurados corretamente?
    - Existe exposição a múltiplos ângulos simultaneamente?
    
    b) Aim e Movimentação:
    - O crosshair está na altura correta?
    - O counter-strafing está sendo executado corretamente?
    - O peek está sendo feito de forma adequada?
    
    c) Uso de Utility:
    - As granadas (smokes, flashes, HE, molotov) estão sendo utilizadas efetivamente?
    - Existe desperdício de utility?
    - As utilities estão sendo combinadas com a equipe?
    
    d) Economia e Loadout:
    - O buy faz sentido para a situação econômica?
    - O kit de utilities está adequado?
    - A distribuição de equipamento na equipe está equilibrada?
    
    e) Game Sense:
    - A rotação/posicionamento faz sentido com a informação disponível?
    - O timing das ações está adequado?
    - Existe consciência do tempo de round e objetivos?
    
    3. Erro Principal:
    - Identifique o erro mais crítico neste frame
    - Forneça uma sugestão específica de correção
    - Se possível, sugira um workshop map ou exercício específico para melhorar este aspecto""",

    "Street Fighter 5": """Você é um analista profissional de Street Fighter 5 especializado em coaching. 
    Analise este frame e forneça feedback técnico e específico sobre:
    
    1. Identificação:
    - Qual personagem está sendo usado?
    - Qual personagem está enfrentando?
    - Qual o estágio da luta?
    - Situação das barras de vida e Drive Gauge?
    - Estado atual do round (neutral, pressão, okizeme, etc)?
    
    2. Análise Técnica (identifique explicitamente UM erro principal):
    a) Neutral Game:
    - O espaçamento está adequado para o personagem?
    - Está utilizando as ferramentas corretas para a situação?
    - Como está o controle de espaço?
    
    b) Defesa e Anti-airs:
    - A defesa está apropriada para a situação?
    - Está reagindo corretamente a pulos?
    - Está defendendo mix-ups adequadamente?
    
    c) Ofensiva e Combos:
    - Os combos estão sendo otimizados?
    - Está aproveitando as oportunidades de punish?
    - O uso do Drive System está eficiente?
    
    d) Recursos e Meter Management:
    - Como está o gerenciamento da Drive Gauge?
    - Está usando Super Arts em momentos apropriados?
    - O uso de Drive Rush/Parry/Reversal está eficiente?
    
    e) Adaptação e Mind Games:
    - Está identificando os padrões do oponente?
    - Como está a variação de opções ofensivas/defensivas?
    - Está adaptando a estratégia conforme necessário?
    
    3. Erro Principal:
    - Identifique o erro mais crítico neste frame
    - Forneça uma sugestão específica de correção
    - Sugira exercícios específicos no modo treino para melhorar este aspecto"""
}


def record_game_window(game_exe, duration=60):
    """Grava a tela do jogo por um período específico"""
    try:
        # Procura o processo do jogo em execução
        game_process = None
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'].lower() == game_exe.lower():
                    game_process = process
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if not game_process:
            print(
                f"Processo do jogo {game_exe} não encontrado. Certifique-se de que o jogo está em execução.")
            return False

        # Configurações de gravação
        fps = 30.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        # Inicializa o MSS para captura de tela
        with mss.mss() as sct:
            # Captura o monitor primário
            # monitor[1] é geralmente o monitor primário
            monitor = sct.monitors[1]

            # Define as dimensões da captura
            width = monitor["width"]
            height = monitor["height"]

            # Inicializa o gravador
            out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

            print(f"Iniciando gravação por {duration} segundos...")
            start_time = time.time()

            while (time.time() - start_time) < duration:
                # Captura a tela
                screenshot = np.array(sct.grab(monitor))

                # Converte BGRA para BGR (remove o canal alpha)
                frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

                # Grava o frame
                out.write(frame)

                # Mostra tempo restante
                remaining = int(duration - (time.time() - start_time))
                print(f"\rTempo restante: {remaining} segundos...", end="")

                # Pequeno delay para reduzir uso de CPU
                time.sleep(1/fps)

            # Libera recursos
            out.release()
            print("\nGravação concluída!")
            return True

    except Exception as e:
        print(f"\nErro durante a gravação: {str(e)}")
        return False


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
    retry=retry_if_exception_type(
        (requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def make_openrouter_request(url, headers, payload, timeout):
    """Request no OpenRouter"""
    return requests.post(url, headers=headers, json=payload, timeout=timeout)


def analyze_frame(frame_base64, frame_number, total_frames, timestamp, game_prompt):
    """Análise aprofundada de cada frame"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Game Analysis",
        "OpenAI-Organization": "openrouter"
    }

    payload = {
        "model": MODEL_VISION,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": game_prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{frame_base64}"}}
                ]
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False
    }

    try:
        print(
            f"\nAnalisando frame {frame_number}/{total_frames} (timestamp: {timestamp:.1f}s)...")
        response = make_openrouter_request(
            OPENROUTER_API_URL, headers, payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            analysis = data['choices'][0]['message']['content']
            print(f"Frame {frame_number} analisado com sucesso!")
            return {
                'frame_number': frame_number,
                'timestamp': timestamp,
                'analysis': analysis
            }
        else:
            error_msg = f"Erro na análise do frame {frame_number}: Status {response.status_code}"
            print(error_msg)
            return {'error': error_msg}

    except Exception as e:
        error_msg = f"Erro durante a análise do frame {frame_number}: {str(e)}"
        print(error_msg)
        return {'error': error_msg}


def generate_final_report(analyses, game_name):
    """Gera um relatório final estruturado com todas as análises"""
    report = f"""# Análise Detalhada de Gameplay - {game_name}\n\n"""

    for analysis in analyses:
        if 'error' not in analysis:
            report += f"\n### Frame {analysis['frame_number']} (Timestamp: {analysis['timestamp']:.1f}s)\n"
            report += f"{analysis['analysis']}\n"

    return report


def generate_synthesis(analysis_content, game_name):
    """Gera uma síntese detalhada usando Claude-4"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Game Analysis",
        "OpenAI-Organization": "openrouter"
    }

    synthesis_prompt = f"""
    Você é um analista profissional de {game_name} com vasta experiência em coaching. 
    Analise o seguinte relatório de gameplay e crie uma síntese detalhada focando nos seguintes aspectos:

    1. Contexto do Jogo
    2. Padrões de Erro por Contexto
    3. Análise Técnica Detalhada
    4. Recomendações Específicas
    5. Plano de Desenvolvimento
    6. Conclusão

    Mantenha a síntese objetiva e prática, focando nas informações mais relevantes para o desenvolvimento do jogador.
    Organize as informações de forma clara e estruturada, usando títulos e subtítulos para facilitar a leitura.
    Priorize recomendações específicas e acionáveis baseadas no contexto observado.

    Relatório para análise:
    {analysis_content}
    """

    payload = {
        "model": MODEL_SYNTHESIS,
        "messages": [
            {
                "role": "user",
                "content": synthesis_prompt
            }
        ],
        "max_tokens": 4000,
        "temperature": 0.7,
        "stream": False
    }

    try:
        print("\nGerando síntese detalhada da análise usando Claude-4...")
        response = make_openrouter_request(
            OPENROUTER_API_URL, headers, payload, timeout=120)

        if response.status_code == 200:
            data = response.json()
            synthesis = data['choices'][0]['message']['content']

            formatted_synthesis = f"""# Síntese de Análise - {game_name}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

{synthesis}

"""

            return formatted_synthesis
        else:
            error_msg = f"Erro ao gerar síntese: Status {response.status_code}"
            print(error_msg)
            return error_msg

    except Exception as e:
        error_msg = f"Erro durante a geração da síntese: {str(e)}"
        print(error_msg)
        return error_msg


def generate_gameplay_score(analysis_content, game_name):
    """Gera uma nota de 0 a 10 para a gameplay usando Claude-4"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Game Analysis",
        "OpenAI-Organization": "openrouter"
    }

    score_prompt = f"""
    Você é um analista profissional de {game_name} com vasta experiência em coaching. 
    Com base no relatório de gameplay fornecido, atribua uma nota de 0 a 10 e justifique sua avaliação.
    
    Considere os seguintes aspectos:
    1. Técnica e Mecânicas
    2. Tomada de Decisão
    3. Consistência
    4. Eficiência
    5. Adaptação
    
    Forneça:
    1. A nota final (apenas o número de 0 a 10)
    2. Uma breve justificativa (2-3 frases)
    3. O aspecto mais forte do jogador
    4. O aspecto que mais precisa de melhoria
    
    Relatório para análise:
    {analysis_content}
    """

    payload = {
        "model": MODEL_SYNTHESIS,
        "messages": [
            {
                "role": "user",
                "content": score_prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.7,
        "stream": False
    }

    try:
        print("\nGerando nota para a gameplay...")
        response = make_openrouter_request(
            OPENROUTER_API_URL, headers, payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            score_analysis = data['choices'][0]['message']['content']
            return score_analysis
        else:
            error_msg = f"Erro ao gerar nota: Status {response.status_code}"
            print(error_msg)
            return error_msg

    except Exception as e:
        error_msg = f"Erro durante a geração da nota: {str(e)}"
        print(error_msg)
        return error_msg


def save_report_to_csv(game_name, report_content, score_analysis):
    """Salva o relatório em um arquivo CSV"""
    csv_file = "gameplay_reports.csv"
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Extrair a nota do score_analysis (assumindo que é o primeiro número encontrado)
    score_match = re.search(r'\b([0-9]|10)\b', score_analysis)
    score = score_match.group(0) if score_match else "N/A"

    # Criar ou atualizar o arquivo CSV
    file_exists = os.path.exists(csv_file)

    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Escrever cabeçalho se o arquivo não existir
        if not file_exists:
            writer.writerow(['Data', 'Jogo', 'Nota', 'Relatório Completo'])

        # Escrever os dados
        writer.writerow([current_date, game_name, score, report_content])


def get_reports_csv():
    """Retorna o conteúdo do arquivo CSV de relatórios"""
    if os.path.exists("gameplay_reports.csv"):
        with open("gameplay_reports.csv", 'r', encoding='utf-8') as f:
            return f.read()
    return None


def run_gameplay_analysis(game_exe, game_name):
    """Função principal de análise do gameplay"""
    synthesis_file = f"SINTESE_{game_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    if not record_game_window(game_exe):
        return {"success": False, "message": "Erro na gravação do gameplay"}

    if not os.path.exists(temp_video):
        return {"success": False, "message": "Arquivo de vídeo não encontrado"}

    try:
        print("Extraindo frames-chave do vídeo...")
        frames, timestamps = extract_key_frames(temp_video)
        total_frames = len(frames)

        print(f"Analisando {total_frames} frames...")
        analyses = []

        game_prompt = GAME_PROMPTS.get(game_name)
        if not game_prompt:
            return {"success": False, "message": "Jogo não suportado"}

        for i, (frame, timestamp) in enumerate(zip(frames, timestamps), 1):
            analysis = analyze_frame(
                frame, i, total_frames, timestamp, game_prompt)
            analyses.append(analysis)

        final_report = generate_final_report(analyses, game_name)

        # Gerar síntese
        synthesis = generate_synthesis(final_report, game_name)

        # Gerar nota
        score_analysis = generate_gameplay_score(final_report, game_name)

        # Combinar síntese com nota
        final_report = f"{synthesis}\n\n## Avaliação da Gameplay\n\n{score_analysis}"

        # Salvar síntese em arquivo
        try:
            with open(synthesis_file, "w", encoding="utf-8") as f:
                f.write(final_report)
            print(f"Síntese salva em: {synthesis_file}")

            # Salvar no CSV
            save_report_to_csv(game_name, final_report, score_analysis)

        except Exception as e:
            print(f"Erro ao salvar síntese: {str(e)}")

        # Limpar arquivo temporário
        if os.path.exists(temp_video):
            os.remove(temp_video)

        return {"success": True, "report": final_report}

    except Exception as e:
        if os.path.exists(temp_video):
            os.remove(temp_video)
        return {"success": False, "message": str(e)}
