import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = FastAPI()

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
    movie_title: Optional[str] = None  # 추가
    author: str
    content: str
    sentiment_score: Optional[float] = None
    created_at: Optional[str] = None

class ReviewCreate(BaseModel):
    movie_id: int
    author: str
    content: str

# ========================================
# 2. 감성 분석 모델 로드
# ========================================

print("🤖 감성 분석 모델 로딩 중...")
MODEL_NAME = "beomi/KcELECTRA-base-v2022"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
print("✅ 모델 로딩 완료!")

def analyze_sentiment(text: str) -> float:
    """
    감성 분석 함수
    Returns: 0.0 ~ 1.0 (0: 부정, 1: 긍정)
    """
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
    
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        positive_score = probabilities[0][1].item()
    
    return round(positive_score, 4)

# ========================================
# 3. 데이터베이스 설정
# ========================================

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

@app.on_event("startup")
def startup():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 영화 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            release_date TEXT,
            director TEXT,
            genre TEXT,
            poster_url TEXT
        )
    ''')
    
    # 리뷰 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            movie_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            sentiment_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

# ========================================
# 4. 영화 API (성능 개선)
# ========================================

@app.post("/movies")
def create_movie(movie: Movie):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO movies (title, release_date, director, genre, poster_url)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    ''', (movie.title, movie.release_date, movie.director, movie.genre, movie.poster_url))
    
    movie.id = cursor.fetchone()['id']
    conn.commit()
    cursor.close()
    conn.close()
    
    return movie

@app.get("/movies", response_model=List[MovieWithRating])
def get_movies():
    """전체 영화 목록 조회 (평점 포함) - 성능 개선"""
    with get_db_connection() as conn:
        rows = conn.execute('''
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
            GROUP BY m.id
            ORDER BY m.id DESC
        ''').fetchall()
    
    return [dict(row) for row in rows]

@app.get("/movies/{movie_id}", response_model=MovieWithRating)
def get_movie(movie_id: int):
    """특정 영화 상세 조회 (평점 포함)"""
    with get_db_connection() as conn:
        row = conn.execute('''
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
            GROUP BY m.id
        ''', (movie_id,)).fetchone()
    
    if row is None:
        raise HTTPException(status_code=404, detail="영화를 찾을 수 없습니다.")
    
    return dict(row)

@app.delete("/movies/{movie_id}")
def delete_movie(movie_id: int):
    """영화 삭제"""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
        
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="삭제할 영화가 없습니다.")
        
        conn.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
        conn.commit()
    
    return {"message": "삭제 성공"}

# ========================================
# 5. 리뷰 API
# ========================================

@app.post("/reviews", response_model=Review)
def create_review(review: ReviewCreate):
    """리뷰 등록 + 자동 감성 분석"""
    
    with get_db_connection() as conn:
        # 1. 영화 존재 여부 확인
        movie = conn.execute("SELECT * FROM movies WHERE id = %s", (review.movie_id,)).fetchone()
        
        if movie is None:
            raise HTTPException(status_code=404, detail="영화를 찾을 수 없습니다.")
        
        # 2. 감성 분석 실행
        sentiment_score = analyze_sentiment(review.content)
        
        # 3. 리뷰 저장
        cursor = conn.execute('''
            INSERT INTO reviews (movie_id, author, content, sentiment_score)
            VALUES (%s, %s, %s, %s)
        ''', (review.movie_id, review.author, review.content, sentiment_score))
        
        conn.commit()
        review_id = cursor.lastrowid
        
        # 4. 저장된 리뷰 조회 (영화 제목 포함)
        row = conn.execute('''
            SELECT r.*, m.title as movie_title
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id
            WHERE r.id = %s
        ''', (review_id,)).fetchone()
    
    return dict(row)

@app.get("/reviews", response_model=List[Review])
def get_all_reviews(limit: int = 10):
    """최근 리뷰 조회 (영화 제목 포함)"""
    with get_db_connection() as conn:
        rows = conn.execute('''
            SELECT r.*, m.title as movie_title
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id
            ORDER BY r.created_at DESC 
            LIMIT %s
        ''', (limit,)).fetchall()
    
    return [dict(row) for row in rows]

@app.get("/movies/{movie_id}/reviews", response_model=List[Review])
def get_movie_reviews(movie_id: int):
    """특정 영화의 리뷰 조회"""
    with get_db_connection() as conn:
        rows = conn.execute('''
            SELECT r.*, m.title as movie_title
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id
            WHERE r.movie_id = %s 
            ORDER BY r.created_at DESC
        ''', (movie_id,)).fetchall()
    
    return [dict(row) for row in rows]

@app.delete("/reviews/{review_id}")
def delete_review(review_id: int):
    """리뷰 삭제"""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM reviews WHERE id = %s", (review_id,))
        
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="삭제할 리뷰가 없습니다.")
        
        conn.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
        conn.commit()
    
    return {"message": "리뷰 삭제 성공"}

# ========================================
# 6. 실행
# ========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)