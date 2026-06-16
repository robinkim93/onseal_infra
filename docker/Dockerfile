FROM python:3.11.15-slim

COPY requirements.txt /app/requirements.txt

# 1) torch는 CPU 전용 인덱스에서 먼저 설치 (GPU/CUDA 빌드 선점 방지 — 에어갭 이미지 경량화)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2) 나머지 의존성 — torch는 이미 설치되어 다시 받지 않음
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

WORKDIR /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]