import requests
import base64
import os
from datetime import datetime
import warnings
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Nome do vídeo de gameplay
video_input = "fds.mp4"  
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
tips_file_grok3 = f"gameplay_tips_grok3_{timestamp}.md"

# Configurações da API
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_GROK3 = "x-ai/grok-2-vision-1212"  # Atualizado para Grok 3

def validate_video_file(video_path):
    """Validação do vídeo"""
    if not os.path.exists(video_path):
        print(f"Vídeo não encontrado: {video_path}")
        return False
    if not video_path.lower().endswith('.mp4'):
        print(f"Formato inválido: O arquivo deve ser .mp4")
        return False
    # Verificar tamanho do arquivo
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb > 50:  # Limite de 50 MB
        print(f"Arquivo muito grande ({file_size_mb:.2f} MB). Considere comprimir o vídeo.")
        return False
    return True

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def make_openrouter_request(url, headers, payload, timeout):
    """Request ao OpenRouter"""
    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def analyze_full_video(video_path, model_name, output_file):
    """Análise do vídeo"""
    if not validate_video_file(video_path):
        return [f"Erro: Arquivo de vídeo inválido ou não encontrado para {model_name}"]

    if not OPENROUTER_API_KEY or len(OPENROUTER_API_KEY) < 20:
        return [f"Erro: Chave de API do OpenRouter inválida ou muito curta para {model_name}"]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # Codificar o vídeo para base64
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()
        base64_video = base64.b64encode(video_data).decode('utf-8')

        prompt = (
            """
            Você é um analista especialista em Valorant e coach de e-sports. Sua tarefa é analisar os frames/clipes de uma gameplay de Valorant, focando na perspectiva do jogador principal, para identificar erros específicos e fornecer dicas construtivas e acionáveis para ajudá-lo a melhorar.
            **Instruções Detalhadas para Análise:**
            Por favor, analise os seguintes aspectos da gameplay e forneça feedback detalhado:
            1. **Posicionamento de Mira (Crosshair Placement):**
                * A mira está consistentemente na altura da cabeça dos oponentes?
                * Está pré-posicionada em ângulos comuns, passagens e pontos de contato esperados?
                * Há algum momento em que a mira está mal posicionada (ex: no chão, muito aberta, muito fechada em relação ao ângulo)?
                * A mira acompanha o movimento do jogador de forma fluida ou parece "atrasada"?
                * **Dica:** Se identificar erros, explique *por que* é um erro e *como* o jogador pode ajustar para um posicionamento ideal naquela situação.
            2. **Movimentação e Posicionamento no Mapa:**
                * O jogador está utilizando ângulos vantajosos? Está se expondo desnecessariamente?
                * Como está a movimentação durante trocações (ex: strafing, counter-strafing)?
                * O jogador está utilizando cover de forma eficaz?
                * Há momentos de hesitação ou posicionamento passivo/agressivo inadequado para a situação?
            3. **Rotações e Consciência de Mapa (Map Awareness):**
                * As rotações foram feitas no tempo correto com base nas informações disponíveis (minimapa, sons, informações de aliados – se inferíveis)?
                * O jogador parece antecipar movimentações inimigas ou objetivos?
                * Houve falha em rotacionar ou em dar suporte a uma área crítica do mapa?
                * **Dica:** Sugira como o jogador poderia ter usado melhor as informações do mapa para tomar decisões de rotação mais eficazes.
            4. **Uso de Habilidades e Utilitários (Específico do Agente):**
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
            5. **Noção de Jogo e Tomada de Decisão (Game Sense):**
                * As decisões tomadas pelo jogador fazem sentido tático considerando o estado do jogo (vantagem/desvantagem numérica, economia, tempo restante)?
                * O jogador demonstrou compreensão dos objetivos do round (plantar/defusar a spike, eliminar todos os inimigos)?
                * Como o jogador reagiu a informações novas (ex: som de passos, habilidade inimiga utilizada, morte de um aliado/inimigo)?
                * Engajamentos: Foram bem escolhidos? O jogador lutou quando deveria recuar ou vice-versa?
                * **Comparativo com Estratégias Profissionais/Alto Elo (Conceitual):**
                    * As jogadas se assemelham a setups, padrões de ataque/defesa ou tomadas de decisão comumente vistas em níveis mais altos de jogo? (Ex: setups de defesa padrão, execuções de ataque coordenadas, como jogar um pós-plant).
                    * Se o jogador cometeu um erro tático, explique qual seria uma abordagem mais estratégica, inspirada em conceitos de jogo de alto nível.
            6. **Outras Dicas e Observações Gerais:**
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
            "max_tokens": 1000  # Reduzido para evitar limites
        }

        response = make_openrouter_request(OPENROUTER_API_URL, headers, payload, timeout=60)
        response.raise_for_status()

        if not response.text:
            return [f"API retornou resposta vazia para {model_name}"]

        data = response.json()
        analysis = data['choices'][0]['message']['content']
        return [analysis]

    except requests.exceptions.HTTPError as http_err:
        return [f"Erro HTTP para {model_name} - {str(http_err)}: {response.text}"]
    except requests.exceptions.ConnectionError as conn_err:
        return [f"Erro de conexão para {model_name} - Verifique sua internet ou DNS ({str(conn_err)})"]
    except requests.exceptions.Timeout:
        return [f"Timeout na conexão com a API para {model_name}"]
    except (KeyError, json.JSONDecodeError):
        return [f"Resposta inválida da API para {model_name}: {response.text[:100]}"]
    except Exception as e:
        return [f"Erro geral para {model_name} - {str(e)}"]

# Análise do vídeo
models = [
    (MODEL_GROK3, tips_file_grok3, "Grok 3"),  # Atualizado para Grok 3
]

for model_name, output_file, model_label in models:
    print(f"Iniciando análise do vídeo completo com {model_label}...")
    raw_analysis = analyze_full_video(video_input, model_name, output_file)

    # Salvamento do relatório
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

print("Análise concluída para todos os modelos.")