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

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Configurações globais
video_input = "SF.mp4"  
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
analysis_file = f"ANALISE_SF6_{timestamp}.md"
synthesis_file = f"SINTESE_SF6_{timestamp}.md"

# Configurações das APIs
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_VISION = "opengvlab/internvl3-14b:free"
MODEL_SYNTHESIS = "anthropic/claude-opus-4"

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

def analyze_frame(frame_base64, frame_number, total_frames, timestamp):
    """Análise aprofundada de cada frame com foco em Street Fighter 6"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Street Fighter 6 Gameplay Analysis",
        "OpenAI-Organization": "openrouter"
    }

    prompt = f"""
    Você é um analista profissional de Street Fighter 6 especializado em coaching. 
    Analise este frame {frame_number}/{total_frames} (timestamp: {timestamp:.1f}s).
    
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
    - Sugira exercícios específicos no modo treino para melhorar este aspecto
    
    Mantenha a análise objetiva e focada em aspectos técnicos observáveis.
    """

    payload = {
        "model": MODEL_VISION,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}"}}
                ]
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False
    }

    try:
        print(f"\nAnalisando frame {frame_number}/{total_frames} (timestamp: {timestamp:.1f}s)...")
        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=60)
        
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

def generate_final_report(analyses):
    """Gera um relatório final estruturado com todas as análises"""
    report = """# Análise Detalhada de Gameplay - Street Fighter 6\n\n"""
    
    for analysis in analyses:
        if 'error' not in analysis:
            report += f"\n### Frame {analysis['frame_number']} (Timestamp: {analysis['timestamp']:.1f}s)\n"
            report += f"{analysis['analysis']}\n"
    
    return report

def generate_synthesis(analysis_content):
    """Gera uma síntese detalhada usando Claude-4"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Street Fighter 6 Gameplay Analysis",
        "OpenAI-Organization": "openrouter"
    }

    synthesis_prompt = f"""
    Você é um analista profissional de Street Fighter 6 com vasta experiência em coaching. 
    Analise o seguinte relatório de gameplay e crie uma síntese detalhada focando nos seguintes aspectos:

    1. Contexto da Partida:
    - Qual personagem está sendo usado?
    - Qual matchup está sendo jogado?
    - Quais são os padrões de jogo mais comuns observados?
    - Como está o gerenciamento de recursos (Drive Gauge, Super Arts)?
    - Quais são as principais ferramentas utilizadas?

    2. Padrões de Erro por Contexto:
    - Erros específicos para o personagem escolhido
    - Erros relacionados ao matchup específico
    - Problemas com gerenciamento de recursos
    - Erros de posicionamento e espaçamento

    3. Análise Técnica Detalhada:
    a) Neutral Game:
    - Efetividade no controle de espaço
    - Uso de normais e especiais
    - Adaptação ao estilo do oponente

    b) Sistema Defensivo:
    - Qualidade dos anti-airs
    - Eficiência na defesa de mix-ups
    - Uso do Drive Parry

    c) Sistema Ofensivo:
    - Otimização de combos
    - Eficiência nos punishes
    - Qualidade do okizeme

    4. Recomendações Específicas:
    a) Para o Personagem:
    - Combos prioritários para treinar
    - Setups importantes para aprender
    - Confirms cruciais para dominar

    b) Para o Matchup:
    - Estratégias específicas para melhorar
    - Opções defensivas/ofensivas recomendadas
    - Situações prioritárias para treinar

    c) Para Gerenciamento de Recursos:
    - Uso otimizado da Drive Gauge
    - Momentos ideais para Super Arts
    - Gerenciamento de Drive Rush/Parry

    5. Plano de Desenvolvimento:
    - 3-5 principais áreas para melhoria imediata
    - Exercícios específicos no modo treino
    - Rotina de treino recomendada

    6. Conclusão:
    - Avaliação geral do nível atual
    - Pontos fortes identificados
    - Próximos passos práticos para evolução

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
        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            synthesis = data['choices'][0]['message']['content']
            
            formatted_synthesis = f"""# Síntese de Análise - Street Fighter 6
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

{synthesis}

---
Análise gerada por Claude-4 com base nos dados do InternVL"""
            
            return formatted_synthesis
        else:
            error_msg = f"Erro ao gerar síntese: Status {response.status_code}"
            print(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Erro durante a geração da síntese: {str(e)}"
        print(error_msg)
        return error_msg

def analyze_gameplay(video_path, output_file):
    """Função principal de análise do gameplay"""
    if not os.path.exists(video_path):
        return ["Erro: Arquivo de vídeo não encontrado"]

    print("Extraindo frames-chave do vídeo...")
    frames, timestamps = extract_key_frames(video_path)
    total_frames = len(frames)
    
    print(f"Analisando {total_frames} frames...")
    analyses = []
    
    for i, (frame, timestamp) in enumerate(zip(frames, timestamps), 1):
        analysis = analyze_frame(frame, i, total_frames, timestamp)
        analyses.append(analysis)
    
    final_report = generate_final_report(analyses)
    
    # Gerar síntese com Claude-4
    synthesis = generate_synthesis(final_report)
    try:
        with open(synthesis_file, "w", encoding="utf-8") as f:
            f.write(synthesis)
        print(f"Síntese salva em: {synthesis_file}")
    except Exception as e:
        print(f"Erro ao salvar síntese: {str(e)}")
    
    return [final_report]

# Execução principal
print("Iniciando análise detalhada do gameplay de Street Fighter 6...")
raw_analysis = analyze_gameplay(video_input, analysis_file)

try:
    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write(raw_analysis[0])
    print(f"Relatório de análise salvo em: {analysis_file}")
except Exception as e:
    print(f"Falha ao salvar relatório: {str(e)}")

print("Análise concluída.")



