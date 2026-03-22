"""
IDEA RADAR - AI 분석 스크립트 v3
종합 사업 판단 + Claude Opus/Sonnet 즉시 사용 프롬프트 자동 생성
"""

import json, os, requests, re, time
from datetime import datetime, timedelta

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
        "model": "claude-haiku-4-5-20251001",  # 분석은 Haiku로 (저비용)
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        resp = requests.post(CLAUDE_API_URL, headers=headers, json=body, timeout=60)
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
    except Exception as e:
        print(f"❌ {e}")
    return None

def parse_json(text):
    if not text:
        return None
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except:
        pass
    return None

# ═══════════════════════════════════════════════
# 1단계: 게시물 클러스터링
# ═══════════════════════════════════════════════
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
      "post_count": 언급횟수,
      "urgency_score": 1~10,
      "target_users": "타겟 사용자",
      "example_posts": [번호들]
    }}
  ],
  "trending_topics": ["키워드1","키워드2","키워드3","키워드4","키워드5"],
  "top_insight": "오늘 가장 중요한 인사이트 한 문장"
}}
"""
    return parse_json(call_claude(prompt, 1500)) or {}

# ═══════════════════════════════════════════════
# 2-A: 프로덕션급 Claude 개발 프롬프트 생성
# ═══════════════════════════════════════════════
def generate_claude_prompt(cluster, ba):
    """
    Claude Opus/Sonnet에 바로 붙여넣을 수 있는 프로덕션급 프롬프트.
    기능 나열이 아닌, 사용자 심리/경험/차별화까지 담은 실전 프롬프트.
    """
    prod = ba.get("product", {})
    bld  = ba.get("build", {})
    rev  = ba.get("revenue", {})
    mkt  = ba.get("market", {})

    prompt = f"""
다음 제품을 Claude Code 또는 Claude.ai에서 바로 개발 시작할 수 있는
완전하고 구체적인 개발 지시서를 작성해주세요.

── 제품 정보 ──
제품명: {prod.get('name','')}
한 줄 설명: {prod.get('tagline','')}
해결하는 불편함: {cluster.get('pain_point','')}
타겟 사용자: {cluster.get('target_users','')}
제품 유형: {prod.get('product_type','')}
기술 스택: {bld.get('tech_stack','')}
수익 모델: {rev.get('model','')} / {rev.get('price_point','')}
MVP 기능: {', '.join(bld.get('mvp_features',[]))}
경쟁 차별점: {mkt.get('differentiation','')}

── 요구사항 ──
아래 9개 섹션 전부 포함. "예시로" "대충" 같은 표현 없이 실제 구현 가능한 수준으로.
프롬프트 본문만 출력. 추가 설명이나 부연 없이.

[1. 이 제품이 존재해야 하는 이유]
어떤 사람이 어떤 구체적 순간에 이 제품을 필요로 하는가.
지금 대안(수작업, 구글 검색 등)이 왜 불충분한가.
이 제품을 쓰고 나서 사용자가 느껴야 할 감정.

[2. 사용자 경험 흐름]
첫 접속부터 첫 번째 가치를 얻기까지 단계별로.
각 단계에서 사용자가 보고 느끼는 것.
재방문하게 만드는 핵심 요소.

[3. 입력 설계]
받아야 할 정보 목록과 각각의 이유.
입력 방식 (텍스트/드롭다운/슬라이더 등).
스마트 기본값과 예시 문구.

[4. 출력 설계]
단순 텍스트가 아닌 "이게 다르다"고 느끼는 출력 형태.
각 결과물에 붙는 설명 (왜 이 결과인지).
복사/저장/공유 UX.

[5. UI/UX 상세]
전체 레이아웃 구조.
색상 테마와 주요 컬러.
핵심 인터랙션 (로딩 상태, 결과 애니메이션, hover 효과).
모바일 반응형 처리.
설명 없이도 바로 쓸 수 있는 UI 원칙.

[6. 내부 AI 프롬프트 설계]
Claude API 사용 시 시스템 프롬프트 전문.
사용자 입력 가공 방법.
출력 JSON 구조와 파싱 방법.

[7. 기술 구현 상세]
파일 구조.
외부 라이브러리 (CDN 링크 포함).
API 키 관리 방법.
에러 처리.

[8. 수익화 구현]
무료/유료 기능 구분.
제한 또는 결제 구현 방법.

[9. 배포 및 첫 유입]
Vercel 배포 단계.
SEO 메타태그.
첫 방문자 100명 유입 방법.
"""
    result = call_claude(prompt, max_tokens=2500)
    return result or ""


# ═══════════════════════════════════════════════
# 2-B: 종합 사업 판단
# ═══════════════════════════════════════════════
def full_business_analysis(cluster):
    prompt = f"""
다음 사용자 불편함을 기반으로 완전한 사업 분석을 해주세요.

카테고리: {cluster.get('category')}
불편함: {cluster.get('pain_point')}
타겟: {cluster.get('target_users')}
긴급도: {cluster.get('urgency_score')}/10

아래 JSON으로만 응답. 모든 항목 반드시 채울 것:

{{
  "build_decision": "TRAFFIC_TOOL 또는 STANDALONE_SAAS 또는 APP_PROGRAM",
  "build_reason": "이 유형이 맞는 이유 한 문장",

  "product": {{
    "name": "제품명 (간결하게)",
    "tagline": "한 줄 설명 (트위터 소개 수준)",
    "core_value": "핵심 가치 제안",
    "product_type": "웹앱 또는 크롬확장 또는 모바일앱 또는 데스크톱 또는 랜딩페이지+툴"
  }},

  "time": {{
    "mvp_days": "MVP 완성까지 일수 (Claude Code 활용 시, 숫자만)",
    "launch_ready_days": "실제 런칭 가능일 (숫자만)",
    "first_revenue_days": "첫 수익 예상일 (숫자만)"
  }},

  "cost": {{
    "dev_cost": "개발 비용 (Claude API 제외, 거의 0원인 경우 0원)",
    "monthly_fixed": "월 고정비 (서버+도메인)",
    "monthly_variable": "월 변동비 (트래픽 증가 시)",
    "total_3months": "3개월 총 예상 비용"
  }},

  "revenue": {{
    "model": "광고(트래픽) 또는 월정액 또는 건당결제 또는 프리미엄",
    "price_point": "가격 (예: 무료+광고, 월 9,900원, 건당 990원)",
    "month1": "1개월 후 예상 월 수익",
    "month3": "3개월 후 예상 월 수익",
    "month6": "6개월 후 예상 월 수익",
    "breakeven": "손익분기점 도달 예상 시점"
  }},

  "market": {{
    "size": "시장 규모 (국내 기준)",
    "competition": "낮음 또는 중간 또는 높음",
    "competitors_kr": ["국내경쟁1","국내경쟁2"],
    "competitors_global": ["해외경쟁1","해외경쟁2"],
    "differentiation": "차별점 한 문장",
    "search_volume": "예상 월 검색량 (구글 기준)",
    "seo_keywords": ["메인키워드","서브키워드1","서브키워드2"]
  }},

  "build": {{
    "mvp_features": ["핵심기능1","핵심기능2","핵심기능3"],
    "tech_stack": "기술 스택 (예: HTML/CSS/JS + Vercel, Next.js + Supabase)",
    "difficulty": "하 또는 중 또는 상",
    "quick_traffic": "첫 방문자 100명 모으는 가장 빠른 방법",
    "growth_hack": "1,000명→10,000명 성장 전략"
  }},

  "risk": {{
    "main_risk": "가장 큰 리스크",
    "risk_level": "낮음 또는 중간 또는 높음",
    "mitigation": "리스크 대응 방법"
  }},

  "score": {{
    "overall": 전체점수(숫자만, 1~10),
    "market_potential": 시장성(숫자만, 1~10),
    "build_ease": 제작용이성(숫자만, 1~10),
    "revenue_speed": 수익속도(숫자만, 1~10),
    "competition_advantage": 경쟁우위(숫자만, 1~10)
  }}
}}
"""
    return parse_json(call_claude(prompt, 1500)) or {}

# ═══════════════════════════════════════════════
# 3단계: 오늘의 최종 추천
# ═══════════════════════════════════════════════
def generate_daily_recommendation(top_ideas):
    summary = []
    for c in top_ideas[:5]:
        bd = c.get("business_analysis", {})
        sc = bd.get("score", {})
        summary.append(
            f"- {c.get('category')}: {bd.get('product',{}).get('name','')} "
            f"(긴급도 {c.get('urgency_score')}/10, 종합점수 {sc.get('overall','?')}/10, "
            f"{bd.get('build_decision','')})"
        )

    prompt = f"""
오늘 분석된 아이디어:
{chr(10).join(summary)}

가장 먼저 시작해야 할 1개를 추천해주세요. JSON으로만:
{{
  "recommended_category": "추천 카테고리명",
  "why_first": "왜 이것을 먼저 해야 하는지 (타이밍, 경쟁, 수익성 기준으로)",
  "tomorrow_action": "내일 당장 할 수 있는 첫 번째 구체적 행동",
  "day7_goal": "7일 후 목표",
  "day30_goal": "30일 후 목표",
  "success_signal": "성공하고 있다는 신호 (예: 일 방문자 50명 돌파)"
}}
"""
    return parse_json(call_claude(prompt, 600)) or {}

# ═══════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════
def run_analysis():
    print(f"\n🧠 Idea Radar 분석 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("─" * 50)

    if not os.path.exists("data/raw_posts.json"):
        print("❌ raw_posts.json 없음. collector.py 먼저 실행하세요.")
        return

    with open("data/raw_posts.json", "r", encoding="utf-8") as f:
        all_posts = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    recent = [p for p in all_posts if p.get("date","") >= yesterday] or all_posts[-50:]

    print(f"   분석 대상: {len(recent)}개 게시물")

    # 1단계
    print("   🔍 [1/3] 클러스터링...")
    base = analyze_posts(recent)
    clusters = base.get("clusters", [])
    print(f"   → {len(clusters)}개 카테고리 발견")
    time.sleep(1)

    # 2단계: 상위 5개 전체 사업 분석
    top5 = sorted(clusters, key=lambda x: x.get("urgency_score",0), reverse=True)[:5]
    print(f"   🏗  [2/3] 상위 {len(top5)}개 종합 사업 분석 중...")
    for i, c in enumerate(top5):
        print(f"      [{i+1}/{len(top5)}] {c.get('category')} 사업 분석...")
        ba = full_business_analysis(c)

        print(f"      [{i+1}/{len(top5)}] {c.get('category')} 개발 프롬프트 생성...")
        claude_prompt = generate_claude_prompt(c, ba)
        ba["claude_prompt"] = claude_prompt

        c["business_analysis"] = ba
        time.sleep(1.5)

    # 3단계
    print("   ⭐ [3/3] 오늘의 최종 추천 생성...")
    rec = generate_daily_recommendation(top5)
    time.sleep(1)

    # 통계
    stats = {
        "total_posts": len(all_posts),
        "today_posts": len([p for p in all_posts if p.get("date")==today]),
        "sources": {}, "languages": {"ko":0,"en":0}, "subreddits": {}
    }
    for p in recent:
        src = p.get("source","unknown")
        stats["sources"][src] = stats["sources"].get(src,0)+1
        lang = p.get("language","en")
        stats["languages"][lang] = stats["languages"].get(lang,0)+1
        if src == "reddit" and p.get("subreddit"):
            sub = p["subreddit"]
            stats["subreddits"][sub] = stats["subreddits"].get(sub,0)+1

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date": today,
        "stats": stats,
        "clusters": clusters,
        "top_ideas": top5,
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
        "ideas_count": len(clusters),
        "top_category": top5[0].get("category","") if top5 else "",
        "top_score": top5[0].get("urgency_score",0) if top5 else 0,
        "recommendation": rec.get("recommended_category","")
    })
    history = history[-60:]
    with open("data/history.json","w",encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 분석 완료!")
    print(f"   오늘 추천: {rec.get('recommended_category','N/A')}")
    print(f"   이유: {rec.get('why_first','')}")

if __name__ == "__main__":
    run_analysis()
