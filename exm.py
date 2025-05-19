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
os.environ["API_KEY"] = "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"
jogo_alvo = "Dungeons.exe"  
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = f"video_original_{timestamp}.avi"
compressed_file = f"video_comprimido_{timestamp}.mp4"
ml_data_file = f"dados_ml_{timestamp}.npy"
tips_file = f"gameplay_tips_{timestamp}.txt"

# OpenRouter AI API settings
API_KEY = ("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")
API_URL = "https://api.openrouter.ai/api/v1/chat/completions"
MODEL = "meta-ai/llama-3.2-vision-instruct:11b"

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
    tips = []
    
    # Verificação básica da API_KEY
    if not API_KEY or len(API_KEY) < 20:
        return ["Erro: Chave de API inválida ou muito curta"]
    
    # Configuração dos headers obrigatórios para OpenRouter
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://localhost",  # Obrigatório pelo OpenRouter
        "Content-Type": "application/json"
    }
    
    for i in range(min(sample_size, len(frames))):
        try:
            # Converte o frame para base64
            img_pil = Image.fromarray(frames[i])
            buffered = io.BytesIO()
            img_pil.save(buffered, format="JPEG", quality=85)
            base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Payload corrigido para OpenRouter
            payload = {
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analise esta gameplay de Blasphemous..."},
                            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                        ]
                    }
                ],
                "max_tokens": 300
            }
            
            # Faz a requisição com timeout
            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Verifica se a resposta está vazia
            if not response.text:
                tips.append(f"Frame {i+1}: API retornou resposta vazia")
                continue
                
            # Tenta parsear o JSON
            try:
                data = response.json()
                tip = data['choices'][0]['message']['content']
                tips.append(f"Frame {i+1}: {tip}")
            except (KeyError, json.JSONDecodeError):
                tips.append(f"Frame {i+1}: Resposta inválida da API: {response.text[:100]}")
                
        except Exception as e:
            tips.append(f"Frame {i+1}: Erro - {str(e)}")
    
    return tips if tips else ["Nenhuma análise foi possível"]
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