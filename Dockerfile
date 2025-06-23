# 1. Base image with Python
FROM python:3.11-slim

# 2. Working directory
WORKDIR /app

# 3. Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy source code
COPY src/ src/

EXPOSE 8501

# 5. Default command
CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
