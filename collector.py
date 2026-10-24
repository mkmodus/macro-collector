import os
import json
from datetime import datetime
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# 1. API 키 및 최신 지원 모델 초기화
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY가 등록되지 않았습니다.")

genai.configure(api_key=GEMINI_KEY)

# 시스템 요구 최신 모델(gemini-3.8-flash) 우선 적용 및 Fallback 리스트
candidate_models = ["gemini-3.8-flash", "gemini-3-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
model = None
target_model_name = "gemini-3.8-flash"

for m_name in candidate_models:
    try:
        candidate = genai.GenerativeModel(m_name)
        # 가벼운 핑 테스트
        candidate.generate_content("ping")
        model = candidate
        target_model_name = m_name
        break
    except Exception:
        continue

if not model:
    # 계정 내 활성화된 첫 번째 가용 모델 자동 선택
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            model = genai.GenerativeModel(m.name)
            target_model_name = m.name
            break

# 2. 파이프라인 소스 ①: 주요 매크로 유튜브 트랜스크립트 수집
def get_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        text = " ".join([t['text'] for t in transcript])
        if len(text) > 8000:
            text = text[:4000] + "\n...[중략]...\n" + text[-4000:]
        return text
    except Exception as e:
        return f"(자막 수집 건너뜀: {e})"

YOUTUBE_VIDEOS = {
    "리스크는 관리하는 것": "85C1Aw5VwTM",
    "시장이 놓치고 있는 결정적 신호": "L8k1Aq9sWKY",
    "금리가 무서운 이유": "bLTnEwWdirk",
    "붕괴의 시그널": "NYro7Ub6elE",
    "오르는 주식": "a_9EQBkciCU"
}

collected_transcripts = []
for title, v_id in YOUTUBE_VIDEOS.items():
    t_text = get_youtube_transcript(v_id)
    if "자막 수집 건너뜀" not in t_text:
        collected_transcripts.append(f"### [영상 자막 분석: {title}]\n{t_text[:3000]}")

# 3. 파이프라인 소스 ②: 글로벌 매크로 RSS 뉴스 피드 수집
FEED_URLS = [
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=Federal%20Reserve&target=rss",
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=BofA&target=rss"
]

collected_news = []
for url in FEED_URLS:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:4]:
            collected_news.append(f"- 제목: {entry.title}\n  내용: {entry.get('summary', '')}")
    except Exception:
        pass

combined_sources = "\n\n".join(collected_transcripts + collected_news)

# 4. 정량화 및 내러티브 정형화 프롬프트
prompt = f"""
당신은 퀀트 헤지펀드의 시니어 매크로 애널리스트입니다.
아래 수집된 글로벌 IB/전략가들의 발언 및 뉴스 원문을 분석하여 다음 4가지 섹션으로 정밀 브리핑을 작성하세요.

1. **글로벌 IB/전문가 핵심 메시지 (매크로 리딩방 동향)**:
   - 발언 주체(BofA, 골드만삭스, PIMCO, 연준 등)와 대상 자산(미 국채 10년물 금리, 환율, AI CapEx 등)
   - 제시된 포지셔닝(숏/롱) 및 유도하려는 시장 내러티브

2. **포지셔닝 괴리도 및 시그널 분석**:
   - 언론에 유포되는 공포/낙관론과 실제 수급(쇼커버, 롱스퀴즈 등) 간의 괴리 여부
   - 전환 변곡점 타임라인(예: 중간선거/대선 이후, 특정 금리 레벨 터치 등)

3. **정량화 지표 요약 (JSON Table)**:
   - [기관명, 대상자산, 스탠스(Bullish/Bearish/Neutral), 목표치/트리거, 신뢰도(1~5)]

4. **한국 증시(KOSPI/KOSDAQ) 운용 대응 지침**:
   - 고ROE·고ROC 우량주 및 계절성 저PBR 종목에 미치는 영향
   - 단기 현금 비중 및 추천 진입 전술

[수집된 원문 데이터]:
{combined_sources[:9000]}
"""

try:
    response = model.generate_content(prompt)
    analysis_text = response.text
except Exception as e:
    analysis_text = f"분석 본문 생성 대체 알림: {e}\n\n[수집 원문 요약]\n" + combined_sources[:2000]

# 5. 파일 저장: 항상 두 파일 모두 안정적으로 기록되도록 보장
today_str = datetime.now().strftime("%Y-%m-%d_%H%M")
os.makedirs("reports", exist_ok=True)

# 1) 노트북 소스 연동용 최신 통합 파일 (항상 이 고정 파일명으로 덮어씀)
latest_filename = "LATEST_MACRO_BRIEFING.md"
with open(latest_filename, "w", encoding="utf-8") as f:
    f.write(f"# [최신] 글로벌 IB 매크로 내러티브 & 수급 브리핑\n")
    f.write(f"*최종 갱신 시각: {today_str}* | *엔진: {target_model_name}*\n\n")
    f.write(analysis_text)

# 2) 히스토리 보관용 일자별 리포트
history_filename = f"reports/IB_Macro_Report_{today_str}.md"
with open(history_filename, "w", encoding="utf-8") as f:
    f.write(f"# 글로벌 매크로 내러티브 브리핑 ({today_str})\n\n")
    f.write(f"> **Engine:** {target_model_name} | **Status:** Active\n\n")
    f.write(analysis_text)

print(f"파이프라인 실행 완료: {latest_filename} 및 {history_filename} 생성 완료 (적용 모델: {target_model_name})")
