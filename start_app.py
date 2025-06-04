import subprocess
import sys
import os

# --- Configurações do seu Projeto ---
# Nome da pasta do ambiente virtual que será criada/usada
VENV_NAME = ".venv"
# Nome do arquivo de dependências (requirements.txt)
REQUIREMENTS_FILE = "requirements.txt"
# Nome do seu arquivo principal do Streamlit
MAIN_APP_FILE = "main_app.py"
# ------------------------------------

def run_command(command, cwd=None, shell=True):
    """
    Executa um comando no shell e exibe a saída em tempo real.
    Garante que erros sejam mostrados claramente.
    """
    print(f"\n--- Executando: {command} ---")
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=shell,
            check=True,  # Levanta um erro se o comando retornar um código de saída diferente de zero
            capture_output=False, # Permite que a saída seja exibida diretamente no terminal
            text=True,
            encoding='utf-8'
        )
        print(f"--- Comando '{command.split(' ')[0]}' concluído com sucesso ---")
        return process.returncode
    except subprocess.CalledProcessError as e:
        print(f"ERRO: Comando '{command}' falhou com código {e.returncode}")
        if e.stdout:
            print(f"Stdout:\n{e.stdout}")
        if e.stderr:
            print(f"Stderr:\n{e.stderr}")
        sys.exit(1) # Sai do script se houver um erro

def main():
    # Caminho absoluto para a raiz do seu projeto
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(project_root, VENV_NAME)

    print(f"Verificando/Configurando ambiente virtual em: {venv_path}")

    # 1. Verificar e criar o ambiente virtual, se necessário
    if not os.path.exists(venv_path):
        print(f"Ambiente virtual '{VENV_NAME}' não encontrado. Criando...")
        # Usa o python do sistema para criar o ambiente virtual
        run_command(f"{sys.executable} -m venv {VENV_NAME}", cwd=project_root)
        print(f"Ambiente virtual '{VENV_NAME}' criado com sucesso.")
    else:
        print(f"Ambiente virtual '{VENV_NAME}' já existe. Usando o existente.")

    # 2. Definir os caminhos para os executáveis dentro do ambiente virtual
    if sys.platform == "win32": # Sistema Operacional Windows
        python_executable_venv = os.path.join(venv_path, "Scripts", "python.exe")
        pip_executable_venv = os.path.join(venv_path, "Scripts", "pip.exe")
        # --- AQUI ESTÁ A CHAVE PARA O PROBLEMA DO PATH ---
        # Adiciona o diretório 'Scripts' do venv ao PATH da sessão atual
        # Isso permite que comandos como 'pip' e 'streamlit' sejam encontrados diretamente
        os.environ["PATH"] = os.path.join(venv_path, "Scripts") + os.pathsep + os.environ.get("PATH", "")
        # --------------------------------------------------
    else: # Sistemas Operacionais baseados em Unix (Linux, macOS)
        python_executable_venv = os.path.join(venv_path, "bin", "python")
        pip_executable_venv = os.path.join(venv_path, "bin", "pip")
        # --- AQUI ESTÁ A CHAVE PARA O PROBLEMA DO PATH ---
        # Adiciona o diretório 'bin' do venv ao PATH da sessão atual
        os.environ["PATH"] = os.path.join(venv_path, "bin") + os.pathsep + os.environ.get("PATH", "")
        # --------------------------------------------------

    # 3. Instalar ou atualizar as dependências usando o pip do ambiente virtual
    print(f"\nInstalando/Atualizando dependências de '{REQUIREMENTS_FILE}'...")
    # Usamos 'pip' diretamente porque o PATH foi ajustado nas linhas anteriores
    run_command(f'"{pip_executable_venv}" install -r "{REQUIREMENTS_FILE}"', cwd=project_root)
    print("Dependências instaladas/atualizadas com sucesso.")

    # 4. Iniciar o aplicativo Streamlit
    print(f"\nIniciando o aplicativo Streamlit: '{MAIN_APP_FILE}'...")
    # O Streamlit é executado através do Python do ambiente virtual,
    # usando a sintaxe "-m streamlit" que é a forma mais robusta e confiável
    run_command(f'"{python_executable_venv}" -m streamlit run "{MAIN_APP_FILE}"', cwd=project_root)

if __name__ == "__main__":
    main()
