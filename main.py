import os
from datetime import datetime
import warnings
import torch
from transformers import AutoTokenizer, AutoModel
from decord import VideoReader, cpu
import numpy as np
import torchvision.transforms as T

# Suprimir avisos para saída mais limpa
warnings.filterwarnings("ignore")

"""Analisador de Gameplay usando Hugging Face - InternVideo2_5_Chat_8B"""

# Nome do vídeo de gameplay
video_input = "gameplay_valorant.mp4"
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
tips_file = f"gameplay_tips_internvideo_{timestamp}.md"

HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL_ID = "OpenGVLab/InternVideo2_5_Chat_8B"

def is_gpu_available():
    return torch.cuda.is_available()

def select_dtype_for_device():
    if is_gpu_available():
        if torch.cuda.is_bf16_supported():
            return torch.bfloat16
        return torch.float16
    return torch.float32

def load_model_and_tokenizer():
    """Carrega o tokenizer e o modelo InternVideo2_5_Chat_8B.

    Observação: este modelo é grande (8B) e requer GPU. Em CPU, não é viável.
    """
    if not is_gpu_available():
        raise RuntimeError("GPU não encontrada. Este modelo requer GPU com CUDA.")

    dtype = select_dtype_for_device()

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        use_fast=False,
        token=HF_TOKEN or None,
    )

    model = AutoModel.from_pretrained(
        MODEL_ID,
        torch_dtype=dtype,
        trust_remote_code=True,
        token=HF_TOKEN or None,
    ).cuda()

    return tokenizer, model

def validate_video_file(video_path):
    """Validação do arquivo de vídeo"""
    if not os.path.exists(video_path):
        print(f"Vídeo não encontrado: {video_path}")
        return False
    if not video_path.lower().endswith('.mp4'):
        print(f"Formato inválido: O arquivo deve ser .mp4")
        return False
    # (Opcional) verificar tamanho e avisar, sem bloquear
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb > 500:
        print(f"Aviso: arquivo grande ({file_size_mb:.2f} MB). A inferência pode ser lenta/usar muita VRAM.")
    return True

def _compute_frame_indices(num_frames, num_segments):
    seg_size = float(num_frames - 1) / num_segments
    start = int(seg_size / 2)
    offsets = [start + int(round(seg_size * idx)) for idx in range(num_segments)]
    return np.array(offsets)

def load_video_tensor(video_path, num_segments=8, resolution=224):
    """Carrega amostras de frames do vídeo e retorna tensor pronto para o modelo."""
    vr = VideoReader(video_path, ctx=cpu(0), num_threads=1)
    num_frames = len(vr)
    frame_indices = _compute_frame_indices(num_frames, num_segments)

    transform = T.Compose([
        T.Resize((resolution, resolution)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    frames_np = vr.get_batch(frame_indices).asnumpy()
    frames_tensor = torch.stack([transform(frame) for frame in frames_np]).unsqueeze(0)
    return frames_tensor

def analyze_video_with_internvideo(video_path):
    """Análise do vídeo usando o modelo InternVideo2_5_Chat_8B (Hugging Face)."""
    if not validate_video_file(video_path):
        return ["Erro: Arquivo de vídeo inválido ou não encontrado"]

    try:
        print("Iniciando análise com o modelo InternVideo2_5_Chat_8B...")
        
        # Prompt em português para análise de gameplay de Valorant
        prompt = """
        Você é um analista especialista em Valorant e coach de e-sports. Sua tarefa é analisar este vídeo de gameplay de Valorant, focando na perspectiva do jogador principal, para identificar erros específicos e fornecer dicas construtivas e acionáveis para ajudá-lo a melhorar.

        **Instruções Detalhadas para Análise:**
        Por favor, analise os seguintes aspectos da gameplay e forneça feedback detalhado:

        1. **Posicionamento de Mira (Crosshair Placement):**
           * A mira está consistentemente na altura da cabeça dos oponentes?
           * Está pré-posicionada em ângulos comuns, passagens e pontos de contato esperados?
           * Há algum momento em que a mira está mal posicionada?
           * A mira acompanha o movimento do jogador de forma fluida?

        2. **Movimentação e Posicionamento no Mapa:**
           * O jogador está utilizando ângulos vantajosos?
           * Como está a movimentação durante trocações?
           * O jogador está utilizando cover de forma eficaz?
           * Há momentos de hesitação ou posicionamento inadequado?

        3. **Rotações e Consciência de Mapa:**
           * As rotações foram feitas no tempo correto?
           * O jogador parece antecipar movimentações inimigas?
           * Houve falha em rotacionar ou dar suporte a áreas críticas?

        4. **Uso de Habilidades e Utilitários:**
           * Identifique o agente sendo jogado
           * As habilidades foram usadas corretamente para cada situação?
           * O timing do uso foi adequado?
           * Houve momentos onde habilidades poderiam ter sido usadas melhor?

        5. **Noção de Jogo e Tomada de Decisão:**
           * As decisões fazem sentido tático?
           * O jogador demonstrou compreensão dos objetivos?
           * Como reagiu a informações novas?
           * Os engajamentos foram bem escolhidos?

        **Formato da Resposta:**
        * Seja claro e objetivo
        * Organize por categorias
        * Forneça exemplos específicos com timestamps quando possível
        * Dê dicas acionáveis e construtivas
        * Priorize as áreas mais críticas para melhoria

        Analise este vídeo de gameplay de Valorant e forneça seu feedback detalhado em português.
        """

        # Carrega modelo/tokenizer
        tokenizer, model = load_model_and_tokenizer()

        # Prepara vídeo
        video_tensor = load_video_tensor(video_path).to(model.device)

        # Executa chat
        chat_history = []
        response, chat_history = model.chat(
            tokenizer,
            "",
            prompt,
            media_type="video",
            media_tensor=video_tensor,
            chat_history=chat_history,
            return_history=True,
            generation_config={"do_sample": False}
        )

        print("Análise concluída com sucesso!")
        return [response] if response else ["Modelo retornou resposta vazia"]

    except Exception as e:
        error_msg = f"Erro durante a análise: {str(e)}"
        print(error_msg)
        return [error_msg]

def save_analysis_report(analysis_results, output_file):
    """Salva o relatório de análise em um arquivo Markdown"""
    try:
        report_content = (
            f"# Análise de Gameplay de Valorant - InternVideo2_5_Chat_8B\n\n"
            f"**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            f"**Vídeo Analisado:** {video_input}\n\n"
            f"## Análise Detalhada\n\n"
        )
        
        # Adicionar cada resultado da análise
        for i, result in enumerate(analysis_results, 1):
            report_content += f"{result}\n\n"
        
        # Adicionar rodapé
        report_content += (
            f"---\n\n"
            f"*Este relatório foi gerado automaticamente pelo modelo InternVideo2_5_Chat_8B (Hugging Face).*\n"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Relatório salvo com sucesso em: {output_file}")
        return True

    except Exception as e:
        print(f"Erro ao salvar relatório: {str(e)}")
        return False

def main():
    """Função principal do programa"""
    print("=== Analisador de Gameplay Valorant com InternVideo2_5_Chat_8B ===")
    print(f"Vídeo a ser analisado: {video_input}")
    print(f"Arquivo de saída: {tips_file}")
    print("-" * 60)

    # Avisos de ambiente
    if not is_gpu_available():
        print("  ERRO: GPU não detectada. Este modelo requer GPU com CUDA para rodar.")
        print("  Instale drivers CUDA/cuDNN e PyTorch com suporte a CUDA ou use uma máquina com GPU.")
        return

    if not HF_TOKEN:
        print("  Aviso: variável HF_TOKEN não definida. Prosseguindo sem token (modelo público).")

    # Analisar o vídeo
    print(" Iniciando análise do vídeo...")
    analysis_results = analyze_video_with_internvideo(video_input)

    if analysis_results and not analysis_results[0].startswith("Erro"):
        # Salvar o relatório
        print(" Salvando relatório...")
        if save_analysis_report(analysis_results, tips_file):
            print(" Análise concluída com sucesso!")
            print(f" Relatório salvo em: {tips_file}")
        else:
            print(" Falha ao salvar o relatório")
    else:
        print(" Análise falhou. Verifique os erros acima.")

if __name__ == "__main__":
    main()