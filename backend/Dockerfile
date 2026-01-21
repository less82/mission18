# Python 3.11 기반
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사
COPY requirements.txt .

# pip 업그레이드
RUN pip install --no-cache-dir --upgrade pip

# 1단계: 일반 패키지 설치 (PyPI에서)
RUN pip install --no-cache-dir -r requirements.txt

# 2단계: torch CPU 버전 별도 설치 (PyTorch 저장소에서)
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu

# 애플리케이션 코드 복사
COPY backend.py .

# 모델 캐시 디렉토리 생성
RUN mkdir -p /app/model_cache

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# 포트 노출
EXPOSE 8000

# 헬스 체크 (선택사항)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 서버 실행
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
