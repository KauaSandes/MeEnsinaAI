# Analisador de Gameplay Valorant com CogVLM2-Video

Este programa analisa vídeos de gameplay de Valorant usando o modelo de IA CogVLM2-Video do Replicate para fornecer feedback detalhado e dicas de melhoria.

## 🚀 Funcionalidades

- **Análise Automática**: Analisa vídeos de gameplay usando IA avançada
- **Feedback Detalhado**: Fornece análise em 5 categorias principais:
  - Posicionamento de Mira (Crosshair Placement)
  - Movimentação e Posicionamento no Mapa
  - Rotações e Consciência de Mapa
  - Uso de Habilidades e Utilitários
  - Noção de Jogo e Tomada de Decisão
- **Relatórios em Markdown**: Gera relatórios estruturados e fáceis de ler
- **Suporte a Vídeos Locais**: Aceita arquivos MP4 locais

## 📋 Pré-requisitos

- Python 3.7 ou superior
- Token da API do Replicate
- Arquivo de vídeo MP4 para análise

## 🛠️ Instalação

1. **Clone ou baixe o projeto**
2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure sua chave da API do Replicate:**
   
   **Opção 1 - Variável de ambiente (Recomendado):**
   ```bash
   # Windows (PowerShell)
   $env:REPLICATE_API_TOKEN="seu_token_aqui"
   
   # Windows (CMD)
   set REPLICATE_API_TOKEN=seu_token_aqui
   
   # Linux/Mac
   export REPLICATE_API_TOKEN="seu_token_aqui"
   ```
   
   **Opção 2 - Editar o código:**
   Edite o arquivo `main.py` e substitua a linha:
   ```python
   REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
   ```
   Por:
   ```python
   REPLICATE_API_TOKEN = "seu_token_aqui"
   ```

## 🔑 Como obter o Token da API do Replicate

1. Acesse [replicate.com](https://replicate.com)
2. Crie uma conta ou faça login
3. Vá para [Account Settings](https://replicate.com/account)
4. Copie sua API Token

## 📁 Preparando o Vídeo

1. **Formato**: O vídeo deve estar em formato MP4
2. **Tamanho**: Recomendado até 100 MB (o programa verificará automaticamente)
3. **Nome**: Por padrão, o programa procura por `fds.mp4`
4. **Localização**: Coloque o vídeo na mesma pasta do programa

## 🎯 Como Usar

1. **Coloque seu vídeo na pasta do projeto** (ou edite a variável `video_input` no código)
2. **Execute o programa:**
   ```bash
   python main.py
   ```
3. **Aguarde a análise** (pode levar alguns minutos dependendo do tamanho do vídeo)
4. **Verifique o relatório gerado** no arquivo `gameplay_tips_cogvlm2_YYYYMMDD_HHMMSS.md`

## 📊 Exemplo de Saída

O programa gera um relatório em Markdown com:
- Data e hora da análise
- Nome do vídeo analisado
- Análise detalhada por categoria
- Dicas específicas e acionáveis
- Sugestões de melhoria priorizadas

## ⚠️ Limitações e Considerações

- **Tamanho do vídeo**: Máximo recomendado de 100 MB
- **Formato**: Apenas MP4 é suportado
- **Tempo de análise**: Depende do tamanho do vídeo e da API do Replicate
- **Custo**: O uso da API do Replicate pode gerar custos (verifique os preços em replicate.com)

## 🐛 Solução de Problemas

### "Token da API não encontrado"
- Verifique se a variável `REPLICATE_API_TOKEN` está configurada
- Teste com `echo $env:REPLICATE_API_TOKEN` (PowerShell) ou `echo $REPLICATE_API_TOKEN` (Linux/Mac)

### "Vídeo não encontrado"
- Verifique se o arquivo está na pasta correta
- Confirme se o nome do arquivo está correto
- Verifique se a extensão é `.mp4`

### "Arquivo muito grande"
- Comprima o vídeo para reduzir o tamanho
- Use ferramentas como HandBrake ou FFmpeg

### Erros de API
- Verifique se seu token está válido
- Confirme se você tem créditos suficientes na conta do Replicate
- Verifique a conectividade com a internet

## 🔧 Personalização

### Alterar o nome do vídeo
Edite a variável `video_input` no início do arquivo `main.py`:
```python
video_input = "seu_video.mp4"
```

### Modificar o prompt de análise
Edite a variável `prompt` na função `analyze_video_with_cogvlm2` para personalizar o tipo de análise.

### Ajustar parâmetros do modelo
Modifique os parâmetros na chamada da API:
```python
"top_p": 0.1,           # Controle de criatividade
"temperature": 0.3,      # Temperatura da resposta
"max_new_tokens": 2048   # Máximo de tokens na resposta
```

## 📞 Suporte

Para problemas relacionados à API do Replicate, consulte a [documentação oficial](https://replicate.com/docs).

## 📄 Licença

Este projeto é de uso pessoal e educacional.
