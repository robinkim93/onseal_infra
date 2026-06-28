FROM python:3.11.15-slim

COPY requirements.txt /app/requirements.txt

# 1) torch는 CPU 전용 인덱스에서 먼저 설치 (GPU/CUDA 빌드 선점 방지 — 에어갭 이미지 경량화)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2) 나머지 의존성 — torch는 이미 설치되어 다시 받지 않음
RUN pip install --no-cache-dir -r /app/requirements.txt

# 모델 가중치(bge-m3)는 이미지에 굽지 않는다 — PVC(/models)에 한 번 적재해두고
# 런타임에 HF_HOME=/models + HF_HUB_OFFLINE=1 로 오프라인 로드. (코드/모델 변경빈도 분리)
COPY app /app/app

WORKDIR /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]