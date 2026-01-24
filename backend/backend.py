import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager

# 감성 분석 모델
from transformers import pipeline

app = FastAPI(
    title="영화 리뷰 시스템 API",
    description="영화 등록 및 AI 감성 분석 기반 리뷰 시스템",
    version="1.0.0"
)

# ========================================
# 환경 변수 설정
# ========================================

ENV = os.getenv("ENV", "development")

if ENV == "production":
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        print("✅ Render.com URL 형식 변환 완료")
else:
    DATABASE_URL = "postgresql://postgres:admin123@localhost:5432/movie_db"

print(f"🔧 환경: {ENV}")
print(f"🗄️ DB 연결: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Unknown'}")

# ========================================
# 데이터 모델 정의
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
    created_at: Optional[datetime] = None

class ReviewCreate(BaseModel):
    movie_id: int
    author: str
    content: str

# ========================================
# 감성 분석 모델 로드
# ========================================

CACHE_DIR = "./model_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

print("🤖 감성 분석 모델 로딩 중...")


sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="sangrimlee/bert-base-multilingual-cased-nsmc",  # 한국어 리뷰 학습된 모델
    model_kwargs={"cache_dir": CACHE_DIR},
    device=-1
)
print("✅ 한국어 감정 분석 모델 로딩 완료!")


# ========================================
# 감성 분석 함수
# ========================================

def analyze_sentiment(text: str) -> float:
    """
    감성 분석 함수
    
    Args:
        text (str): 분석할 리뷰 텍스트
    
    Returns:
        float: 0.0 ~ 1.0 (0: 매우 부정, 1: 매우 긍정)
    """
    try:
        # 텍스트가 너무 길면 자르기
        if len(text) > 500:
            text = text[:500]
        
        # 너무 짧은 텍스트 처리
        if len(text.strip()) < 3:
            return 0.5
        
        result = sentiment_analyzer(text)[0]
        label = result['label']
        score = result['score']
        
        print(f"📊 AI 분석 - Label: {label}, Confidence: {score:.4f}")
        
        # korean 모델: positive/negative
        if label.lower() == 'positive':
            sentiment_score = 0.5 + (score * 0.5)
        else:
            sentiment_score = 0.5 - (score * 0.5)
        
        print(f"✅ 최종 점수: {sentiment_score:.4f}")
        return round(sentiment_score, 4)
        
    except Exception as e:
        print(f"⚠️ 감성 분석 오류: {e}")
        return 0.5  # 오류 시 중립값 반환

# ========================================
# 데이터베이스 설정
# ========================================

@contextmanager
def get_db_connection():
    """PostgreSQL 연결 Context Manager"""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()

@app.on_event("startup")
def startup():
    """앱 시작 시 테이블 생성"""
    print("🔌 데이터베이스 연결 확인 중...")
    
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
            
            # 모델 워밍업 (첫 실행 속도 개선)
            print("🔥 AI 모델 워밍업 중...")
            test_scores = [
                analyze_sentiment("이 영화 정말 최고예요! 대박이에요!"),
                analyze_sentiment("별로예요. 돈 아까워요."),
                analyze_sentiment("그냥 그래요.")
            ]
            print(f"✅ 워밍업 완료! 테스트 점수: {test_scores}")
            break
            
        except psycopg.OperationalError as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"❌ DB 연결 실패: {e}")
                raise
            print(f"⏳ DB 연결 대기 중... ({retry_count}/{max_retries})")
            time.sleep(2)

# ========================================
# 영화 API
# ========================================

@app.post("/movies", response_model=Movie, tags=["영화"])
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

@app.get("/movies", response_model=List[MovieWithRating], tags=["영화"])
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

@app.get("/movies/{movie_id}", response_model=MovieWithRating, tags=["영화"])
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

@app.delete("/movies/{movie_id}", tags=["영화"])
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
    
    return {"message": "영화가 삭제되었습니다.", "status": "success"}

# ========================================
# 리뷰 API
# ========================================

@app.post("/reviews", response_model=Review, tags=["리뷰"])
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
            
            # 2. 감성 분석 실행
            print(f"\n📊 감성 분석 시작")
            print(f"리뷰 내용: {review.content[:100]}...")
            sentiment_score = analyze_sentiment(review.content)
            
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

@app.get("/reviews", response_model=List[Review], tags=["리뷰"])
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

@app.get("/movies/{movie_id}/reviews", response_model=List[Review], tags=["리뷰"])
def get_movie_reviews(movie_id: int):
    """특정 영화의 전체 리뷰 조회"""
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

@app.delete("/reviews/{review_id}", tags=["리뷰"])
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
    
    return {"message": "리뷰가 삭제되었습니다.", "status": "success"}

# ========================================
# 헬스 체크
# ========================================

@app.get("/", tags=["시스템"])
def read_root():
    """API 상태 확인"""
    return {
        "status": "ok",
        "message": "영화 리뷰 시스템 API",
        "database": "PostgreSQL + psycopg3",
        "environment": ENV,
        "ai_model": "Multilingual BERT Sentiment (5-star)" if MODEL_TYPE == "5-star" else "DistilBERT Sentiment"
    }

@app.get("/health", tags=["시스템"])
def health_check():
    """데이터베이스 연결 상태 확인"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ========================================
# 실행
# ========================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 서버 시작: http://localhost:{port}")
    print(f"📚 API 문서: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)