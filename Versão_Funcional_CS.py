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
video_input = "MIRAGE1.mp4"  
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
analysis_file = f"ANALISE_CS2_{timestamp}.md"
synthesis_file = f"SINTESE_CS2_{timestamp}.md"

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
    """Análise aprofundada de cada frame com foco em CS2"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "CS2 Gameplay Analysis",
        "OpenAI-Organization": "openrouter"
    }

    prompt = f"""
    Você é um analista profissional de CS2 (Counter-Strike 2) especializado em coaching. 
    Analise este frame {frame_number}/{total_frames} (timestamp: {timestamp:.1f}s).
    
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
    - Se possível, sugira um workshop map ou exercício específico para melhorar este aspecto
    
    Mantenha a análise objetiva e focada em aspectos técnicos observáveis.
    Para identificação do lado e mapa, use APENAS os elementos visuais específicos mencionados (ícone do time e minimapa).
    Se não for possível ver claramente esses elementos, indique como "Não visível neste frame".
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
    report = """# Análise Detalhada de Gameplay - CS2\n\n"""
    
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
        "X-Title": "CS2 Gameplay Analysis",
        "OpenAI-Organization": "openrouter"
    }

    synthesis_prompt = f"""
    Você é um analista profissional de CS2 com vasta experiência em coaching. 
    Analise o seguinte relatório de gameplay e crie uma síntese detalhada focando nos seguintes aspectos:

    1. Contexto do Jogo:
    - Qual mapa está sendo jogado (baseado nas menções mais frequentes)?
    - Qual lado o jogador está (CT ou T)?
    - Quais são as fases de compra mais comuns observadas?
    - Como está o estado econômico geral da equipe?
    - Quais armas o jogador mais utiliza?

    2. Padrões de Erro por Contexto:
    - Erros específicos para o mapa identificado
    - Erros relacionados ao lado (CT/T) que está jogando
    - Problemas com escolhas de armas e economia
    - Erros de posicionamento específicos do mapa

    3. Análise Técnica Detalhada:
    a) Aim e Movimentação:
    - Padrões de posicionamento do crosshair
    - Qualidade do counter-strafing e peek
    - Eficácia no controle de spray

    b) Uso de Utilities:
    - Eficiência no uso de granadas
    - Conhecimento de lineups
    - Coordenação com a equipe

    c) Posicionamento e Game Sense:
    - Conhecimento de ângulos do mapa
    - Timing de rotações
    - Leitura do jogo e adaptação

    4. Recomendações Específicas:
    a) Para o Mapa:
    - Posições específicas para treinar
    - Lineups importantes para aprender
    - Ângulos cruciais para dominar

    b) Para o Lado (CT/T):
    - Estratégias específicas para melhorar
    - Posições defensivas/ofensivas recomendadas
    - Utilities prioritárias

    c) Para Economia:
    - Sugestões de rounds de economia
    - Prioridades de compra
    - Gestão de utilities

    5. Plano de Desenvolvimento:
    - 3-5 principais áreas para melhoria imediata
    - Sugestões de mapas de workshop específicos para cada área
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
            
            formatted_synthesis = f"""# Síntese de Análise - CS2
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
print("Iniciando análise detalhada do gameplay de CS2...")
raw_analysis = analyze_gameplay(video_input, analysis_file)

try:
    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write(raw_analysis[0])
    print(f"Relatório de análise salvo em: {analysis_file}")
except Exception as e:
    print(f"Falha ao salvar relatório: {str(e)}")

print("Análise concluída.")



