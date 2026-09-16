import datetime
import time
import streamlit as st
import google.genai as genai
from googleapiclient.discovery import build

# 웹 앱 제목 설정
st.set_page_config(page_title="식품 쇼츠 콘티 생성기", layout="centered")

st.title("🎬 32초 식품 쇼츠 콘티 생성기")
st.caption("쿠팡 파트너스 식품 전용 32초 마크다운 표 콘티 생성 앱")

# 사이드바 API 키 입력
with st.sidebar:
    st.header("🔑 API 키 설정")
    gemini_key = st.text_input("Gemini API Key", type="password")
    youtube_key = st.text_input("YouTube API Key", type="password")

# 메인 입력창
product_name = st.text_input("쿠팡 상품명을 입력하세요", placeholder="예: 활꽃게, 알룰로스, 닭가슴살")

if st.button("🔥 32초 콘티 생성하기", type="primary", use_container_width=True):
    if not gemini_key or not youtube_key:
        st.warning("왼쪽 사이드바에 Gemini 및 YouTube API 키를 입력해 주세요.")
    elif not product_name:
        st.warning("상품명을 입력해 주세요.")
    else:
        with st.spinner("유튜브 인기 트렌드 분석 및 식품 콘티 생성 중..."):
            try:
                # 1. 유튜브 인기 트렌드 추출
                youtube = build("youtube", "v3", developerKey=youtube_key)
                seven_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat() + "Z"
                
                search_response = youtube.search().list(
                    q="쿠팡추천식품 #shorts",
                    part="id,snippet",
                    maxResults=5,
                    type="video",
                    videoDuration="short",
                    publishedAfter=seven_days_ago,
                    order="viewCount"
                ).execute()

                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                pattern = "문제해결/비포애프터"
                
                if video_ids:
                    stats_response = youtube.videos().list(
                        part="snippet,statistics",
                        id=",".join(video_ids)
                    ).execute()
                    
                    patterns = {
                        "가격/가성비": ["가성비", "원대", "반값", "할인"],
                        "문제해결/비포애프터": ["이거", "청소", "정리", "해결", "식단"],
                        "비교/추천": ["TOP", "3가지", "추천", "비교", "필수"]
                    }
                    score_board = {"가격/가성비": 0, "문제해결/비포애프터": 0, "비교/추천": 0}
                    
                    for item in stats_response.get('items', []):
                        title = item['snippet']['title']
                        for cat, words in patterns.items():
                            if any(w in title for w in words):
                                score_board[cat] += 1
                    pattern = max(score_board, key=score_board.get)

                # 2. 제미나이 식품 전용 콘티 생성
                client = genai.Client(api_key=gemini_key)
                prompt = f"""
                [경고: 모든 답변은 100% 한국어로만 작성하세요. 서론이나 인삿말 없이 바로 마크다운 결과물만 출력하세요.]

                당신은 한국 유튜브 쿠팡 파트너스 식품(Food) 쇼츠 전문 기획자입니다.
                상품명: {product_name}
                분석된 트렌드 패턴: {pattern}

                [식품 전용 변환 규칙]
                분석된 패턴이 타 카테고리이더라도, 반드시 아래 연출로 100% 재해석하여 대본을 작성하세요.
                - 비주얼 연출 ➔ 조리 장면, 김이 모락모락 나는 비주얼, 치즈 늘어남, 육즙/윤기 클로즈업(Sizzle)
                - 비포&애프터 ➔ 배달비 4천원 내고 기다리기 vs 5분 만에 집에서 고퀄리티 완성 / 설탕 폭탄 vs 칼로리 싹 뺀 대체식
                - 식감 연출 ➔ 바삭함(ASMR), 쫀득함, 부드러운 식감 강조

                [필수 출력 양식]
                ---
                ### 📌 썸네일 설정
                - **배경 구도:** (군침 도는 음식 클로즈업 또는 가성비/비교 반반 구도)
                - **강렬한 노란색 문구 (3~5자):** (시선을 사로잡는 문구)

                ### 🎬 32초 식품 쇼츠 콘티 폼
                | 구분 | 타임코드 | 역할 | 나레이션 (음성) | 시각 연출 및 자막 |
                | :--- | :--- | :--- | :--- | :--- |
                | 1구간 | 0~8초 | 훅 & 문제 제기 | (강렬한 훅 나레이션) | **[시각]** (지글지글 조리/치즈/육즙 등 극강의 씨즐 컷)<br>**[자막]** (3~6자 자막) |
                | 2구간 | 8~16초 | 핵심 소구점 1 | (첫 번째 해결책 나레이션) | **[시각]** (조리 과정 또는 비교 연출)<br>**[자막]** (핵심 자막) |
                | 3구간 | 16~24초 | 핵심 소구점 2 | (두 번째 해결책 나레이션) | **[시각]** (ASMR/단면 연출)<br>**[자막]** (핵심 자막) |
                | 4구간 | 24~32초 | 구매 유도 & 마무리 | (댓글창 확인 유도 멘트) | **[시각]** (완성 접시 & 댓글창 가리키는 화살표)<br>**[자막]** (👇 고정 댓글 클릭!) |

                [주의사항]
                - 4구간 구매 유도는 오직 '댓글창 고정 링크' 또는 '관련 영상' 유도 멘트로만 작성하세요.
                """

                for attempt in range(3):
                    try:
                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=prompt
                        )
                        st.success(f"적용된 패턴: [{pattern}]")
                        st.markdown(response.text)
                        break
                    except Exception as e:
                        if "503" in str(e) and attempt < 2:
                            time.sleep(2)
                        else:
                            raise e
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")