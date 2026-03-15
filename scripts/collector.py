"""
IDEA RADAR - 데이터 수집 스크립트
매일 자동으로 커뮤니티에서 불편함/아이디어를 수집합니다.
"""

import praw
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import time
import re

# ───────────────────────────────────────────────
# 설정값 (GitHub Secrets에서 자동으로 불러옴)
# ───────────────────────────────────────────────
REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = "IdeaRadar/1.0 by YourRedditUsername"

# ───────────────────────────────────────────────
# 키워드 필터 (이 단어가 포함된 게시물만 수집)
# ───────────────────────────────────────────────
KEYWORDS_EN = [
    "is there a tool", "wish there was", "anyone know a way",
    "looking for a tool", "pain point", "frustrated with",
    "would pay for", "manual process", "can't find",
    "does anyone have", "how do you automate", "is there an app",
    "need a way to", "tired of", "annoying that",
    "would love a", "anyone built", "thinking of building",
    "build a saas", "saas idea", "startup idea"
]

KEYWORDS_KR = [
    "불편", "필요해", "있으면 좋겠다", "가능한가요",
    "어떻게 하나요", "만들고 싶다", "자동화하고 싶",
    "이런 서비스", "왜 없지", "SaaS", "앱 만들",
    "개발하고 싶", "아이디어", "서비스 만들", "불편함"
]

# ───────────────────────────────────────────────
# 수집 대상 Reddit 서브레딧
# ───────────────────────────────────────────────
SUBREDDITS = [
    "Entrepreneur", "startups", "SaaS", "nocode",
    "indiehackers", "webdev", "smallbusiness",
    "freelance", "side_project", "business"
]

def contains_keyword(text, keywords):
    """텍스트에 키워드가 포함되어 있는지 확인"""
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False

# ═══════════════════════════════════════════════
# 1. Reddit 수집
# ═══════════════════════════════════════════════
def collect_reddit(days_back=1):
    """Reddit에서 게시물 수집"""
    posts = []
    
    if not REDDIT_CLIENT_ID:
        print("⚠️  Reddit API 키가 없습니다. 건너뜁니다.")
        return posts
    
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)
        
        for sub_name in SUBREDDITS:
            print(f"  📥 Reddit r/{sub_name} 수집 중...")
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.new(limit=100):
                    post_time = datetime.utcfromtimestamp(post.created_utc)
                    if post_time < cutoff_time:
                        break
                    
                    full_text = f"{post.title} {post.selftext}"
                    
                    if contains_keyword(full_text, KEYWORDS_EN):
                        posts.append({
                            "id": post.id,
                            "source": "reddit",
                            "community": f"r/{sub_name}",
                            "title": post.title,
                            "content": post.selftext[:500],
                            "url": f"https://reddit.com{post.permalink}",
                            "score": post.score,
                            "comments": post.num_comments,
                            "date": post_time.strftime("%Y-%m-%d"),
                            "language": "en"
                        })
                time.sleep(0.5)  # API 제한 방지
            except Exception as e:
                print(f"  ⚠️  r/{sub_name} 오류: {e}")
                continue
    except Exception as e:
        print(f"  ❌ Reddit 연결 오류: {e}")
    
    print(f"  ✅ Reddit: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════════════
# 2. Hacker News 수집 (완전 무료, API 키 불필요)
# ═══════════════════════════════════════════════
def collect_hackernews(days_back=1):
    """Hacker News에서 수집 (Algolia API - 완전 무료)"""
    posts = []
    
    try:
        # 날짜 범위 설정
        date_from = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
        
        # 'Ask HN' 게시물 검색
        search_terms = ["tool", "app", "service", "saas", "automate", "pain"]
        
        for term in search_terms[:3]:  # API 부담 줄이기
            url = (
                f"https://hn.algolia.com/api/v1/search_by_date"
                f"?query=Ask+HN+{term}&tags=story"
                f"&numericFilters=created_at_i>{date_from}"
                f"&hitsPerPage=30"
            )
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for hit in data.get("hits", []):
                    title = hit.get("title", "")
                    if contains_keyword(title, KEYWORDS_EN) or "Ask HN" in title:
                        posts.append({
                            "id": hit.get("objectID"),
                            "source": "hackernews",
                            "community": "Hacker News",
                            "title": title,
                            "content": hit.get("story_text", "")[:500] if hit.get("story_text") else "",
                            "url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                            "score": hit.get("points", 0),
                            "comments": hit.get("num_comments", 0),
                            "date": datetime.utcnow().strftime("%Y-%m-%d"),
                            "language": "en"
                        })
            time.sleep(0.3)
    except Exception as e:
        print(f"  ⚠️  HackerNews 오류: {e}")
    
    print(f"  ✅ Hacker News: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════════════
# 3. 클리앙 수집 (한국 커뮤니티)
# ═══════════════════════════════════════════════
def collect_clien(days_back=1):
    """클리앙 사고사요 게시판 수집"""
    posts = []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # 클리앙 사고사요, 팁과강좌 게시판
        boards = [
            ("sms", "사고사요"),
            ("tips", "팁과강좌"),
        ]
        
        for board_id, board_name in boards:
            url = f"https://www.clien.net/service/board/{board_id}?&od=T31&category=0&po=0"
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".list_item.symph_row")
                
                for item in items[:30]:
                    title_el = item.select_one(".subject_fixed")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    link_el = item.select_one("a.list_subject")
                    link = "https://www.clien.net" + link_el["href"] if link_el else ""
                    
                    if contains_keyword(title, KEYWORDS_KR):
                        posts.append({
                            "id": link.split("/")[-1] if link else str(len(posts)),
                            "source": "clien",
                            "community": f"클리앙/{board_name}",
                            "title": title,
                            "content": "",
                            "url": link,
                            "score": 0,
                            "comments": 0,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "language": "ko"
                        })
        time.sleep(1)
    except Exception as e:
        print(f"  ⚠️  클리앙 오류: {e}")
    
    print(f"  ✅ 클리앙: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════════════
# 4. Product Hunt 수집 (완전 무료)
# ═══════════════════════════════════════════════
def collect_producthunt(days_back=1):
    """Product Hunt 최신 제품 수집 (경쟁/트렌드 파악)"""
    posts = []
    
    try:
        url = "https://www.producthunt.com/feed"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.find_all("item")[:20]
            
            for item in items:
                title = item.find("title")
                link = item.find("link")
                desc = item.find("description")
                
                if title and link:
                    posts.append({
                        "id": str(len(posts)),
                        "source": "producthunt",
                        "community": "Product Hunt",
                        "title": title.get_text(strip=True),
                        "content": BeautifulSoup(desc.get_text() if desc else "", "html.parser").get_text()[:300],
                        "url": link.get_text(strip=True),
                        "score": 0,
                        "comments": 0,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "language": "en"
                    })
    except Exception as e:
        print(f"  ⚠️  Product Hunt 오류: {e}")
    
    print(f"  ✅ Product Hunt: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════
def run_collection(days_back=1):
    """전체 수집 실행"""
    print(f"\n🚀 데이터 수집 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"   수집 기간: 최근 {days_back}일")
    print("─" * 50)
    
    all_posts = []
    
    # 각 소스에서 수집
    all_posts += collect_reddit(days_back)
    all_posts += collect_hackernews(days_back)
    all_posts += collect_clien(days_back)
    all_posts += collect_producthunt(days_back)
    
    # 중복 제거 (같은 URL)
    seen_urls = set()
    unique_posts = []
    for post in all_posts:
        if post["url"] not in seen_urls:
            seen_urls.add(post["url"])
            unique_posts.append(post)
    
    print(f"\n📊 총 {len(unique_posts)}개 수집 완료 (중복 제거 후)")
    
    # 기존 데이터 불러오기
    raw_file = "data/raw_posts.json"
    existing = []
    if os.path.exists(raw_file):
        with open(raw_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except:
                existing = []
    
    # 기존 데이터에 새 데이터 추가 (최근 30일치만 유지)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    existing = [p for p in existing if p.get("date", "") >= thirty_days_ago]
    
    existing_ids = {p.get("id") for p in existing}
    new_posts = [p for p in unique_posts if p.get("id") not in existing_ids]
    
    combined = existing + new_posts
    
    # 저장
    os.makedirs("data", exist_ok=True)
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 신규 {len(new_posts)}개 추가 → 총 {len(combined)}개 저장")
    return combined

if __name__ == "__main__":
    import sys
    days = 14 if "--init" in sys.argv else 1
    run_collection(days_back=days)
