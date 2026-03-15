"""
IDEA RADAR - AI 분석 스크립트 v5
누적 비교 점수 + KST + score 안정화
"""

import json, os, requests, re, time
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
def now_kst():
    return datetime.now(KST)

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

def call_claude(prompt, max_tokens=2000):
    if not CLAUDE_API_KEY:
        return None
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        resp = requests.post(CLAUDE_API_URL, headers=headers, json=body, timeout=60)
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
        else:
            print(f"❌ API 오류 {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ {e}")
    return None

def parse_json(text):
    if not text:
        return None
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except:
        pass
    try:
        start = text.index('{')
        depth = 0
        end = start
        for i, c in enumerate(text[start:], start):
            if c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        return json.loads(text[start:end+1])
    except:
        pass
    return None

def safe_int(val, default=5):
    if isinstance(val, int): return max(1, min(10, val))
    if isinstance(val, float): return max(1, min(10, int(val)))
    if isinstance(val, str):
        m = re.search(r'\d+', val)
        if m: return max(1, min(10, int(m.group())))
    return default

# ═══════════════════════════════════
# 1단계: 클러스터링
# ═══════════════════════════════════
def analyze_posts(posts):
    post_texts = [
        f"{i+1}. [{p['community']}] {p['title']}" +
        (f" | {p['content'][:100]}" if p.get("content") else "")
        for i, p in enumerate(posts[:40])
    ]
    prompt = f"""
커뮤니티 게시물에서 불편함과 니즈를 분석해주세요.

{chr(10).join(post_texts)}

JSON으로만 응답:
{{
  "clusters": [
    {{
      "category": "카테고리명",
      "pain_point": "핵심 불편함 한 문장",
      "post_count": 3,
      "urgency_score": 8,
      "target_users": "타겟 사용자",
      "example_posts": [1, 2]
    }}
  ],
  "trending_topics": ["키워드1","키워드2","키워드3","키워드4","키워드5"],
  "top_insight": "오늘 가장 중요한 인사이트 한 문장"
}}
"""
    return parse_json(call_claude(prompt, 1500)) or {}

# ═══════════════════════════════════
# 2단계: 개별 사업 분석
# ═══════════════════════════════════
def full_business_analysis(cluster):
    prompt = f"""
다음 불편함을 분석해서 JSON으로만 응답. 다른 텍스트 없이.
숫자 항목은 반드시 정수만 입력.

카테고리: {cluster.get('category')}
불편함: {cluster.get('pain_point')}
타겟: {cluster.get('target_users')}

{{
  "build_decision": "TRAFFIC_TOOL 또는 STANDALONE_SAAS 또는 APP_PROGRAM",
  "build_reason": "한 문장",
  "product": {{
    "name": "제품명",
    "tagline": "한 줄 설명",
    "product_type": "웹앱 또는 크롬확장 또는 모바일앱"
  }},
  "time": {{
    "mvp_days": "7",
    "launch_ready_days": "14",
    "first_revenue_days": "30"
  }},
  "cost": {{
    "monthly_fixed": "월 5,000원",
    "total_3months": "3개월 15,000원"
  }},
  "revenue": {{
    "model": "광고(트래픽) 또는 월정액",
    "price_point": "무료+광고 또는 월 9,900원",
    "month1": "5~15만원",
    "month3": "30~80만원",
    "month6": "80~250만원"
  }},
  "market": {{
    "competition": "낮음 또는 중간 또는 높음",
    "differentiation": "차별점 한 문장",
    "seo_keywords": ["키워드1","키워드2"]
  }},
  "build": {{
    "mvp_features": ["기능1","기능2","기능3"],
    "tech_stack": "HTML/CSS/JS + Vercel",
    "difficulty": "하 또는 중 또는 상",
    "quick_traffic": "첫 100명 유입 방법"
  }},
  "risk": {{
    "main_risk": "리스크 한 문장",
    "risk_level": "낮음 또는 중간 또는 높음"
  }},
  "score": {{
    "overall": 8,
    "market_potential": 7,
    "build_ease": 9,
    "revenue_speed": 6,
    "competition_advantage": 8
  }}
}}
"""
    result = parse_json(call_claude(prompt, 1200)) or {}
    if "score" in result:
        sc = result["score"]
        result["score"] = {
            "overall": safe_int(sc.get("overall"), 5),
            "market_potential": safe_int(sc.get("market_potential"), 5),
            "build_ease": safe_int(sc.get("build_ease"), 5),
            "revenue_speed": safe_int(sc.get("revenue_speed"), 5),
            "competition_advantage": safe_int(sc.get("competition_advantage"), 5)
        }
    else:
        result["score"] = {"overall":5,"market_potential":5,"build_ease":5,"revenue_speed":5,"competition_advantage":5}
    return result

# ═══════════════════════════════════
# 3단계: 누적 비교 점수 산정 (핵심!)
# ═══════════════════════════════════
def compare_all_ideas(all_ideas):
    """
    누적된 모든 아이디어를 동시에 비교해서
    상대적 점수를 재산정. 진짜 1등이 명확하게 나옴.
    """
    if len(all_ideas) < 2:
        return all_ideas

    # 비교용 요약 생성
    summaries = []
    for i, idea in enumerate(all_ideas[:20]):  # 최대 20개 비교
        ba = idea.get("business_analysis", {})
        rev = ba.get("revenue", {})
        cost = ba.get("cost", {})
        tim = ba.get("time", {})
        mkt = ba.get("market", {})
        bld = ba.get("build", {})
        risk = ba.get("risk", {})
        summaries.append(
            f"{i+1}. [{idea.get('category')}] {ba.get('product',{}).get('name','')}\n"
            f"   수익모델: {rev.get('model','')} / 6개월수익: {rev.get('month6','')}\n"
            f"   월고정비: {cost.get('monthly_fixed','')} / MVP: {tim.get('mvp_days','')}일\n"
            f"   경쟁: {mkt.get('competition','')} / 난이도: {bld.get('difficulty','')} / 리스크: {risk.get('risk_level','')}\n"
            f"   차별점: {mkt.get('differentiation','')}"
        )

    prompt = f"""
아래 {len(summaries)}개 아이디어를 서로 비교해서 상대적 점수를 매겨주세요.

평가 기준:
- 수익성: 6개월 후 예상 수익이 높을수록 높은 점수
- 제작용이성: 개발 기간이 짧고 난이도가 낮을수록 높은 점수
- 수익속도: 첫 수익까지 기간이 짧을수록 높은 점수
- 경쟁우위: 경쟁이 낮고 차별점이 명확할수록 높은 점수
- 종합: 위 4가지를 종합한 점수

중요: 같은 점수를 주지 말고 반드시 차별화해서 점수를 매길 것.
최고점은 9~10, 최저점은 1~4가 나와야 함.

아이디어 목록:
{chr(10).join(summaries)}

JSON으로만 응답:
{{
  "scores": [
    {{
      "index": 1,
      "overall": 9,
      "market_potential": 8,
      "build_ease": 9,
      "revenue_speed": 7,
      "competition_advantage": 8,
      "rank": 1,
      "rank_reason": "왜 이 순위인지 한 문장"
    }}
  ]
}}
"""
    result = parse_json(call_claude(prompt, 1500))
    if not result or "scores" not in result:
        return all_ideas

    # 점수 업데이트
    scores_map = {s["index"]: s for s in result["scores"]}
    for i, idea in enumerate(all_ideas[:20]):
        sc_data = scores_map.get(i+1)
        if sc_data and "business_analysis" in idea:
            idea["business_analysis"]["score"] = {
                "overall": safe_int(sc_data.get("overall"), 5),
                "market_potential": safe_int(sc_data.get("market_potential"), 5),
                "build_ease": safe_int(sc_data.get("build_ease"), 5),
                "revenue_speed": safe_int(sc_data.get("revenue_speed"), 5),
                "competition_advantage": safe_int(sc_data.get("competition_advantage"), 5)
            }
            idea["business_analysis"]["rank"] = safe_int(sc_data.get("rank"), i+1)
            idea["business_analysis"]["rank_reason"] = sc_data.get("rank_reason", "")
            idea["is_new"] = idea.get("is_new", False)

    return all_ideas

# ═══════════════════════════════════
# 4단계: Claude 개발 프롬프트
# ═══════════════════════════════════
def generate_claude_prompt(cluster, ba):
    prod = ba.get("product", {})
    bld  = ba.get("build", {})
    rev  = ba.get("revenue", {})
    mkt  = ba.get("market", {})

    prompt = f"""
다음 제품을 Claude Code에서 바로 개발 시작할 수 있는 완전한 개발 지시서를 작성해주세요.

제품명: {prod.get('name','')}
설명: {prod.get('tagline','')}
불편함: {cluster.get('pain_point','')}
타겟: {cluster.get('target_users','')}
기술 스택: {bld.get('tech_stack','')}
수익 모델: {rev.get('model','')} / {rev.get('price_point','')}
MVP 기능: {', '.join(bld.get('mvp_features',[]))}
차별점: {mkt.get('differentiation','')}

아래 9개 섹션 전부 포함. 프롬프트 본문만 출력:

[1. 이 제품이 존재해야 하는 이유]
어떤 사람이 어떤 순간에 필요로 하는가. 현재 대안이 왜 부족한가. 사용 후 느껴야 할 감정.

[2. 사용자 경험 흐름]
첫 접속부터 가치를 얻기까지 단계별로.

[3. 입력 설계]
받아야 할 정보와 이유. 입력 방식. 기본값과 예시.

[4. 출력 설계]
"이게 다르다"고 느끼는 출력 형태. 각 결과물 설명. 복사/저장 UX.

[5. UI/UX 상세]
레이아웃, 색상, 인터랙션, 모바일 반응형.

[6. 내부 AI 프롬프트 설계]
시스템 프롬프트 전문. 입력 가공. 출력 JSON 구조.

[7. 기술 구현]
파일 구조. 라이브러리 CDN. API 키 관리. 에러 처리.

[8. 수익화]
무료/유료 구분. 제한 구현.

[9. 배포 및 첫 유입]
Vercel 배포. SEO. 첫 방문자 100명 전략.
"""
    return call_claude(prompt, max_tokens=2500) or ""

# ═══════════════════════════════════
# 5단계: 오늘의 추천
# ═══════════════════════════════════
def generate_daily_recommendation(top_ideas):
    summary = [
        f"- {c.get('category')}: {c.get('business_analysis',{}).get('product',{}).get('name','')} "
        f"(종합 {c.get('business_analysis',{}).get('score',{}).get('overall','?')}/10, "
        f"누적순위 {c.get('business_analysis',{}).get('rank','?')}위)"
        for c in top_ideas[:5]
    ]
    prompt = f"""
오늘 아이디어 (누적 비교 점수 적용):
{chr(10).join(summary)}

가장 먼저 시작할 1개 추천. JSON으로만:
{{
  "recommended_category": "추천 카테고리명",
  "why_first": "왜 이것을 먼저 해야 하는지",
  "tomorrow_action": "내일 당장 할 첫 번째 행동",
  "day7_goal": "7일 후 목표",
  "day30_goal": "30일 후 목표",
  "success_signal": "성공 신호"
}}
"""
    return parse_json(call_claude(prompt, 600)) or {}

# ═══════════════════════════════════
# 메인
# ═══════════════════════════════════
def run_analysis():
    print(f"\n🧠 분석 시작 ({now_kst().strftime('%Y-%m-%d %H:%M KST')})")
    print("─" * 50)

    if not os.path.exists("data/raw_posts.json"):
        print("❌ raw_posts.json 없음")
        return

    with open("data/raw_posts.json", "r", encoding="utf-8") as f:
        all_posts = json.load(f)

    today = now_kst().strftime("%Y-%m-%d")
    yesterday = (now_kst() - timedelta(days=1)).strftime("%Y-%m-%d")
    recent = [p for p in all_posts if p.get("date","") >= yesterday] or all_posts[-50:]

    print(f"   분석 대상: {len(recent)}개")

    # 1단계: 클러스터링
    print("   🔍 [1/4] 클러스터링...")
    base = analyze_posts(recent)
    clusters = base.get("clusters", [])
    print(f"   → {len(clusters)}개 카테고리")
    time.sleep(1)

    # 2단계: 개별 사업 분석
    top5 = sorted(clusters, key=lambda x: x.get("urgency_score",0), reverse=True)[:5]
    print(f"   🏗  [2/4] 상위 {len(top5)}개 개별 분석...")
    for i, c in enumerate(top5):
        print(f"      [{i+1}/{len(top5)}] {c.get('category')} 분석...")
        ba = full_business_analysis(c)
        print(f"      [{i+1}/{len(top5)}] {c.get('category')} 프롬프트 생성...")
        ba["claude_prompt"] = generate_claude_prompt(c, ba)
        c["business_analysis"] = ba
        c["is_new"] = True  # 오늘 신규 표시
        c["date"] = today
        time.sleep(1.5)

    # 누적 아이디어 불러오기
    accumulated_file = "data/accumulated_ideas.json"
    accumulated = []
    if os.path.exists(accumulated_file):
        with open(accumulated_file, "r", encoding="utf-8") as f:
            try:
                accumulated = json.load(f)
            except:
                accumulated = []

    # 오늘 신규 아이디어 추가 (중복 카테고리 제거)
    existing_cats = {a.get("category") for a in accumulated}
    for c in top5:
        if c.get("category") not in existing_cats:
            accumulated.append(c)
        else:
            # 기존 것 업데이트 (더 최신 분석으로)
            for j, a in enumerate(accumulated):
                if a.get("category") == c.get("category"):
                    accumulated[j] = c
                    break

    # 30일 이상 된 것 제거
    thirty_days_ago = (now_kst() - timedelta(days=30)).strftime("%Y-%m-%d")
    accumulated = [a for a in accumulated if a.get("date","") >= thirty_days_ago]

    # 3단계: 누적 비교 점수 산정
    print(f"   📊 [3/4] 누적 {len(accumulated)}개 아이디어 비교 점수 산정...")
    accumulated = compare_all_ideas(accumulated)
    time.sleep(1)

    # 누적 저장
    with open(accumulated_file, "w", encoding="utf-8") as f:
        json.dump(accumulated, f, ensure_ascii=False, indent=2)

    # 종합 점수 기준 정렬
    accumulated_sorted = sorted(
        accumulated,
        key=lambda x: x.get("business_analysis",{}).get("score",{}).get("overall",0),
        reverse=True
    )

    # 오늘 신규만 따로
    today_new = [a for a in accumulated_sorted if a.get("is_new") and a.get("date")==today]

    # 4단계: 추천
    print("   ⭐ [4/4] 추천 생성...")
    rec = generate_daily_recommendation(accumulated_sorted[:5])
    time.sleep(1)

    # 통계
    stats = {
        "total_posts": len(all_posts),
        "today_posts": len([p for p in all_posts if p.get("date")==today]),
        "accumulated_ideas": len(accumulated),
        "sources": {}, "languages": {"ko":0,"en":0}
    }
    for p in recent:
        src = p.get("source","unknown")
        stats["sources"][src] = stats["sources"].get(src,0)+1
        lang = p.get("language","en")
        stats["languages"][lang] = stats["languages"].get(lang,0)+1

    result = {
        "generated_at": now_kst().strftime("%Y-%m-%d %H:%M KST"),
        "date": today,
        "stats": stats,
        "clusters": clusters,
        "top_ideas": accumulated_sorted[:5],      # 누적 TOP 5
        "today_new": today_new,                    # 오늘 신규
        "all_accumulated": accumulated_sorted,     # 전체 누적
        "daily_recommendation": rec,
        "top_insight": base.get("top_insight",""),
        "trending_topics": base.get("trending_topics",[])
    }

    os.makedirs("data", exist_ok=True)
    with open("data/analysis.json","w",encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 히스토리
    history = []
    if os.path.exists("data/history.json"):
        with open("data/history.json","r",encoding="utf-8") as f:
            try: history = json.load(f)
            except: pass

    history = [h for h in history if h.get("date")!=today]
    history.append({
        "date": today,
        "total_posts": stats["total_posts"],
        "today_posts": stats["today_posts"],
        "accumulated_ideas": len(accumulated),
        "top_category": accumulated_sorted[0].get("category","") if accumulated_sorted else "",
        "top_score": accumulated_sorted[0].get("business_analysis",{}).get("score",{}).get("overall",0) if accumulated_sorted else 0
    })
    history = history[-60:]
    with open("data/history.json","w",encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료! ({now_kst().strftime('%H:%M KST')})")
    if accumulated_sorted:
        top = accumulated_sorted[0]
        print(f"   누적 1위: {top.get('category')} — {top.get('business_analysis',{}).get('product',{}).get('name','')}")

if __name__ == "__main__":
    run_analysis()
