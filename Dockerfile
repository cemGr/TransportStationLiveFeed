# 1. Basis-Image mit Python
FROM python:3.11-slim

# 2. Arbeitsverzeichnis
WORKDIR /app

# 3. Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Quellcode kopieren
COPY src/ src/

EXPOSE 8501

# 5. Default-Command
CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
