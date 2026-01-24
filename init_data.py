import os
import psycopg
from datetime import datetime
import random

# 데이터베이스 연결 설정
# 환경 변수가 없으면 기본값(로컬 개발용) 사용
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/movie_db")

SAMPLE_MOVIES = [
    {
        "title": "인셉션",
        "release_date": "2010-07-21",
        "director": "크리스토퍼 놀란",
        "genre": "SF, 액션",
        "poster_url": "https://image.tmdb.org/t/p/original/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg"
    },
    {
        "title": "기생충",
        "release_date": "2019-05-30",
        "director": "봉준호",
        "genre": "드라마, 스릴러",
        "poster_url": "https://image.tmdb.org/t/p/original/jSuTH2wyQAp80lVr3d0tQGgHPP.jpg"
    },
    {
        "title": "인터스텔라",
        "release_date": "2014-11-06",
        "director": "크리스토퍼 놀란",
        "genre": "SF, 드라마",
        "poster_url": "https://image.tmdb.org/t/p/original/gEU2QniL6E8ahDaX06e8q288UL.jpg"
    }
]

SAMPLE_REVIEWS = [
    ("정말 인생 영화입니다!", 0.9),
    ("시간 가는 줄 모르고 봤네요.", 0.8),
    ("연출이 대단합니다.", 0.85),
    ("배우들 연기가 훌륭해요.", 0.9),
    ("생각보다 지루했어요.", 0.3),
    ("스토리가 좀 난해하네요.", 0.4),
    ("영상미가 압도적입니다.", 0.95),
    ("결말이 충격적이에요.", 0.8),
    ("다시 보고 싶은 영화.", 0.9),
    ("가족이랑 보기 좋아요.", 0.75),
    ("음악이 너무 좋아요.", 0.85),
    ("기대보다는 별로였어요.", 0.35),
    ("감독의 천재성이 돋보임.", 0.92)
]

def init_data():
    print(f"🔌 Connecting to DB: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else '...'}")
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                print("🧹 기존 데이터 정리 중...")
                cursor.execute("TRUNCATE TABLE reviews, movies RESTART IDENTITY CASCADE;")
                
                print("🎬 영화 데이터 추가 중...")
                movie_ids = []
                for movie in SAMPLE_MOVIES:
                    cursor.execute('''
                        INSERT INTO movies (title, release_date, director, genre, poster_url)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    ''', (movie["title"], movie["release_date"], movie["director"], movie["genre"], movie["poster_url"]))
                    movie_id = cursor.fetchone()[0]
                    movie_ids.append(movie_id)
                    print(f"  + {movie['title']} (ID: {movie_id})")
                
                print("✍️ 리뷰 데이터 추가 중...")
                authors = ["김철수", "이영희", "박지성", "손흥민", "봉준호", "User123", "MovieFan", "Reviewer_A"]
                
                for movie_id in movie_ids:
                    for i in range(12): 
                        content, sentiment = random.choice(SAMPLE_REVIEWS)
                        author = random.choice(authors)
                        final_score = min(1.0, max(0.0, sentiment + random.uniform(-0.1, 0.1)))
                        
                        cursor.execute('''
                            INSERT INTO reviews (movie_id, author, content, sentiment_score)
                            VALUES (%s, %s, %s, %s)
                        ''', (movie_id, author, content, final_score))
                    print(f"  + 영화 ID {movie_id}에 리뷰 12개 추가 완료")
                
                conn.commit()
                print("✅ 모든 초기 데이터가 성공적으로 등록되었습니다!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    init_data()
