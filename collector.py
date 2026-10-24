import os
import feedparser
from datetime import datetime
import google.generativeai as genai

# 1. API 설정
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY가 등록되지 않았습니다.")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# 2. 무료 글로벌 매크로 RSS 뉴스 피드 수집 (CNBC, 로이터 매크로 등)
FEED_URLS = [
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=Federal%20Reserve&target=rss",
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=BofA&target=rss"
]

collected_news = []
for url in FEED_URLS:
    feed = feedparser.parse(url)
    for entry in feed.entries[:5]:  # 최신 뉴스 5개씩
        collected_news.append(f"- 제목: {entry.title}\n  요약: {entry.get('summary', '')}")

raw_text = "\n\n".join(collected_news)

# 3. 비정형 내러티브 정형화 프롬프트
prompt = f"""
다음은 최근 글로벌 경제 뉴스 및 기관 코멘트 요약이다.
한국 주식 투자자 관점에서 아래 형식으로 정리해줘:

1. 글로벌 매크로 주요 내러티브 (국채 금리, AI 투자 회수율/ROIC, 환율 등)
2. 대형 기관/전략가(BofA, 골드만삭스, 연준 등)의 포지셔닝 및 분위기
3. 한국 증시(코스피/코스닥)에 미칠 영향 요약

[뉴스 원문]:
{raw_text}
"""

try:
    response = model.generate_content(prompt)
    summary_result = response.text
except Exception as e:
    summary_result = f"요약 생성 중 오류 발생: {e}"

# 4. 일자별 마크다운 문서로 저장
today_str = datetime.now().strftime("%Y-%m-%d_%H%M")
os.makedirs("reports", exist_ok=True)
filename = f"reports/IB_Macro_Report_{today_str}.md"

with open(filename, "w", encoding="utf-8") as f:
    f.write(f"# 글로벌 매크로 내러티브 브리핑 ({today_str})\n\n")
    f.write(summary_result)

print(f"보고서 저장 완료: {filename}")
