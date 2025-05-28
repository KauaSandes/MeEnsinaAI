import subprocess
import os
import sys

def ffmpeg_esta_instalado():
    """Verifica se o FFmpeg está instalado e acessível no sistema."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

# Verificação no início do programa
if not ffmpeg_esta_instalado():
    print("❌ FFmpeg não encontrado. Soluções:")
    print("1. Baixe em https://ffmpeg.org/")
    print("2. Adicione ao PATH do sistema")
    print("3. Ou coloque o ffmpeg.exe na mesma pasta do seu script")
    sys.exit(1)