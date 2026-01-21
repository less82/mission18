# Python 3.11 기반
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY frontend.py .

# 포트 노출
EXPOSE 8501

# Streamlit 실행
CMD ["streamlit", "run", "frontend.py", "--server.address", "0.0.0.0"]