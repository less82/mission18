# 🎬 영화 리뷰 시스템 (Movie Review System)

FastAPI + Streamlit + AI 감성 분석 기반 영화 리뷰 플랫폼

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-green)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.53.0-red)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📌 **주요 기능**

- 🎥 **영화 등록 및 관리** - 포스터, 감독, 장르 등 상세 정보
- ✍️ **리뷰 작성** - 사용자 리뷰 등록
- 🤖 **AI 감성 분석** - KcELECTRA 모델 기반 자동 감성 분석 (긍정/부정/중립)
- ⭐ **평균 평점** - 영화별 감성 분석 점수 평균 표시
- 📊 **실시간 대시보드** - Streamlit 기반 사용자 친화적 UI
- 🗄️ **PostgreSQL 데이터베이스** - 안정적인 데이터 관리
- ☁️ **클라우드 배포** - Render.com 무료 배포 지원

---

## 🚀 **빠른 시작**

### **방법 1: Docker Compose** (추천)

```bash
# 저장소 클론
git clone https://github.com/[YOUR_USERNAME]/mission18.git
cd mission18

# Docker Compose 실행
docker-compose up --build

# 접속
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### **방법 2: 로컬 실행**

#### Backend

```bash
cd backend
pip install -r requirements.txt
pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
python backend.py
```

#### Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run frontend.py
```

---

## 📂 **프로젝트 구조**

```
mission18/
├── backend/
│   ├── backend.py              # FastAPI 애플리케이션
│   ├── requirements.txt        # Backend 의존성
│   └── Dockerfile
│
├── frontend/
│   ├── frontend.py             # Streamlit 애플리케이션
│   ├── requirements.txt        # Frontend 의존성
│   └── Dockerfile
│
├── docker-compose.yml          # Docker Compose 설정
├── render.yaml                 # Render.com 배포 설정
├── .gitignore
└── README.md
```

---

## 🛠 **기술 스택**

### Backend
- **FastAPI 0.128.0** - 고성능 Python 웹 프레임워크
- **psycopg 3.2.6** - PostgreSQL 데이터베이스 어댑터 (psycopg2보다 2배 빠름)
- **SQLAlchemy 2.0.45** - ORM
- **Transformers 4.57.6** - Hugging Face 모델
- **PyTorch 2.9.1 (CPU)** - 딥러닝 프레임워크
- **KcELECTRA** - 한국어 감성 분석 모델

### Frontend
- **Streamlit 1.53.0** - 데이터 앱 프레임워크
- **Requests 2.32.3** - HTTP 라이브러리

### Database
- **PostgreSQL 16** - 관계형 데이터베이스

### Deployment
- **Docker** - 컨테이너화
- **Render.com** - 클라우드 플랫폼 (무료)

---

## 🎯 **API 엔드포인트**

### 영화 (Movies)
```
POST   /movies          # 영화 등록
GET    /movies          # 전체 영화 목록
GET    /movies/{id}     # 특정 영화 조회
DELETE /movies/{id}     # 영화 삭제
```

### 리뷰 (Reviews)
```
POST   /reviews              # 리뷰 등록 (자동 감성 분석)
GET    /reviews?limit=10     # 최근 리뷰 조회
GET    /movies/{id}/reviews  # 특정 영화 리뷰
DELETE /reviews/{id}         # 리뷰 삭제
```

### 헬스 체크
```
GET    /                # API 상태
GET    /health          # DB 연결 확인
```

---

## 🤖 **AI 감성 분석**

### 사용 모델
- **beomi/KcELECTRA-base-v2022**
- 한국어 특화 ELECTRA 모델
- 긍정/부정 분류

### 경량화
- **INT8 Quantization** (CPU)
- **Float16** (GPU)
- 메모리 사용량 50% 절감

### 성능
- 캐싱 적용 (LRU Cache)
- 빠른 추론 속도

---

## ☁️ **배포 (Render.com)**

### 무료 배포 가능!

자세한 배포 가이드: [RENDER_DEPLOY_GUIDE.md](RENDER_DEPLOY_GUIDE.md)

**간단 요약:**
1. GitHub에 코드 업로드
2. Render.com에서 PostgreSQL 생성
3. Backend Web Service 생성
4. Frontend Web Service 생성
5. 완료! 🎉

**배포 URL 예시:**
```
Frontend: https://movie-review-frontend.onrender.com
Backend: https://movie-review-backend.onrender.com
API Docs: https://movie-review-backend.onrender.com/docs
```

---

## 📸 **스크린샷**

### 메인 화면
![Main](screenshots/main.png)

### 영화 등록
![Add Movie](screenshots/add-movie.png)

### 리뷰 작성 & 감성 분석
![Review](screenshots/review.png)

---

## 🔧 **환경 변수**

### Backend
```env
ENV=production
DATABASE_URL=postgresql://user:password@host:5432/dbname
PYTHON_VERSION=3.11.0
```

### Frontend
```env
BACKEND_URL=https://movie-review-backend.onrender.com
```

---

## 🐛 **트러블슈팅**

### Docker Build 오류
[ERROR_FIX_GUIDE.md](ERROR_FIX_GUIDE.md) 참고

### Render.com 배포 오류
[RENDER_DEPLOY_GUIDE.md](RENDER_DEPLOY_GUIDE.md) 참고

---

## 📝 **라이센스**

MIT License

---

## 👥 **기여**

Pull Request 환영합니다!

1. Fork
2. Feature Branch 생성 (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add: Amazing Feature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

---

## 📧 **연락처**

프로젝트 링크: [https://github.com/less82/mission18](https://github.com/less82/mission18)

---

## 🙏 **감사의 말**

- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://streamlit.io/)
- [Hugging Face](https://huggingface.co/)
- [Render.com](https://render.com/)
- [beomi/KcELECTRA](https://github.com/Beomi/KcELECTRA)

---

**⭐ 이 프로젝트가 도움이 되셨다면 Star를 눌러주세요!**