import streamlit as st
import requests

# 백엔드 서버 주소
BACKEND_URL = "http://localhost:8000"

# 페이지 설정
st.set_page_config(
    page_title="영화 리뷰 시스템",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 영화 리뷰 시스템")

# ========================================
# 감성 분석 결과 표시 함수
# ========================================

def display_sentiment(score):
    """감성 점수를 이모지와 색상으로 표시"""
    if score is None:
        return "⭐ 아직 리뷰가 없습니다", "gray"
    
    if score >= 0.7:
        return f"😊 긍정 ({score:.2f})", "green"
    elif score >= 0.4:
        return f"😐 중립 ({score:.2f})", "orange"
    else:
        return f"😞 부정 ({score:.2f})", "red"

# ========================================
# 영화 등록 다이얼로그
# ========================================

@st.dialog("🎬 영화 등록하기")
def new_movie_form():
    with st.form("movie_form"):
        title = st.text_input("제목", placeholder="예: 기생충")
        release_date = st.text_input("개봉일", placeholder="예: 2019-05-30")
        director = st.text_input("감독", placeholder="예: 봉준호")
        genre = st.text_input("장르", placeholder="예: 드라마, 스릴러")
        poster_url = st.text_input("포스터 URL", placeholder="이미지 URL 입력")

        col1, col2 = st.columns(2)
        with col1:
            cancel = st.form_submit_button("취소", use_container_width=True)
        with col2:
            submit = st.form_submit_button("등록하기", type="primary", use_container_width=True)
        
        if submit:
            if not all([title, release_date, director, genre]):
                st.error("모든 필드를 입력해주세요!")
                return
            
            new_movie = {
                "title": title,
                "release_date": release_date,
                "director": director,
                "genre": genre,
                "poster_url": poster_url
            }
            
            try:
                response = requests.post(f"{BACKEND_URL}/movies", json=new_movie)
                
                if response.status_code == 200:
                    st.success("✅ 영화가 등록되었습니다!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ 영화 등록에 실패했습니다.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 백엔드 서버에 연결할 수 없습니다.")

# ========================================
# 리뷰 등록 다이얼로그
# ========================================

@st.dialog("✍️ 리뷰 등록하기")
def new_review_form(movie_id, movie_title):
    st.subheader(f"'{movie_title}' 리뷰 작성")
    
    with st.form("review_form"):
        author = st.text_input("작성자", placeholder="이름을 입력하세요")
        content = st.text_area(
            "리뷰 내용", 
            placeholder="영화에 대한 솔직한 의견을 남겨주세요...",
            height=150
        )
        
        col1, col2 = st.columns(2)
        with col1:
            cancel = st.form_submit_button("취소", use_container_width=True)
        with col2:
            submit = st.form_submit_button("등록하기", type="primary", use_container_width=True)
        
        if submit:
            if not author or not content:
                st.error("작성자와 리뷰 내용을 모두 입력해주세요!")
                return
            
            new_review = {
                "movie_id": movie_id,
                "author": author,
                "content": content
            }
            
            try:
                with st.spinner("🤖 감성 분석 중..."):
                    response = requests.post(f"{BACKEND_URL}/reviews", json=new_review)
                
                if response.status_code == 200:
                    review_data = response.json()
                    sentiment_text, color = display_sentiment(review_data['sentiment_score'])
                    
                    st.success("✅ 리뷰가 등록되었습니다!")
                    st.info(f"📊 감성 분석 결과: {sentiment_text}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ 리뷰 등록에 실패했습니다.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 백엔드 서버에 연결할 수 없습니다.")

# ========================================
# 메인 화면
# ========================================

col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("➕ 영화 등록", use_container_width=True):
        new_movie_form()
with col2:
    refresh = st.button("🔄 새로고침", use_container_width=True)

st.divider()

# ========================================
# 영화 목록 표시 (성능 개선 - 한 번의 API 호출)
# ========================================

try:
    response = requests.get(f"{BACKEND_URL}/movies")
    movies = response.json()
    
    if not movies:
        st.info("📭 등록된 영화가 없습니다. 영화를 등록해보세요!")
    else:
        st.header(f"🎥 영화 목록 ({len(movies)}개)")
        
        # 한 줄에 3개씩 카드 배치
        cols_per_row = 3
        rows = [movies[i:i + cols_per_row] for i in range(0, len(movies), cols_per_row)]
        
        for row_movies in rows:
            cols = st.columns(cols_per_row)
            
            for idx, movie in enumerate(row_movies):
                with cols[idx]:
                    with st.container(border=True):
                        # 포스터 이미지
                        if movie.get('poster_url'):
                            try:
                                st.image(movie['poster_url'], use_container_width=True)
                            except:
                                st.write("🖼️ 이미지를 불러올 수 없습니다")
                        else:
                            st.write("🎬")
                        
                        # 영화 정보
                        st.subheader(movie['title'])
                        st.caption(f"🎬 {movie['director']} | 🎭 {movie['genre']}")
                        st.write(f"📅 {movie['release_date']}")
                        
                        # 평균 평점 표시 (이미 데이터에 포함됨!)
                        if movie['review_count'] > 0:
                            sentiment_text, color = display_sentiment(movie['average_rating'])
                            st.markdown(f"⭐ **평점**: :{color}[{sentiment_text}]")
                            st.caption(f"리뷰 {movie['review_count']}개")
                        else:
                            st.caption("⭐ 아직 리뷰가 없습니다")
                        
                        st.divider()
                        
                        # 버튼들
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            if st.button("✍️ 리뷰", key=f"review_{movie['id']}", use_container_width=True):
                                new_review_form(movie['id'], movie['title'])
                        
                        with col_btn2:
                            if st.button("🗑️ 삭제", key=f"delete_{movie['id']}", use_container_width=True):
                                try:
                                    delete_response = requests.delete(f"{BACKEND_URL}/movies/{movie['id']}")
                                    if delete_response.status_code == 200:
                                        st.success("삭제되었습니다!")
                                        st.rerun()
                                    else:
                                        st.error("삭제 실패")
                                except:
                                    st.error("서버 오류")

except requests.exceptions.ConnectionError:
    st.error("🔌 백엔드 서버에 연결할 수 없습니다. 서버를 실행해주세요:")
    st.code("python backend.py")
except Exception as e:
    st.error(f"오류 발생: {str(e)}")

st.divider()

# ========================================
# 최근 리뷰 10개 표시
# ========================================

st.header("📝 최근 리뷰")

try:
    reviews_response = requests.get(f"{BACKEND_URL}/reviews?limit=10")
    reviews = reviews_response.json()
    
    if not reviews:
        st.info("📭 아직 작성된 리뷰가 없습니다.")
    else:
        for review in reviews:
            with st.container(border=True):
                # 헤더: 영화 정보 + 감성 분석 결과
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    # 영화 제목이 이미 포함됨!
                    st.markdown(f"**🎬 {review.get('movie_title', f'영화 ID: {review["movie_id"]}')}**")
                
                with col2:
                    sentiment_text, color = display_sentiment(review['sentiment_score'])
                    st.markdown(f":{color}[**{sentiment_text}**]")
                
                with col3:
                    st.caption(f"ID: {review['id']}")
                
                # 리뷰 내용
                st.write(f"**✍️ {review['author']}**")
                st.write(review['content'])
                
                # 작성 시간
                st.caption(f"🕒 {review['created_at']}")
                
                # 삭제 버튼
                if st.button("🗑️ 삭제", key=f"delete_review_{review['id']}", use_container_width=True):
                    try:
                        delete_response = requests.delete(f"{BACKEND_URL}/reviews/{review['id']}")
                        if delete_response.status_code == 200:
                            st.success("리뷰가 삭제되었습니다!")
                            st.rerun()
                    except:
                        st.error("삭제 실패")

except requests.exceptions.ConnectionError:
    st.warning("리뷰를 불러올 수 없습니다.")
except Exception as e:
    st.error(f"오류 발생: {str(e)}")

st.divider()
st.caption("🤖 Powered by FastAPI + Streamlit + KcELECTRA")