import streamlit as st
import requests
import os

# ========================================
# 설정
# ========================================

# 백엔드 서버 주소
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# 페이지 설정
st.set_page_config(
    page_title="영화 리뷰 시스템",
    page_icon="🎬",
    layout="wide"
)

# 제목
st.title("🎬 영화 리뷰 시스템")
st.caption("AI 감성 분석 기반 영화 리뷰 플랫폼")

# ========================================
# 유틸리티 함수
# ========================================

def display_sentiment(score):
    """
    감성 점수를 이모지와 색상으로 표시
    
    Args:
        score (float): 0.0 ~ 1.0 사이의 감성 점수
    
    Returns:
        tuple: (표시 텍스트, 색상)
    """
    if score is None:
        return "⭐ 리뷰 없음", "gray"
    
    if score >= 0.7:
        return f"😊 긍정 ({score:.2f})", "green"
    elif score >= 0.4:
        return f"😐 중립 ({score:.2f})", "orange"
    else:
        return f"😞 부정 ({score:.2f})", "red"

# ========================================
# 토스트 알림 처리
# ========================================

if 'show_toast' in st.session_state:
    toast_type = st.session_state['show_toast']

    if toast_type == "movie_registered":
        st.toast("✅ 영화가 등록되었습니다!", icon="🎬")
    elif toast_type == "review_registered":
        sentiment_score = st.session_state.get('review_sentiment')
        sentiment_text, _ = display_sentiment(sentiment_score) if sentiment_score else ("", "")
        st.toast(f"✅ 리뷰가 등록되었습니다! 감성 분석: {sentiment_text}", icon="✍️")
        if 'review_sentiment' in st.session_state:
            del st.session_state['review_sentiment']
    elif toast_type == "movie_deleted":
        st.toast("✅ 영화가 삭제되었습니다!", icon="🗑️")
    elif toast_type == "review_deleted":
        st.toast("✅ 리뷰가 삭제되었습니다!", icon="🗑️")

    del st.session_state['show_toast']

# ========================================
# 영화 등록 다이얼로그
# ========================================
import streamlit.components.v1 as components

def close_modal():
    # 자바스크립트를 주입해서 'Close' 버튼(X버튼)을 찾아서 클릭하게 함
    js = """
    <script>
        var closeBtns = window.parent.document.querySelectorAll('button[aria-label="Close"]');
        // 혹시 몰라 모든 닫기 버튼을 찾음 (보통 다이얼로그는 하나지만)
        closeBtns.forEach(btn => btn.click());
    </script>
    """
    # 화면에 안 보이게 height=0으로 실행
    components.html(js, height=0)

@st.dialog("🎬 영화 등록하기")
def new_movie_form():
    """영화 등록 폼"""
    st.write("영화 정보를 입력해주세요")
    
    with st.form("movie_form"):
        title = st.text_input("제목 *", placeholder="예: 기생충")
        release_date = st.text_input("개봉일 *", placeholder="예: 2019-05-30")
        director = st.text_input("감독 *", placeholder="예: 봉준호")
        genre = st.text_input("장르 *", placeholder="예: 드라마, 스릴러")
        poster_url = st.text_input("포스터 URL", placeholder="https://...")

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("취소", width="stretch"):
                close_modal()
        with col2:
            submit = st.form_submit_button("등록하기", type="primary", width="stretch")
        
        if submit:
            # 필수 필드 검증
            if not all([title, release_date, director, genre]):
                st.error("❌ 모든 필수 항목(*)을 입력해주세요!")
                return
            
            new_movie = {
                "title": title,
                "release_date": release_date,
                "director": director,
                "genre": genre,
                "poster_url": poster_url or ""
            }
            
            try:
                response = requests.post(f"{BACKEND_URL}/movies", json=new_movie)
                
                if response.status_code == 200:
                    st.session_state['show_toast'] = "movie_registered"
                    st.rerun()
                else:
                    st.error(f"❌ 오류 발생: {response.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("🔌 백엔드 서버에 연결할 수 없습니다.")
                st.info("로컬 실행 시: `python backend.py` 명령어로 서버를 먼저 실행하세요.")

# ========================================
# 리뷰 등록 다이얼로그
# ========================================

def new_review_form(movie_id, movie_title):
    """리뷰 작성 폼"""
    st.subheader(f"'{movie_title}' 리뷰 작성")
    st.caption("작성한 리뷰는 AI가 자동으로 감성을 분석합니다.")
    
    with st.form("review_form"):
        author = st.text_input("작성자 *", placeholder="이름을 입력하세요")
        content = st.text_area(
            "리뷰 내용 *", 
            placeholder="영화에 대한 솔직한 의견을 남겨주세요...",
            height=150
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("취소", width="stretch"):
                close_modal()
        with col2:
            submit = st.form_submit_button("등록하기", type="primary", width="stretch")
        
        if submit:
            if not author or not content:
                st.error("❌ 작성자와 리뷰 내용을 모두 입력해주세요!")
                return
            
            new_review = {
                "movie_id": movie_id,
                "author": author,
                "content": content
            }
            
            try:
                with st.spinner("🤖 AI 감성 분석 중..."):
                    response = requests.post(f"{BACKEND_URL}/reviews", json=new_review)
                
                if response.status_code == 200:
                    review_data = response.json()
                    st.session_state['show_toast'] = "review_registered"
                    st.session_state['review_sentiment'] = review_data['sentiment_score']
                    st.rerun()
                else:
                    st.error(f"❌ 오류 발생: {response.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("🔌 백엔드 서버에 연결할 수 없습니다.")


# ========================================
# 삭제 확인 다이얼로그
# ========================================

@st.dialog("🚨 영화 삭제 확인")
def confirm_delete_movie(movie_id, movie_title):
    """영화 삭제 확인 다이얼로그"""
    st.write(f"**'{movie_title}'** 영화를 정말로 삭제하시겠습니까?")
    st.caption("⚠️ 삭제된 영화와 관련된 모든 리뷰도 함께 삭제됩니다.")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("취소", width="stretch"):
            close_modal()
    with col2:
        if st.button("삭제", type="primary", width="stretch"):
            try:
                delete_response = requests.delete(f"{BACKEND_URL}/movies/{movie_id}")
                # delete_response.status_code == 200으로 하면 서버 오류라고 뜸
                if delete_response.status_code == 200:
                # if 200 <= delete_response.status_code < 300:
                    st.session_state['show_toast'] = "movie_deleted"
                    st.rerun()
                else:
                    st.error(f"❌ 삭제 실패: {delete_response.status_code} - {delete_response.text}")
            except requests.exceptions.ConnectionError:
                st.error("🔌 서버에 연결할 수 없습니다.")
            except Exception as e:
                st.error(f"🔌 서버 오류: {str(e)}")

# ========================================
# 영화별 리뷰 목록 다이얼로그 (완전 수정)
# ========================================

@st.dialog("📝 리뷰 목록", width="large")
def show_movie_reviews(movie_id, movie_title):
    """영화의 리뷰 목록 보기"""
    st.subheader(f"🎬 {movie_title}")

    writing_key = f'writing_review_{movie_id}'
    dialog_init_key = f'dialog_init_{movie_id}'
    
    # 리뷰 작성 버튼
    if st.button("✍️ 새 리뷰 작성하기", type="primary", width="stretch", key=f"write_btn_{movie_id}"):
        st.session_state[writing_key] = True
    
    st.divider()
    
    # ✅ 다이얼로그가 새로 열렸는지 확인
    # 메인 화면에서 이 함수를 호출할 때마다 dialog_init_key를 삭제하면
    # 여기서 다시 False로 초기화됨
    if dialog_init_key not in st.session_state:
        st.session_state[writing_key] = False
        st.session_state[dialog_init_key] = True

        # ✅ 체크박스 상태 초기화
        keys_to_delete = [
            key for key in st.session_state.keys() 
            if key.startswith(f'check_{movie_id}_') or 
                key.startswith(f'select_all_{movie_id}') or
                key.startswith(f'prev_select_all_{movie_id}')
        ]
        for key in keys_to_delete:
            del st.session_state[key]

        # ✅ 추가: 체크박스 관련 세션 상태 초기화
        st.session_state[f'select_all_{movie_id}'] = False
        st.session_state[f'prev_select_all_{movie_id}'] = False

    # ========================================
    # 리뷰 작성 폼 표시
    # ========================================
    if st.session_state[writing_key]:
        st.caption("작성한 리뷰는 AI가 자동으로 감성을 분석합니다.")
        
        with st.form(f"review_form_{movie_id}"):
            author = st.text_input("작성자 *", placeholder="이름을 입력하세요")
            content = st.text_area(
                "리뷰 내용 *", 
                placeholder="영화에 대한 솔직한 의견을 남겨주세요...",
                height=150
            )
            
            col1, col2 = st.columns(2)
            with col1:
                cancel = st.form_submit_button("취소", width="stretch")
            with col2:
                submit = st.form_submit_button("등록하기", type="primary", width="stretch")
            
            if cancel:
                st.session_state[writing_key] = False
                st.rerun()
            
            if submit:
                if not author or not content:
                    st.error("❌ 작성자와 리뷰 내용을 모두 입력해주세요!")
                else:
                    new_review = {
                        "movie_id": movie_id,
                        "author": author,
                        "content": content
                    }
                    
                    try:
                        with st.spinner("🤖 AI 감성 분석 중..."):
                            response = requests.post(f"{BACKEND_URL}/reviews", json=new_review)
                        
                        if response.status_code == 200:
                            review_data = response.json()
                            st.session_state['show_toast'] = "review_registered"
                            st.session_state['review_sentiment'] = review_data['sentiment_score']
                            st.session_state[writing_key] = False
                            st.rerun()
                        else:
                            st.error(f"❌ 오류 발생: {response.status_code}")
                    except requests.exceptions.ConnectionError:
                        st.error("🔌 백엔드 서버에 연결할 수 없습니다.")
        
        return
    
    # ========================================
    # 리뷰 목록 표시 (리뷰 작성 중이 아닐 때만)
    # ========================================

    # 리뷰 불러오기
    try:
        response = requests.get(f"{BACKEND_URL}/movies/{movie_id}/reviews")
        reviews = response.json()
        
        if not reviews:
            st.info("📭 아직 리뷰가 없습니다. 첫 리뷰를 작성해보세요!")
        else:
            st.caption(f"총 {len(reviews)}개의 리뷰")

            # 전체 선택 체크박스
            select_all = st.checkbox("전체 선택", key=f"select_all_{movie_id}")

            # ✅ 전체 선택 상태 변경 감지 및 동기화
            prev_select_all_key = f"prev_select_all_{movie_id}"
            if prev_select_all_key not in st.session_state:
                st.session_state[prev_select_all_key] = False

            # "전체 선택" 버튼의 상태가 바뀌었는지 확인
            if select_all != st.session_state[prev_select_all_key]:
                st.session_state[prev_select_all_key] = select_all
                # 바뀌었다면 모든 리뷰의 session_state 값을 강제로 변경
                for review in reviews:
                    st.session_state[f"check_{movie_id}_{review['id']}"] = select_all

            st.divider()

            selected_reviews = []

            for idx, review in enumerate(reviews):
                preview = review['content'][:40]
                if len(review['content']) > 40:
                    preview += "..."
                
                sentiment_text, color = display_sentiment(review['sentiment_score'])
                
                with st.container(border=True):
                    col_check, col_content = st.columns([1, 20])
                    
                    with col_check:
                        checkbox_key = f"check_{movie_id}_{review['id']}"
                        
                        # [핵심 수정 1] 값이 없을 때만 초기화 (value 파라미터 대신 사용)
                        if checkbox_key not in st.session_state:
                            st.session_state[checkbox_key] = False
                        
                        # [핵심 수정 2] value 파라미터 삭제! (key가 알아서 session_state를 바라봄)
                        is_checked = st.checkbox(
                            "선택",
                            key=checkbox_key, 
                            label_visibility="collapsed"
                        )
                        
                        if is_checked:
                            selected_reviews.append(review['id'])
                    
                    # 리뷰 내용 (펼치기)
                    with col_content:
                        with st.expander(
                            f"✍️ {review['author']} · {sentiment_text} · {preview}",
                            expanded=False
                        ):
                            # 전체 리뷰 내용
                            st.write(review['content'])
                            st.caption(f"🕒 {review['created_at']}")
            
            # 하단: 선택된 항목 삭제 버튼
            if selected_reviews:
                st.divider()
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.caption(f"✅ 선택된 리뷰: {len(selected_reviews)}개")
                
                with col3:
                    if st.button("🗑️ 삭제", type="primary", width="stretch", key=f"delete_selected_{movie_id}"):
                        try:
                            deleted_count = 0
                            for review_id in selected_reviews:
                                delete_response = requests.delete(f"{BACKEND_URL}/reviews/{review_id}")
                                if 200 <= delete_response.status_code < 300:
                                    deleted_count += 1
                            
                            if deleted_count > 0:
                                st.success(f"✅ {deleted_count}개의 리뷰가 삭제되었습니다!")
                                st.session_state['show_toast'] = "review_deleted"
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ 삭제 실패")
                        except Exception as e:
                            st.error(f"🔌 서버 오류: {str(e)}")
    
    except requests.exceptions.ConnectionError:
        st.error("🔌 서버에 연결할 수 없습니다.")
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")

@st.dialog("🚨 리뷰 삭제 확인")
def confirm_delete_review(review_id):
    """리뷰 삭제 확인 다이얼로그"""
    st.write("이 리뷰를 정말로 삭제하시겠습니까?")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("취소", width="stretch", key="cancel_review_delete"):
            close_modal()
    with col2:
        if st.button("삭제", type="primary", width="stretch", key="confirm_review_delete"):
            try:
                delete_response = requests.delete(f"{BACKEND_URL}/reviews/{review_id}")
                # ✅ 이 부분 수정!
                if 200 <= delete_response.status_code < 300:
                    st.session_state['show_toast'] = "review_deleted"
                    st.rerun()
                else:
                    st.error(f"❌ 삭제 실패: {delete_response.status_code} - {delete_response.text}")
            except requests.exceptions.ConnectionError:
                st.error("🔌 서버에 연결할 수 없습니다.")
            except Exception as e:
                st.error(f"🔌 서버 오류: {str(e)}")
        

# ========================================
# 메인 화면
# ========================================

# 상단 버튼
col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    if st.button("➕ 영화 등록", width="stretch"):
        new_movie_form()
with col2:
    refresh = st.button("🔄 새로고침", width="stretch")



# ========================================
# 영화 목록 표시
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
                                st.image(movie['poster_url'], width="stretch")
                            except:
                                st.write("🎬 포스터 없음")
                        else:
                            st.write("🎬")
                        
                        # 영화 정보
                        st.subheader(movie['title'])
                        st.caption(f"🎬 {movie['director']} | 🎭 {movie['genre']}")
                        st.write(f"📅 {movie['release_date']}")
                        
                        # 평균 평점 표시
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
                            if st.button("✍️ 리뷰", key=f"review_{movie['id']}", width="stretch"):
                                # ✅ 다이얼로그 열기 전에 초기화 플래그 삭제
                                dialog_init_key = f'dialog_init_{movie["id"]}'
                                if dialog_init_key in st.session_state:
                                    del st.session_state[dialog_init_key]
                                
                                show_movie_reviews(movie['id'], movie['title'])
                        
                        with col_btn2:
                            if st.button("🗑️ 삭제", key=f"delete_{movie['id']}", width="stretch"):
                                confirm_delete_movie(movie['id'], movie['title'])

except requests.exceptions.ConnectionError:
    st.error("🔌 백엔드 서버에 연결할 수 없습니다.")
    st.info("**로컬 실행 시:**")
    st.code("cd backend\npython backend.py", language="bash")
    st.info(f"**현재 연결 시도 중인 주소:** {BACKEND_URL}")
except Exception as e:
    st.error(f"❌ 오류 발생: {str(e)}")

st.divider()

# ========================================
# 푸터
# ========================================

st.caption("🤖 Powered by FastAPI + Streamlit + KcELECTRA")
st.caption(f"Backend: {BACKEND_URL}")
