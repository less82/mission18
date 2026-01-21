# 🎬 영화 리뷰 감성 분석 시스템

KcELECTRA 모델을 활용한 실시간 영화 리뷰 감성 분석 시스템

## 🚀 빠른 시작

### 사전 요구사항
- Docker Desktop 설치
- Git 설치

### 실행 방법
```bash
# 1. 저장소 클론
git clone https://github.com/your-username/movie-review-system.git
cd movie-review-system

# 2. Docker Compose로 전체 시스템 실행
docker-compose up --build

# 3. 브라우저에서 접속
# - Frontend: http://localhost:8501
# - Backend API: http://localhost:8000/docs
```

### 중지
```bash
docker-compose down
```

## 🏗️ 시스템 구조
```
Frontend (Streamlit) → Backend (FastAPI) → Database (PostgreSQL)
                              ↓
                        AI Model (KcELECTRA)
```

## 📊 주요 기능

- ✅ 영화 등록/조회/삭제
- ✅ 리뷰 작성 시 실시간 감성 분석
- ✅ 영화별 평균 평점 자동 계산
- ✅ 모델 경량화 (양자화 + 캐싱)

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: PostgreSQL
- **AI Model**: KcELECTRA (beomi/KcELECTRA-base-v2022)
- **Containerization**: Docker, Docker Compose

## 👨‍💻 개발자

오현민 | 코드잇 스프린트 AI 엔지니어 5기