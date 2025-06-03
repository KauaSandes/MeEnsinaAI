#!/usr/bin/env python3
"""
Script de inicialização para Me Ensina A.I
Automatiza a configuração e execução da aplicação no VS Code
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ é necessário. Versão atual:", sys.version)
        return False
    print("✅ Python", sys.version.split()[0], "detectado")
    return True

def check_venv():
    """Verifica e cria ambiente virtual se necessário"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("📦 Criando ambiente virtual...")
        subprocess.run([sys.executable, "-m", "venv", "venv"])
        print("✅ Ambiente virtual criado")
    else:
        print("✅ Ambiente virtual encontrado")
    
    # Detectar sistema operacional e ativar venv
    if platform.system() == "Windows":
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"
    
    return python_path, pip_path

def install_dependencies(pip_path):
    """Instala dependências necessárias"""
    dependencies = [
        "streamlit>=1.28.0",
        "requests>=2.31.0", 
        "tenacity>=8.2.0"
    ]
    
    print("📦 Instalando dependências...")
    for dep in dependencies:
        try:
            subprocess.run([str(pip_path), "install", dep], check=True, capture_output=True)
            print(f"✅ {dep.split('>=')[0]} instalado")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar {dep}: {e}")
            return False
    
    return True

def check_app_file():
    """Verifica se o arquivo principal existe"""
    app_file = Path("gameplay_analyzer_app.py")
    if not app_file.exists():
        print("❌ Arquivo 'gameplay_analyzer_app.py' não encontrado!")
        print("💡 Certifique-se de que o arquivo está na mesma pasta que este script.")
        return False
    print("✅ Arquivo principal encontrado")
    return True

def run_streamlit(python_path):
    """Executa a aplicação Streamlit"""
    print("\n🚀 Iniciando Me Ensina A.I...")
    print("📱 A aplicação abrirá em: http://localhost:8501")
    print("⏹️  Para parar: Ctrl+C no terminal\n")
    
    try:
        subprocess.run([
            str(python_path), "-m", "streamlit", "run", "gameplay_analyzer_app.py",
            "--server.headless", "false",
            "--server.runOnSave", "true"
        ])
    except KeyboardInterrupt:
        print("\n👋 Aplicação encerrada pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao executar aplicação: {e}")

def main():
    """Função principal"""
    print("🎮 Me Ensina A.I - Configuração Automática")
    print("=" * 50)
    
    # Verificações
    if not check_python_version():
        return
    
    python_path, pip_path = check_venv()
    
    if not install_dependencies(pip_path):
        print("❌ Falha na instalação de dependências")
        return
    
    if not check_app_file():
        return
    
    print("\n✅ Configuração concluída com sucesso!")
    print("=" * 50)
    
    # Executar aplicação
    run_streamlit(python_path)

if __name__ == "__main__":
    main()