# 1. Base image
FROM python:3.11-slim

# 2. Working directory
WORKDIR /app

# 3. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application source
COPY src/ src/

EXPOSE 8501

# 5. Default command
CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
