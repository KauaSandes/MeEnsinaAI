import cv2
import numpy as np
from mss import mss
import time
from datetime import datetime
import subprocess
import os
import requests
import base64
import json
from PIL import Image
import io
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Monitor settings for screen capture
monitor = {
    "top": 0,
    "left": 0,
    "width": 1920,
    "height": 1080
}
fps = 10.0

# File names
jogo_alvo = "jogo.exe"  # Generic game executable
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = f"video_original_{timestamp}.avi"
compressed_file = f"video_comprimido_{timestamp}.mp4"
ml_data_file = f"dados_ml_{timestamp}.npy"
tips_file = f"gameplay_tips_{timestamp}.txt"

# Together AI API settings
API_KEY = os.getenv("TOGETHER_API_KEY")
if not API_KEY:
    raise ValueError("TOGETHER_API_KEY environment variable not set")
API_URL = "https://api.together.xyz/v1/chat/completions"
MODEL = "meta-llama/Llama-Vision-Free"

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

def image_to_base64(frame):
    """Convert a numpy array frame to base64 string."""
    try:
        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(frame)
        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"❌ Erro ao converter imagem para base64: {str(e)}")
        return None

def analyze_gameplay(frames, sample_size=5):
    """Analyze gameplay frames using Llama 3.2 11B API and return tips."""
    tips = []
    if len(frames) < sample_size:
        sample_size = len(frames)
    if sample_size == 0:
        return ["Nenhum frame disponível para análise."]

    # Sample frames evenly from the recorded gameplay
    indices = np.linspace(0, len(frames) - 1, sample_size, dtype=int)
    sampled_frames = [frames[i] for i in indices]

    for i, frame in enumerate(sampled_frames):
        # Convert frame to base64 for API
        base64_image = image_to_base64(frame)
        if not base64_image:
            continue

        # Prepare the prompt for gameplay analysis
        prompt = (
            "Você é um especialista em Super Mario Bros (NES). Analise esta imagem de gameplay "
            "e identifique padrões ou erros no jogo, como falhas em pulos, colisões com inimigos, "
            "ou movimentos ineficientes. Forneça dicas específicas para o jogador melhorar seu desempenho. "
            "Descreva brevemente o que observa na imagem e sugira 1-2 dicas práticas."
        )

        # API payload
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        # Send request to Together AI API
        try:
            response = requests.post(API_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            tip = result["choices"][0]["message"]["content"]
            tips.append(f"Frame {i+1}: {tip}")
        except Exception as e:
            print(f"❌ Erro na análise do frame {i+1}: {str(e)}")
            tips.append(f"Frame {i+1}: Falha na análise devido a erro na API.")

    return tips if tips else ["Nenhuma dica gerada devido a falhas na análise."]

# --- 1. Gravação do Vídeo --- #
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

# --- 2. Verificação dos Dados --- #
if not frames_brutos:
    print("❌ Nenhum frame válido foi capturado. Verifique:")
    print("- A região de captura está visível?")
    print("- Outro programa está bloqueando a captura?")
    exit()

# --- 3. Compressão do Vídeo --- #
if os.path.exists(output_file):
    try:
        subprocess.run([
            "ffmpeg",
            "-i", output_file,
            "-crf", "28",
            "-preset", "ultrafast",
            compressed_file
        ], check=True)
        print(f"✅ Vídeo comprimido: {compressed_file}")
    except Exception as e:
        print(f"❌ Falha na compressão: {str(e)}")
else:
    print(f"⚠️ Arquivo {output_file} não encontrado para compressão")

# --- 4. Pré-Processamento para ML --- #
try:
    frames_ml = np.array([cv2.resize(f, (64, 64))/255.0 for f in frames_brutos])
    np.save(ml_data_file, frames_ml)
    print(f"✅ Dados para ML salvos em: {ml_data_file}")
    print(f"Shape dos dados: {frames_ml.shape}")
except Exception as e:
    print(f"❌ Falha no pré-processamento: {str(e)}")

# --- 5. Análise de Gameplay com Llama 3.2 11B --- #
print("Iniciando análise de gameplay com Llama 3.2 11B...")
tips = analyze_gameplay(frames_brutos, sample_size=5)
try:
    with open(tips_file, "w", encoding="utf-8") as f:
        f.write("\n".join(tips))
    print(f"✅ Dicas de gameplay salvas em: {tips_file}")
except Exception as e:
    print(f"❌ Falha ao salvar dicas: {str(e)}")