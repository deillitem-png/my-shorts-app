import streamlit as st
import os
import datetime
import time
from google import genai

# Page Config
st.set_page_config(page_title="푸드/쇼핑 숏폼 대본 생성기", page_icon="🎬", layout="wide")

# =========================================================
# 1. Secrets에서 비밀번호 및 API 키 불러오기
# =========================================================
app_password = st.secrets.get("APP_PASSWORD", "")
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
youtube_key = st.secrets.get("YOUTUBE_API_KEY", "")

# =========================================================
# 2. 비밀번호 잠금 (인증 화면)
# =========================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 비밀번호를 입력하세요")
    st.caption("허가된 사용자만 접근할 수 있는 숏폼 대본 생성기입니다.")
    user_input_pw = st.text_input("접속 비밀번호", type="password")
    
    if st.button("로그인", use_container_width=True):
        if app_password and user_input_pw == app_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 일치하지 않거나 Secrets 설정이 완료되지 않았습니다.")
    st.stop()  # 🛑 비밀번호 통과 전까지는 메인 기능을 절대 실행하지 않음

# =========================================================
# 3. 메인 앱 실행 (비밀번호 통과 후)
# =========================================================
st.title("🎬 쇼핑 숏폼 대본 & 콘티 자동 생성기")
st.caption("Gemini 3.6 Flash 모델 기반 숏폼 기획 툴")

# Gemini API 클라이언트 초기화
if not gemini_key:
    st.error("Streamlit Secrets에 GEMINI_API_KEY가 설정되지 않았습니다. Secrets를 먼저 확인해주세요.")
    st.stop()

client = genai.Client(api_key=gemini_key)

# 사이드바 입력 설정
with st.sidebar:
    st.header("⚙️ 생성 옵션")
    pattern = st.selectbox(
        "기획 패턴 선택",
        [
            "패턴 A: 훅 중심 (강렬한 문제 제기 + 빠른 해결)",
            "패턴 B: 정보 전달형 (꿀팁 3가지 + 추천)",
            "패턴 C: 비교 분석형 (기존 제품 vs 해당 제품)",
            "패턴 D: 공감/상황극형 (일상 불편함 극복)"
        ]
    )
    video_length = st.radio("영상 길이 Target", ["15초 (초고속 훅)", "30초 (표준 숏폼)", "60초 (상세 정보)"])
    st.divider()
    st.info("🔓 Secrets에 설정된 API 키로 자동 연동되어 동작 중입니다.")

# 메인 입력 폼
product_name = st.text_input("📦 상품명 또는 키워드를 입력하세요", placeholder="예: 야채 탈수기, 마늘다지기, 샤워메이트 바디워시")
product_features = st.text_area("✨ 상품 핵심 특징 및 장점 (선택사항)", placeholder="예: 무선 충전, 강력한 탈수 능력, 내구성 우수, 간편한 세척")

if st.button("🚀 숏폼 대본 및 콘티 생성하기", type="primary", use_container_width=True):
    if not product_name:
        st.warning("상품명을 입력해주세요!")
    else:
        with st.spinner("최적의 숏폼 훅과 장면 콘티를 생성 중입니다..."):
            prompt = f"""
            너는 대한민국 최고의 YouTube Shorts / TikTok 쇼핑 숏폼 전문 기획자이자 카피라이터이다.
            아래 정보를 바탕으로 시청자의 시선을 사로잡는 숏폼 대본 및 장면별 상세 콘티를 작성하라.

            [상품 정보]
            - 상품명: {product_name}
            - 특징/소개: {product_features if product_features else '입력 안됨 (상품명 기반 분석하여 작성)'}
            - 적용 패턴: {pattern}
            - 목표 길이: {video_length}

            [작성 가이드라인]
            1. 첫 3초 안에 시청자 이탈을 막을 수 있는 강렬한 시각적/후각적/상황적 '훅(Hook)' 멘트 필수 포함.
            2. 화면 해설(영상 구성/컷 전환)과 나레이션(대사)을 1:1로 매칭하여 보기 쉽게 테이블 또는 구분된 리스트 형태로 제시할 것.
            3. 쿠팡 파트너스/쇼핑 숏폼 성격에 맞게 구매 욕구를 자극하는 자연스러운 CTA(Call To Action / 프로필 링크 유도) 포함할 것.
            4. 숏폼 영상 제작에 바로 활용할 수 있는 추천 BGM 분위기와 텍스트 자막 위치 팁도 함께 제시할 것.
            """

            # 503 에러 대비 재시도 로직 포함 (최대 3회)
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )
                    st.success(f"✅ 대본 생성 완료! (적용 패턴: {pattern})")
                    st.markdown(response.text)
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < 2:
                        time.sleep(2)
                    else:
                        st.error(f"오류가 발생했습니다. 잠시 후 다시 시도해 주세요: {e}")
                        break
