from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import glob
from datetime import datetime
import markdown
import bleach
import json

app = Flask(__name__)

def get_markdown_files(game_filter=None):
    """Obtém todos os arquivos markdown no diretório com filtro opcional por jogo"""
    md_files = {
        'sinteses': [],
        'analises': []
    }
    
    try:
        print("Procurando arquivos markdown...")
        current_dir = os.getcwd()
        print(f"Diretório atual: {current_dir}")
        
        for file in glob.glob("*.md"):
            try:
                print(f"\nProcessando arquivo: {file}")
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"Conteúdo lido: {len(content)} caracteres")
                    
                    # Determina o tipo de jogo e ícone
                    game_type = 'CS2' if 'CS2' in file else 'SF6' if 'SF6' in file else 'Other'
                    game_icon = '🎯' if game_type == 'CS2' else '🥋' if game_type == 'SF6' else '🎮'
                    print(f"Tipo de jogo: {game_type}, Ícone: {game_icon}")
                    
                    # Se houver filtro por jogo, pula arquivos que não correspondem
                    if game_filter and game_filter.lower() != game_type.lower():
                        print(f"Arquivo ignorado devido ao filtro: {game_filter}")
                        continue
                    
                    file_info = {
                        'filename': file,
                        'game_type': game_type,
                        'game_icon': game_icon,
                        'date': datetime.fromtimestamp(os.path.getctime(file)).strftime('%Y-%m-%d %H:%M:%S'),
                        'content': content
                    }
                    print(f"Info do arquivo criada: {file_info['filename']}, {file_info['date']}")
                    
                    # Categoriza o arquivo baseado no nome
                    if 'SINTESE' in file.upper():
                        print("Categorizado como síntese")
                        md_files['sinteses'].append(file_info)
                    else:
                        print("Categorizado como análise")
                        md_files['analises'].append(file_info)
            except Exception as e:
                print(f"Erro ao processar arquivo {file}: {str(e)}")
                continue
        
        # Ordena cada lista por data
        for category in ['sinteses', 'analises']:
            md_files[category] = sorted(
                md_files[category],
                key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'),
                reverse=True
            )
            print(f"\nArquivos em {category}: {len(md_files[category])}")
        
    except Exception as e:
        print(f"Erro ao listar arquivos: {str(e)}")
        return {'sinteses': [], 'analises': []}
    
    return md_files

@app.route('/')
def index():
    """Rota principal que renderiza o template"""
    return render_template('viewer.html')

@app.route('/api/files')
def get_files():
    """API para listar arquivos markdown com suporte a filtro por jogo"""
    try:
        game = request.args.get('game', None)
        print(f"\nRequisição de arquivos recebida. Filtro de jogo: {game}")
        files = get_markdown_files(game)
        print(f"Total de arquivos encontrados: {len(files['sinteses']) + len(files['analises'])}")
        return jsonify(files)
    except Exception as e:
        print(f"Erro na API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 