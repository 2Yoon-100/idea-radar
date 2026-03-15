"""
IDEA RADAR - AI 분석 스크립트 v4
KST 시간 + score 안정화 + Reddit RSS 대응
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
    # 코드블록 제거
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    # 직접 파싱
    try:
        return json.loads(text)
    except:
        pass
    # 중괄호 범위 추출
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
    """숫자 추출 - 텍스트가 섞여있어도 처리"""
    if isinstance(val, int):
        return max(1, min(10, val))
    if isinstance(val, float):
        return max(1, min(10, int(val)))
    if isinstance(val, str):
        m = re.search(r'\d+', val)
        if m:
            return max(1, min(10, int(m.group())))
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

JSON으로만 응답 (다른 텍스트 없이):
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
# 2단계: 사업 분석 (score 안정화)
# ═══════════════════════════════════
def full_business_analysis(cluster):
    prompt = f"""
다음 불편함을 분석해서 JSON으로만 응답. 다른 텍스트 없이.
숫자 항목은 반드시 숫자(정수)만 입력.

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
    "month1": "5~15만원 (반드시 이 형식으로, 숫자만 쓰지 말것)",
    "month3": "30~80만원 (반드시 이 형식으로, 숫자만 쓰지 말것)",
    "month6": "80~250만원 (반드시 이 형식으로, 숫자만 쓰지 말것)"
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

    # score 정수 변환 보장
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
        result["score"] = {
            "overall": 5, "market_potential": 5,
            "build_ease": 5, "revenue_speed": 5,
            "competition_advantage": 5
        }
    return result

# ═══════════════════════════════════
# 2-B: Claude 개발 프롬프트 생성
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

아래 9개 섹션 전부 포함해서 작성. 프롬프트 본문만 출력:

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
# 3단계: 오늘의 추천
# ═══════════════════════════════════
def generate_daily_recommendation(top_ideas):
    summary = [
        f"- {c.get('category')}: {c.get('business_analysis',{}).get('product',{}).get('name','')} "
        f"(긴급도 {c.get('urgency_score')}/10, 종합 {c.get('business_analysis',{}).get('score',{}).get('overall','?')}/10)"
        for c in top_ideas[:5]
    ]
    prompt = f"""
오늘 아이디어:
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

    print("   🔍 [1/3] 클러스터링...")
    base = analyze_posts(recent)
    clusters = base.get("clusters", [])
    print(f"   → {len(clusters)}개 카테고리")
    time.sleep(1)

    top5 = sorted(clusters, key=lambda x: x.get("urgency_score",0), reverse=True)[:5]
    print(f"   🏗  [2/3] 상위 {len(top5)}개 사업 분석...")
    for i, c in enumerate(top5):
        print(f"      [{i+1}/{len(top5)}] {c.get('category')} 분석...")
        ba = full_business_analysis(c)
        print(f"      [{i+1}/{len(top5)}] {c.get('category')} 프롬프트 생성...")
        ba["claude_prompt"] = generate_claude_prompt(c, ba)
        c["business_analysis"] = ba
        time.sleep(1.5)

    print("   ⭐ [3/3] 추천 생성...")
    rec = generate_daily_recommendation(top5)
    time.sleep(1)

    stats = {
        "total_posts": len(all_posts),
        "today_posts": len([p for p in all_posts if p.get("date")==today]),
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
        "top_ideas": top5,
        "daily_recommendation": rec,
        "top_insight": base.get("top_insight",""),
        "trending_topics": base.get("trending_topics",[])
    }

    os.makedirs("data", exist_ok=True)
    with open("data/analysis.json","w",encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

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

    print(f"\n✅ 완료! ({now_kst().strftime('%H:%M KST')})")
    print(f"   추천: {rec.get('recommended_category','N/A')}")

if __name__ == "__main__":
    run_analysis()
