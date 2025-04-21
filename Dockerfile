# Usa uma imagem base com Python + Chromium Playwright
FROM mcr.microsoft.com/playwright/python:v1.51.0-jammy

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos para dentro do container
COPY . .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Garante que o navegador vai estar instalado corretamente (não precisa baixar de novo porque a imagem já vem pronta)
RUN playwright install --with-deps

# Comando para rodar o app
CMD ["python", "app.py"]
