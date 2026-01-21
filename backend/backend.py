import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from functools import lru_cache

# 감성 분석 모델
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = FastAPI()

# ========================================
# 환경 변수 설정
# ========================================

# 환경 구분
ENV = os.getenv("ENV", "development")

if ENV == "production":
    # Docker 환경 (환경 변수에서 가져옴)
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    # 로컬 개발 환경
    DATABASE_URL = "postgresql://postgres:admin123@localhost:5432/movie_db"

print(f"🔧 환경: {ENV}")
print(f"🗄️ DB 연결: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Unknown'}")

# ========================================
# 1. 데이터 모델 정의
# ========================================

class Movie(BaseModel):
    id: Optional[int] = None
    title: str
    release_date: str
    director: str
    genre: str
    poster_url: str

class MovieWithRating(BaseModel):
    id: Optional[int] = None
    title: str
    release_date: str
    director: str
    genre: str
    poster_url: str
    review_count: int = 0
    average_rating: Optional[float] = None

class Review(BaseModel):
    id: Optional[int] = None
    movie_id: int
    movie_title: Optional[str] = None
    author: str
    content: str
    sentiment_score: Optional[float] = None
    created_at: Optional[str] = None

class ReviewCreate(BaseModel):
    movie_id: int
    author: str
    content: str

# ========================================
# 2. 감성 분석 모델 로드 + 경량화
# ========================================

# 캐시 디렉토리 설정
CACHE_DIR = "./model_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

print("🤖 감성 분석 모델 로딩 중...")
MODEL_NAME = "beomi/KcELECTRA-base-v2022"

# 토크나이저 로드 (캐싱 적용)
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    cache_dir=CACHE_DIR
)

# 모델 로드 (캐싱 적용)
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2,
    cache_dir=CACHE_DIR
)

# ========================================
# 모델 경량화 (양자화)
# ========================================
print("⚡ 모델 경량화 중...")

if torch.cuda.is_available():
    # GPU 있으면 Float16으로 변환
    model = model.half()
    model = model.cuda()
    print("✅ GPU 모드 (Float16) - 메모리 50% 절감!")
else:
    # CPU에서는 Dynamic Quantization
    model = torch.quantization.quantize_dynamic(
        model,
        {torch.nn.Linear},
        dtype=torch.qint8
    )
    print("✅ CPU 모드 (Int8 Quantization) - 메모리 50% 절감!")

model.eval()
print("✅ 모델 로딩 완료!")

# ========================================
# 감성 분석 함수 (캐싱 적용)
# ========================================

@lru_cache(maxsize=1000)
def analyze_sentiment_cached(text: str) -> float:
    """캐싱된 감성 분석"""
    return analyze_sentiment(text)

def analyze_sentiment(text: str) -> float:
    """
    감성 분석 함수
    Returns: 0.0 ~ 1.0 (0: 부정, 1: 긍정)
    """
    inputs = tokenizer(
        text, 
        return_tensors="pt", 
        truncation=True, 
        max_length=512, 
        padding=True
    )
    
    # GPU 사용 시 입력도 GPU로 이동
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        positive_score = probabilities[0][1].item()
    
    return round(positive_score, 4)

# ========================================
# 3. 데이터베이스 설정
# ========================================

@contextmanager
def get_db_connection():
    """PostgreSQL 연결 Context Manager"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

@app.on_event("startup")
def startup():
    """앱 시작 시 테이블 생성"""
    print("🔌 데이터베이스 연결 확인 중...")
    
    # DB 연결 재시도 로직 (Docker 환경에서 필요)
    import time
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 영화 테이블 생성
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS movies (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        release_date VARCHAR(50),
                        director VARCHAR(255),
                        genre VARCHAR(255),
                        poster_url TEXT
                    )
                ''')
                
                # 리뷰 테이블 생성
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS reviews (
                        id SERIAL PRIMARY KEY,
                        movie_id INTEGER NOT NULL,
                        author VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        sentiment_score FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
                    )
                ''')
                
                conn.commit()
                cursor.close()
            
            print("✅ 데이터베이스 초기화 완료!")
            break
            
        except psycopg2.OperationalError as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"❌ DB 연결 실패: {e}")
                raise
            print(f"⏳ DB 연결 대기 중... ({retry_count}/{max_retries})")
            time.sleep(2)

# ========================================
# 4. 영화 API
# ========================================

@app.post("/movies", response_model=Movie)
def create_movie(movie: Movie):
    """영화 등록"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO movies (title, release_date, director, genre, poster_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (movie.title, movie.release_date, movie.director, movie.genre, movie.poster_url))
        
        movie.id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
    
    return movie

@app.get("/movies", response_model=List[MovieWithRating])
def get_movies():
    """전체 영화 목록 조회"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                m.id,
                m.title,
                m.release_date,
                m.director,
                m.genre,
                m.poster_url,
                COUNT(r.id) as review_count,
                AVG(r.sentiment_score) as average_rating
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            GROUP BY m.id, m.title, m.release_date, m.director, m.genre, m.poster_url
            ORDER BY m.id DESC
        ''')
        
        rows = cursor.fetchall()
        cursor.close()
    
    return [dict(row) for row in rows]

@app.get("/movies/{movie_id}", response_model=MovieWithRating)
def get_movie(movie_id: int):
    """특정 영화 상세 조회"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                m.id,
                m.title,
                m.release_date,
                m.director,
                m.genre,
                m.poster_url,
                COUNT(r.id) as review_count,
                AVG(r.sentiment_score) as average_rating
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            WHERE m.id = %s
            GROUP BY m.id, m.title, m.release_date, m.director, m.genre, m.poster_url
        ''', (movie_id,))
        
        row = cursor.fetchone()
        cursor.close()
    
    if row is None:
        raise HTTPException(status_code=404, detail="영화를 찾을 수 없습니다.")
    
    return dict(row)

@app.delete("/movies/{movie_id}")
def delete_movie(movie_id: int):
    """영화 삭제"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
        
        if cursor.fetchone() is None:
            cursor.close()
            raise HTTPException(status_code=404, detail="삭제할 영화가 없습니다.")
        
        cursor.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
        conn.commit()
        cursor.close()
    
    return {"message": "삭제 성공"}

# ========================================
# 5. 리뷰 API
# ========================================

@app.post("/reviews", response_model=Review)
def create_review(review: ReviewCreate):
    """리뷰 등록 + 자동 감성 분석"""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # 1. 영화 존재 여부 확인
            cursor.execute("SELECT * FROM movies WHERE id = %s", (review.movie_id,))
            movie = cursor.fetchone()
            
            if movie is None:
                raise HTTPException(status_code=404, detail="영화를 찾을 수 없습니다.")
            
            # 2. 감성 분석 실행 (캐싱!)
            sentiment_score = analyze_sentiment_cached(review.content)
            
            # 3. 리뷰 저장
            cursor.execute('''
                INSERT INTO reviews (movie_id, author, content, sentiment_score)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (review.movie_id, review.author, review.content, sentiment_score))
            
            review_id = cursor.fetchone()['id']
            conn.commit()
            
            # 4. 저장된 리뷰 조회
            cursor.execute('''
                SELECT r.*, m.title as movie_title
                FROM reviews r
                JOIN movies m ON r.movie_id = m.id
                WHERE r.id = %s
            ''', (review_id,))
            
            row = cursor.fetchone()
            
            return dict(row)
            
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
        finally:
            cursor.close()

@app.get("/reviews", response_model=List[Review])
def get_all_reviews(limit: int = 10):
    """최근 리뷰 조회"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.*, m.title as movie_title
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id
            ORDER BY r.created_at DESC 
            LIMIT %s
        ''', (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
    
    return [dict(row) for row in rows]

@app.get("/movies/{movie_id}/reviews", response_model=List[Review])
def get_movie_reviews(movie_id: int):
    """특정 영화의 리뷰 조회"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.*, m.title as movie_title
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id
            WHERE r.movie_id = %s
            ORDER BY r.created_at DESC
        ''', (movie_id,))
        
        rows = cursor.fetchall()
        cursor.close()
    
    return [dict(row) for row in rows]

@app.delete("/reviews/{review_id}")
def delete_review(review_id: int):
    """리뷰 삭제"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM reviews WHERE id = %s", (review_id,))
        
        if cursor.fetchone() is None:
            cursor.close()
            raise HTTPException(status_code=404, detail="삭제할 리뷰가 없습니다.")
        
        cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
        conn.commit()
        cursor.close()
    
    return {"message": "리뷰 삭제 성공"}

# ========================================
# 6. 헬스 체크
# ========================================

@app.get("/")
def read_root():
    """API 상태 확인"""
    return {
        "status": "ok",
        "message": "Movie Review System API",
        "database": "PostgreSQL",
        "environment": ENV
    }

@app.get("/health")
def health_check():
    """데이터베이스 연결 확인"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ========================================
# 7. 실행
# ========================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)