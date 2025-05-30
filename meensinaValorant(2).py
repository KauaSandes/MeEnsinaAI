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
fps = 2.0

# File names
jogo_alvo = "Valorant.exe"
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = f"video_original_{timestamp}.avi"
compressed_file = f"video_comprimido_{timestamp}.mp4"
ml_data_file = f"dados_ml_{timestamp}.npy"
tips_file = f"gameplay_tips_{timestamp}.md"

# API settings
OPENROUTER_API_KEY = "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"
GEMINI_API_KEY = 'AIzaSyBco-5bq8-o_0adSTuktqf6c8-xui0hDcU'  # Replace with your Gemini API key
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
                "Você é um especialista em Valorant. Analise este frame de gameplay e forneça feedback técnico e específico. "
                "Concentre-se em: "
                "- Posicionamento do jogador (está em uma boa posição no mapa? Evitando overpeeks?). "
                "- Precisão de mira e colocação do crosshair (está no nível da cabeça? Antecipando inimigos?). "
                "- Uso de habilidades e utilitários (smokes, flashes, paredes estão sendo usados corretamente?). "
                "- Coordenação com a equipe (está cobrindo ângulos ou jogando isolado?). "
                "- Gestão de economia (armas, armaduras e utilitários condizem com a economia do time?). "
                "- Erros comuns do jogador e como corrigi-los (ex.: rotação tardia, recarga em momento errado). "
                "Forneça dicas práticas e objetivas, com exemplos concretos baseados no frame, como 'Mova seu crosshair para o nível da cabeça no ângulo X'."
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
                "max_tokens": 500
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

def synthesize_tips_with_gemini(raw_tips):
    """Synthesize raw tips into a polished report using Gemini."""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (
            "Você é um assistente de jogos especializado em Valorant. Recebi as seguintes análises de gameplay de um modelo de visão: \n\n"
            f"{' '.join(raw_tips)}\n\n"
            "Sua tarefa é sintetizar essas dicas em um relatório claro, conciso e objetivo em Markdown. Estruture o relatório com: "
            "- Uma introdução resumindo o desempenho geral do jogador. "
            "- Uma lista de dicas específicas, organizadas por categoria (ex.: Posicionamento, Mira, Uso de Habilidades, Coordenação com Equipe, Gestão de Economia). "
            "- Uma conclusão com recomendações gerais para melhoria. "
            "Use linguagem direta e exemplos práticos, como 'Posicione-se no canto da B Long em Bind para evitar overpeeks'. Máximo de 500 palavras."
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao sintetizar dicas com Gemini: {str(e)}"

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

# --- 3. Compressão do Vídeo ---

# --- 4. Pré-Processamento para ML ---
try:
    frames_ml = np.array([cv2.resize(f, (64, 64))/255.0 for f in frames_brutos])
    np.save(ml_data_file, frames_ml)
    print(f"✅ Dados para ML salvos em: {ml_data_file}")
    print(f"Shape dos dados: {frames_ml.shape}")
except Exception as e:
    print(f"❌ Falha no pré-processamento: {str(e)}")

# --- 5. Análise de Gameplay ---
print("Iniciando análise de gameplay com internvl...")
raw_tips = analyze_gameplay_with_internvl(frames_brutos, sample_size=5)
print("Sintetizando dicas com Gemini...")
final_report = synthesize_tips_with_gemini(raw_tips)

try:
    with open(tips_file, "w", encoding="utf-8") as f:
        f.write(final_report)
    print(f"✅ Relatório de dicas salvo em: {tips_file}")
except Exception as e:
    print(f"❌ Falha ao salvar relatório: {str(e)}")