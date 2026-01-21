# 🔧 Docker Build 오류 해결 가이드

## ❌ 발생한 오류

```
ERROR: Could not find a version that satisfies the requirement fastapi==0.128.0
ERROR: No matching distribution found for fastapi==0.128.0
```

## 🔍 원인 분석

### 문제점
`requirements.txt`에서 `--index-url` 옵션이 **모든 패키지**에 적용되어, FastAPI를 PyPI가 아닌 PyTorch 저장소에서 찾으려고 시도했습니다.

**문제가 있던 requirements.txt:**
```txt
fastapi==0.128.0
transformers==4.57.6

# 이 줄이 위의 모든 패키지에도 적용됨!
--index-url https://download.pytorch.org/whl/cpu
torch==2.9.1+cpu
```

### 해결 방법
torch만 별도로 설치하도록 **2단계 설치** 방식으로 변경

---

## ✅ 해결 방법 1: 수정된 파일 사용

### 1. **backend/requirements.txt** 교체

```txt
# Core FastAPI
fastapi==0.128.0
uvicorn[standard]==0.34.0
pydantic==2.10.3

# Database - PostgreSQL
psycopg[binary]==3.2.6
sqlalchemy==2.0.45

# 감성분석
transformers==4.57.6

# torch는 Dockerfile에서 별도 설치
```

### 2. **backend/Dockerfile** 교체

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# pip 업그레이드
RUN pip install --no-cache-dir --upgrade pip

# 1단계: 일반 패키지 설치 (PyPI)
RUN pip install --no-cache-dir -r requirements.txt

# 2단계: torch CPU 버전 별도 설치 (PyTorch 저장소)
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu

COPY backend.py .

RUN mkdir -p /app/model_cache

ENV PYTHONUNBUFFERED=1
ENV ENV=production

EXPOSE 8000

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ✅ 해결 방법 2: 수동 수정

### 1. backend/requirements.txt 수정
```bash
# 마지막 2줄 삭제
--index-url https://download.pytorch.org/whl/cpu
torch==2.9.1+cpu
```

### 2. backend/Dockerfile 수정
다음 줄을 추가:
```dockerfile
# 기존 RUN pip install -r requirements.txt 아래에 추가
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
```

---

## 🚀 실행 명령어

### 수정 후 Docker 빌드:
```bash
# 기존 이미지 삭제 (선택사항)
docker-compose down -v

# 새로 빌드
docker-compose up --build
```

---

## 📦 다운로드할 파일

1. **backend_requirements_fixed.txt** → `backend/requirements.txt`
2. **backend_Dockerfile_fixed** → `backend/Dockerfile`

---

## 🎯 빠른 해결 (복사 & 붙여넣기)

### PowerShell에서 실행:
```powershell
# backend 디렉토리로 이동
cd backend

# requirements.txt 백업
Copy-Item requirements.txt requirements.txt.backup

# requirements.txt 수정 (마지막 2줄 삭제)
(Get-Content requirements.txt | Select-Object -SkipLast 2) | Set-Content requirements.txt

# Dockerfile에 torch 설치 추가
$dockerfileContent = Get-Content Dockerfile
$insertIndex = $dockerfileContent.IndexOf("RUN pip install --no-cache-dir -r requirements.txt") + 1
$newLine = "`n# 2단계: torch CPU 버전 별도 설치`nRUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu`n"
$dockerfileContent = $dockerfileContent[0..($insertIndex-1)] + $newLine.Split("`n") + $dockerfileContent[$insertIndex..($dockerfileContent.Count-1)]
$dockerfileContent | Set-Content Dockerfile
```

---

## ✅ 확인 사항

빌드가 성공하면 다음과 같은 메시지가 표시됩니다:

```
✅ 모델 로딩 완료!
✅ 데이터베이스 초기화 완료!
```

---

## 💡 추가 팁

### Render.com 배포 시
Render.com에서는 `requirements.txt`만 사용하므로, 다른 방식이 필요합니다:

**Render.com용 requirements.txt:**
```txt
fastapi==0.128.0
uvicorn[standard]==0.34.0
pydantic==2.10.3
psycopg[binary]==3.2.6
sqlalchemy==2.0.45
transformers==4.57.6

# Render.com에서는 이 방식으로 작동
torch --index-url https://download.pytorch.org/whl/cpu
```

또는 **Build Command** 설정:
```bash
pip install -r requirements.txt && pip install torch --index-url https://download.pytorch.org/whl/cpu
```

---

## 🎉 완료!

이제 `docker-compose up --build` 명령어가 정상 작동할 것입니다!
