import requests
import base64
import os
from datetime import datetime
import warnings
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# nome do video de gameplay
video_input = "gameplay_teste (2).mp4"  

# nomes dos arquivos
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
tips_file_internvl = f"gameplay_tips_internvl3_{timestamp}.md"
tips_file_gemini = f"gameplay_tips_gemini_{timestamp}.md"
tips_file_llama = f"gameplay_tips_llama_{timestamp}.md"

# setando as API's
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_INTERNVL3 = "opengvlab/internvl3-14b:free"
MODEL_GEMINI = "google/gemini-2.5-pro-preview" 
MODEL_LLAMA = "meta-llama/llama-3.2-11b-vision-instruct:free"

def validate_video_file(video_path):
    """Validação do vídeo"""
    if not os.path.exists(video_path):
        print(f"Vídeo não encontrado: {video_path}")
        return False
    if not video_path.lower().endswith('.mp4'):
        print(f"Formato inválido: O arquivo deve ser .mp4")
        return False
    return True

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def make_openrouter_request(url, headers, payload, timeout):
    """request no OpenRouter"""
    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def analyze_full_video(video_path, model_name, output_file):
    """Analise do video"""
    if not validate_video_file(video_path):
        return [f"Erro: Arquivo de vídeo inválido ou não encontrado para {model_name}"]

    if not OPENROUTER_API_KEY or len(OPENROUTER_API_KEY) < 20:
        return [f"Erro: Chave de API do OpenRouter inválida ou muito curta para {model_name}"]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # codificar o video para base64
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()
        base64_video = base64.b64encode(video_data).decode('utf-8')

        prompt = (
            "Você é um especialista em Valorant. Analise este vídeo de gameplay completo e forneça um feedback técnico e específico. "
            "Concentre-se em: "
            "- Posicionamento do jogador (está em boas posições no mapa? Evitando overpeeks?). "
            "- Precisão de mira e colocação do crosshair (está no nível da cabeça? Antecipando inimigos?). "
            "- Uso de habilidades e utilitários (smokes, flashes, paredes estão sendo usados corretamente?). "
            "- Coordenação com a equipe (está cobrindo ângulos ou jogando isolado?). "
            "- Gestão de economia (armas, armaduras e utilitários condizem com a economia do time?). "
            "- Erros comuns do jogador e como corrigi-los (ex.: rotação tardia, recarga em momento errado). "
            "Forneça um relatório detalhado em Markdown com uma introdução resumindo o desempenho geral, "
            "uma lista de dicas específicas organizadas por categoria (Posicionamento, Mira, Uso de Habilidades, "
            "Coordenação com Equipe, Gestão de Economia), e uma conclusão com recomendações gerais para melhoria. "
            "Use exemplos práticos, como 'Posicione-se no canto da B Long em Bind para evitar overpeeks'."
        )

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "video_url", "video_url": f"data:video/mp4;base64,{base64_video}"}
                    ]
                }
            ],
            "max_tokens": 1000
        }

        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=60)
        response.raise_for_status()

        if not response.text:
            return [f"API retornou resposta vazia para {model_name}"]

        data = response.json()
        analysis = data['choices'][0]['message']['content']
        return [analysis]

    except requests.exceptions.HTTPError as http_err:
        return [f"Erro HTTP para {model_name} - {str(http_err)}"]
    except requests.exceptions.ConnectionError as conn_err:
        return [f"Erro de conexão para {model_name} - Verifique sua internet ou DNS ({str(conn_err)})"]
    except requests.exceptions.Timeout:
        return [f"Timeout na conexão com a API para {model_name}"]
    except (KeyError, json.JSONDecodeError):
        return [f"Resposta inválida da API para {model_name}: {response.text[:100]}"]
    except Exception as e:
        return [f"Erro geral para {model_name} - {str(e)}"]

# --- 1. Análise do Vídeo com Três LLMs ---
models = [
    (MODEL_INTERNVL3, tips_file_internvl, "InternVL3-14B"),
    (MODEL_GEMINI, tips_file_gemini, "Gemini-2.5-Pro-Preview"),
    (MODEL_LLAMA, tips_file_llama, "Llama-3.2-11B-Vision")
]

for model_name, output_file, model_label in models:
    print(f"Iniciando análise do vídeo completo com {model_label}...")
    raw_analysis = analyze_full_video(video_input, model_name, output_file)

    # --- 2. Salvamento do Relatório ---
    report_content = (
        f"# Análise de Gameplay de Valorant - {model_label}\n\n"
        f"Este relatório contém uma análise detalhada do vídeo de gameplay fornecido, gerada automaticamente pelo modelo {model_label}.\n\n"
        f"{' '.join(raw_analysis)}"
    )

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Relatório de dicas salvo em: {output_file}")
    except Exception as e:
        print(f"Falha ao salvar relatório para {model_label}: {str(e)}")

print("✅ Análise concluída para todos os modelos.")