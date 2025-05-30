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

# Monitor settings for screen capture
monitor = {
    "top": 0,
    "left": 0,
    "width": 1920,
    "height": 1080
}
fps = 1.0

# File names
jogo_alvo = "Valorant.exe"
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = f"video_original_{timestamp}.avi"
tips_file = f"gameplay_tips_{timestamp}.md"

# API settings
OPENROUTER_API_KEY = "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"
GEMINI_API_KEY = 'AIzaSyBco-5bq8-o_0adSTuktqf6c8-xui0hDcU' 
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "opengvlab/internvl3-14b:free"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

def jogo_esta_rodando():
    """Check if the target game is running."""
    try:
        output = os.popen('tasklist').read()
        return jogo_alvo.lower() in output.lower()
    except:
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
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def make_openrouter_request(url, headers, payload, timeout):
    """Make a request to OpenRouter with retry logic."""
    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def analyze_gameplay_with_internvl(frames, sample_size=100):
    """Analyze gameplay frames using internvl via OpenRouter."""
    tips = []
    if not OPENROUTER_API_KEY or len(OPENROUTER_API_KEY) < 20:
        return ["Erro: Chave de API do OpenRouter inválida ou muito curta"]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Select diverse frames (e.g., evenly spaced)
    total_frames = len(frames)
    step = max(1, total_frames // sample_size)
    selected_frames = [frames[i * step] for i in range(min(sample_size, total_frames // step))]

    for i, frame in enumerate(selected_frames):
        try:
            # Convert frame to base64
            img_pil = Image.fromarray(frame)
            buffered = io.BytesIO()
            img_pil.save(buffered, format="JPEG", quality=85)
            base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # Inside the analyze_gameplay_with_internvl function
            prompt = (
               """Você é um analista especialista em Valorant e coach de e-sports. Sua tarefa é analisar os frames/clipes de uma gameplay de Valorant, focando na perspectiva do jogador principal, para identificar erros específicos e fornecer dicas construtivas e acionáveis para ajudá-lo a melhorar.
                **Instruções Detalhadas para Análise:**
                Por favor, analise os seguintes aspectos da gameplay e forneça feedback detalhado:
                1.  **Posicionamento de Mira (Crosshair Placement):**
                    * A mira está consistentemente na altura da cabeça dos oponentes?
                    * Está pré-posicionada em ângulos comuns, passagens e pontos de contato esperados?
                    * Há algum momento em que a mira está mal posicionada (ex: no chão, muito aberta, muito fechada em relação ao ângulo)?
                    * A mira acompanha o movimento do jogador de forma fluida ou parece "atrasada"?
                    * **Dica:** Se identificar erros, explique *por que* é um erro e *como* o jogador pode ajustar para um posicionamento ideal naquela situação.
                2.  **Movimentação e Posicionamento no Mapa:**
                    * O jogador está utilizando ângulos vantajosos? Está se expondo desnecessariamente?
                    * Como está a movimentação durante trocações (ex: strafing, counter-strafing)?
                    * O jogador está utilizando cover de forma eficaz?
                    * Há momentos de hesitação ou posicionamento passivo/agressivo inadequado para a situação?
                3.  **Rotações e Consciência de Mapa (Map Awareness):**
                    * As rotações foram feitas no tempo correto com base nas informações disponíveis (minimapa, sons, informações de aliados – se inferíveis)?
                    * O jogador parece antecipar movimentações inimigas ou objetivos?
                    * Houve falha em rotacionar ou em dar suporte a uma área crítica do mapa?
                    * **Dica:** Sugira como o jogador poderia ter usado melhor as informações do mapa para tomar decisões de rotação mais eficazes.
                4.  **Uso de Habilidades e Utilitários (Específico do Agente):**
                    * **Identificação do Agente (se não fornecido no contexto):** Se o agente não foi especificado, identifique-o a partir dos frames.
                    * **Habilidade Utilizada:** Para cada habilidade utilizada (Q, E, C, X - Ultimate):
                        * Foi a habilidade correta para a situação tática?
                        * O timing do uso foi adequado? (Ex: usou uma flash antes de abrir um ângulo? Usou uma smoke para cobrir um avanço no momento certo?)
                        * O posicionamento da habilidade foi ótimo? (Ex: smokes cobrindo todas as brechas, molotovs alcançando áreas estratégicas, flashes cegando efetivamente os inimigos sem prejudicar aliados).
                        * A habilidade foi usada de forma criativa ou estratégica?
                    * **Habilidades Não Utilizadas:** Houve momentos claros onde uma habilidade específica poderia ter mudado o resultado de uma jogada ou oferecido vantagem, mas não foi utilizada?
                    * **Economia de Utilitários:** O jogador está gastando utilitários de forma impulsiva ou conservando-os demais?
                    * **Uso Ideal e Estratégico:**
                        * Explique o uso ideal de cada utilitário do agente em questão, considerando diferentes cenários (ataque, defesa, retake, clutches).
                        * Compare o uso do jogador com estratégias comuns ou eficazes para aquele agente.
                        * **Dica:** Forneça exemplos concretos de como as habilidades poderiam ter sido usadas de forma mais impactante.
                5.  **Noção de Jogo e Tomada de Decisão (Game Sense):**
                    * As decisões tomadas pelo jogador fazem sentido tático considerando o estado do jogo (vantagem/desvantagem numérica, economia, tempo restante)?
                    * O jogador demonstrou compreensão dos objetivos do round (plantar/defusar a spike, eliminar todos os inimigos)?
                    * Como o jogador reagiu a informações novas (ex: som de passos, habilidade inimiga utilizada, morte de um aliado/inimigo)?
                    * Engajamentos: Foram bem escolhidos? O jogador lutou quando deveria recuar ou vice-versa?
                    * **Comparativo com Estratégias Profissionais/Alto Elo (Conceitual):**
                        * As jogadas se assemelham a setups, padrões de ataque/defesa ou tomadas de decisão comumente vistas em níveis mais altos de jogo? (Ex: setups de defesa padrão, execuções de ataque coordenadas, como jogar um pós-plant).
                        * Se o jogador cometeu um erro tático, explique qual seria uma abordagem mais estratégica, inspirada em conceitos de jogo de alto nível.
                6.  **Outras Dicas e Observações Gerais:**
                    * Comunicação (se houver alguma indicação visual, como pings no mapa feitos pelo jogador).
                    * Adaptação a jogadas inimigas (se observável).
                    * Erros de mecânica básica não cobertos anteriormente.
                    * Quaisquer outros padrões de comportamento que poderiam ser melhorados.
                **Formato da Resposta Esperada:**
                * **Clareza e Objetividade:** Vá direto ao ponto.
                * **Estrutura:** Organize a análise por categorias (Posicionamento de Mira, Uso de Habilidades, etc.).
                * **Especificidade:** Em vez de "uso ruim de smoke", diga "A smoke na entrada da B foi mal posicionada porque deixou uma fresta à direita, permitindo que um inimigo tivesse visão. O ideal seria posicioná-la mais profundamente para cobrir totalmente a passagem."
                * **Tom Construtivo:** O objetivo é ajudar o jogador a melhorar, não apenas criticar.
                * **Dicas Acionáveis:** As sugestões devem ser práticas e o jogador deve entender como aplicá-las.
                * **(Opcional) Priorização:** Se possível, indique 1-2 áreas mais críticas que o jogador deveria focar primeiro.

                **Exemplo de como iniciar a análise de um erro:**
                'No momento X:Y do vídeo/frame, observei um erro no seu posicionamento de mira ao avançar pelo corredor [Nome da Área do Mapa, se identificável]. Sua mira estava apontada para o chão. **Erro:** Mirar no chão diminui drasticamente seu tempo de reação caso um inimigo apareça. **Dica:** Mantenha sua mira sempre na altura da cabeça e pré-mire ângulos onde os inimigos costumam estar. Neste caso, ao entrar no corredor, sua mira deveria estar varrendo os cantos na altura da cabeça.'

                Analise o(s) frame(s)/clipe fornecido(s) e gere seu feedback. Estou aguardando sua análise detalhada!
                """

            )

            payload = {
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                        ]
                    }
                ],
                "max_tokens": 5000
            }

            response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=30)
            response.raise_for_status()

            if not response.text:
                tips.append(f"Frame {i+1}: API retornou resposta vazia")
                continue

            data = response.json()
            tip = data['choices'][0]['message']['content']
            tips.append(f"Frame {i+1}: {tip}")

        except requests.exceptions.HTTPError as http_err:
            tips.append(f"Frame {i+1}: Erro HTTP - {str(http_err)}")
        except requests.exceptions.ConnectionError as conn_err:
            tips.append(f"Frame {i+1}: Erro de conexão - Verifique sua internet ou DNS ({str(conn_err)})")
        except requests.exceptions.Timeout:
            tips.append(f"Frame {i+1}: Timeout na conexão com a API")
        except (KeyError, json.JSONDecodeError):
            tips.append(f"Frame {i+1}: Resposta inválida da API: {response.text[:100]}")
        except Exception as e:
            tips.append(f"Frame {i+1}: Erro geral - {str(e)}")

    return tips if tips else ["Nenhuma análise foi possível"]


# --- 1. Gravação do Vídeo ---
fourcc = cv2.VideoWriter_fourcc(*"XVID")
video_writer = cv2.VideoWriter(
    output_file,
    fourcc,
    fps,
    (monitor["width"], monitor["height"]),
    isColor=False
)

start_time = time.time()
frames_brutos = []

with mss() as sct:
    try:
        while True:
            if jogo_esta_rodando():
                frame = capturar_tela(sct, monitor)
                if frame is not None:
                    try:
                        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                        video_writer.write(gray_frame)
                        frames_brutos.append(gray_frame)

                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                    except Exception as e:
                        print(f"❌ Erro no processamento do frame: {str(e)}")
                        continue
            else:
                print("Jogo não está em execução. Aguardando...")
                time.sleep(10)
    except KeyboardInterrupt:
        print("\nGravação encerrada pelo usuário")

video_writer.release()
cv2.destroyAllWindows()

# --- 2. Verificação dos Dados ---
if not frames_brutos:
    print("❌ Nenhum frame válido foi capturado. Verifique:")
    print("- A região de captura está visível?")
    print("- Outro programa está bloqueando a captura?")
    exit()

# --- 5. Análise de Gameplay ---
print("Iniciando análise de gameplay com internvl...")
raw_tips = analyze_gameplay_with_internvl(frames_brutos, sample_size=100)

try:
    with open(tips_file, "w", encoding="utf-8") as f:
        f.write(raw_tips)
    print(f"✅ Relatório de dicas salvo em: {tips_file}")
except Exception as e:
    print(f"❌ Falha ao salvar relatório: {str(e)}")