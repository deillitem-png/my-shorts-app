import streamlit as st
import os
import datetime
import time
from google import genai
from google.genai import types
from googleapiclient.discovery import build
from PIL import Image

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
# 3. YouTube API 분석 함수 (구독자 대비 조회수 500%+ 추출)
# =========================================================
def fetch_top_performing_shorts(keyword, api_key):
    if not api_key:
        return []
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # 최근 7일 날짜 계산 (ISO 8601)
        one_week_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat() + "Z"
        
        # 1. 키워드 관련 숏폼 영상 검색 (#shorts 포함)
        search_response = youtube.search().list(
            q=f"{keyword} #shorts",
            part='id,snippet',
            maxResults=50,
            order='viewCount',
            publishedAfter=one_week_ago,
            type='video',
            videoDuration='short'
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        if not video_ids:
            return []

        # 2. 영상 세부 정보 (조회수) 가져오기
        videos_response = youtube.videos().list(
            id=','.join(video_ids),
            part='snippet,statistics'
        ).execute()

        channel_ids = list(set([item['snippet']['channelId'] for item in videos_response.get('items', [])]))
        
        # 3. 채널 구독자 수 가져오기
        channel_subscribers = {}
        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i:i+50]
            channels_response = youtube.channels().list(
                id=','.join(chunk),
                part='statistics'
            ).execute()
            for ch in channels_response.get('items', []):
                sub_count = int(ch['statistics'].get('subscriberCount', 1))
                channel_subscribers[ch['id']] = max(sub_count, 1)

        analyzed_videos = []
        for item in videos_response.get('items', []):
            title = item['snippet']['title']
            video_id = item['id']
            views = int(item['statistics'].get('viewCount', 0))
            ch_id = item['snippet']['channelId']
            subs = channel_subscribers.get(ch_id, 1)

            ratio = (views / subs) * 100

            if ratio >= 500:
                analyzed_videos.append({
                    'title': title,
                    'url': f"https://www.youtube.com/shorts/{video_id}",
                    'views': views,
                    'subs': subs,
                    'ratio': round(ratio, 1)
                })

        analyzed_videos = sorted(analyzed_videos, key=lambda x: x['ratio'], reverse=True)[:50]
        return analyzed_videos

    except Exception as e:
        st.warning(f"YouTube 분석 데이터를 불러오는 중 오류 발생: {e}")
        return []

# =========================================================
# 4. 메인 앱 실행 (비밀번호 통과 후)
# =========================================================
st.title("🎬 쇼핑 숏폼 대본 생성기 (이미지 분석 & 떡상 분석형)")
st.caption("Gemini 3.6 Flash & YouTube Data API 연동 | 이미지 첨부 기능 탑재")

# Gemini API 클라이언트 초기화
if not gemini_key:
    st.error("Streamlit Secrets에 GEMINI_API_KEY가 설정되지 않았습니다. Secrets를 먼저 확인해주세요.")
    st.stop()

client = genai.Client(api_key=gemini_key)

# 사이드바 입력 설정
with st.sidebar:
    st.header("⚙️ 기획 옵션")
    pattern = st.selectbox(
        "기획 패턴 선택",
        [
            "패턴 A: 훅 중심 (강렬한 문제 제기 + 빠른 해결)",
            "패턴 B: 정보 전달형 (핵심 특징 2가지 + 추천)",
            "패턴 C: 비교 분석형 (기존 제품 vs 해당 제품)",
            "패턴 D: 공감/상황극형 (일상 불편함 극복)"
        ]
    )
    st.divider()
    st.info("⏱️ **영상 구성 고정**\n8초 x 4개 씬 = 총 32초 타이트 대본")
    st.info("🖼️ **이미지 인식 탑재**\n상품 캡처 사진을 올리면 AI가 특징을 분석합니다.")

# 메인 입력 폼
product_name = st.text_input("📦 상품명 또는 키워드를 입력하세요", placeholder="예: 야채 탈수기, 마늘다지기, 샤워메이트 바디워시")
product_features = st.text_area("✨ 상품 핵심 특징 및 장점 (글로 직접 입력 시)", placeholder="예: 무선 충전, 강력한 탈수 능력, 내구성 우수, 간편한 세척")

# 📸 이미지 여러 장 업로드 기능 추가
uploaded_files = st.file_uploader(
    "📷 상품 설명 또는 캡처 이미지 첨부 (여러 장 선택 가능)", 
    type=["png", "jpg", "jpeg", "webp"], 
    accept_multiple_files=True
)

# 업로드된 이미지 미리보기 표시
if uploaded_files:
    st.write(f"첨부된 이미지: 총 {len(uploaded_files)}장")
    cols = st.imagerows if hasattr(st, "imagerows") else st.columns(min(len(uploaded_files), 4))
    for idx, file in enumerate(uploaded_files):
        with cols[idx % len(cols)]:
            st.image(file, caption=f"이미지 {idx+1}", use_column_width=True)

if st.button("🚀 이미지 분석 & 32초 대본 생성하기", type="primary", use_container_width=True):
    if not product_name:
        st.warning("상품명을 입력해주세요!")
    else:
        # 1. 떡상 영상 분석
        with st.spinner("최근 7일간 구독자 대비 조회수 500% 이상 떡상한 영상 상위 50개를 분석 중입니다..."):
            top_videos = fetch_top_performing_shorts(product_name, youtube_key)

        st.subheader("🔥 최근 1주일 키워드 떡상 영상 Top 10 (구독자 대비 조회수 500%+)")
        if top_videos:
            top_10 = top_videos[:10]
            for idx, vid in enumerate(top_10, 1):
                st.write(f"**{idx}. [{vid['title']}]({vid['url']})** — 조회수: {vid['views']:,}회 / 구독자: {vid['subs']:,}명 (**성과: {vid['ratio']}%**) ")
        else:
            st.info("최근 7일 내 조건에 맞는 영상을 찾지 못해 일반 최적화 알고리즘 기반으로 대본을 작성합니다.")

        analysis_context = ""
        if top_videos:
            analysis_context = "다음은 최근 1주일간 해당 키워드로 구독자 대비 조회수 500% 이상을 기록한 상위 떡상 영상들의 제목 리스트이다:\n"
            for v in top_videos:
                analysis_context += f"- {v['title']} (성과: {v['ratio']}%)\n"

        # 2. 이미지 파일 처리 및 AI 전달 준비
        pil_images = []
        if uploaded_files:
            for file in uploaded_files:
                pil_images.append(Image.open(file))

        # 3. Gemini 대본 생성 요청 구성
        with st.spinner("첨부된 이미지와 떡상 패턴을 종합하여 32초 대본을 짜는 중입니다..."):
            prompt_contents = []
            
            # 첨부된 이미지가 있다면 프롬프트 리스트에 추가
            if pil_images:
                prompt_contents.extend(pil_images)

            text_prompt = f"""
            너는 대한민국 최고의 YouTube Shorts / TikTok 쇼핑 숏폼 전문 기획자이자 카피라이터이다.

            [실시간 떡상 영상 데이터 분석]
            {analysis_context if analysis_context else '최근 떡상 데이터 없음'}

            [상품 정보]
            - 상품명: {product_name}
            - 사용자가 직접 적은 특징: {product_features if product_features else '입력 안됨'}
            - 첨부된 이미지 분석 지시: 첨부된 이미지(상품 사진, 상세페이지 캡처 등)를 면밀히 분석하여, 이미지 속에 드러나는 상품의 디자인, 편리한 기능, 사용 상황, 문구 등을 스스로 파악하고 대본에 적극 반영할 것.
            - 적용 패턴: {pattern}

            [대본 필수 구성 조건 (엄격 준수)]
            총 32초 영상이며, 정확히 8초씩 분량 분배된 총 4개의 씬(Scene)으로 구성할 것.

            - **Scene 1 (0초~8초)**: [시각적/상황적 훅] 분석된 떡상 영상들의 훅을 참고하여 시청자 이탈을 막는 강렬한 첫 3초 훅 + 문제 제기
            - **Scene 2 (8초~16초)**: [핵심 해결책 제시] 상품 등장 및 이미지에서 확인된 가장 강력한 1번 특징/기능 연출
            - **Scene 3 (16초~24초)**: [실사용 체감 및 디테일] 사용 편의성(예: 편리함, 간편함 등), 세척/보관 등 추가 특징 연출
            - **Scene 4 (24초~32초)**: [구매 유도 CTA] 혜택/결론 정리 + 프로필 링크/댓글 구매 유도 멘트

            [작성 형식]
            1. **[상위 50위 떡상 영상 종합 분석 및 이미지 인식 요약]**: 최근 반응이 좋은 훅 패턴과, 첨부된 이미지에서 파악한 상품의 핵심 장점을 간단히 2~3줄로 요약할 것.
            2. 각 Scene별 마크다운 테이블 또는 구조화된 표기:
               - 씬 번호 및 타임코드 (예: Scene 1 [00:00~00:08])
               - 화면 해설 (어떤 영상 화면과 컷 전환이 들어가는지)
               - 나레이션/대사 (8초 동안 말할 수 있는 타이트한 글자 수)
               - 자막 텍스트 (화면에 크게 띄울 키워드)
            3. 마지막에 추천 BGM 분위기 1줄 정리.
            """
            
            prompt_contents.append(text_prompt)

            # 503 에러 대비 재시도 로직 포함 (최대 3회)
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt_contents
                    )
                    st.divider()
                    st.success(f"✅ 이미지 분석 및 떡상 패턴 기반 32초 대본 생성 완료! (적용 패턴: {pattern})")
                    st.markdown(response.text)
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < 2:
                        time.sleep(2)
                    else:
                        st.error(f"오류가 발생했습니다. 잠시 후 다시 시도해 주세요: {e}")
                        break
