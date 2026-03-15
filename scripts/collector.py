"""
IDEA RADAR - 데이터 수집 스크립트 v3
소스: Reddit RSS + HackerNews + Indie Hackers + Dev.to + 네이버카페 + 클리앙 + Product Hunt
전부 무료, API 키 불필요 (Reddit API 키 있으면 더 많이 수집)
"""

import praw
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta, timezone
import time
import re

KST = timezone(timedelta(hours=9))
def now_kst():
    return datetime.now(KST)

REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = "IdeaRadar/1.0"

KEYWORDS_EN = [
    "is there a tool", "wish there was", "anyone know a way",
    "looking for a tool", "pain point", "frustrated with",
    "would pay for", "manual process", "can't find",
    "does anyone have", "how do you automate", "is there an app",
    "need a way to", "tired of", "annoying that",
    "would love a", "anyone built", "thinking of building",
    "build a saas", "saas idea", "startup idea", "side project",
    "I wish", "why isn't there", "why is there no",
    "problem with", "struggle with", "looking for software",
    "is there a way", "how to automate", "anyone else find"
]

KEYWORDS_KR = [
    "불편", "필요해", "있으면 좋겠다", "가능한가요",
    "어떻게 하나요", "만들고 싶다", "자동화하고 싶",
    "이런 서비스", "왜 없지", "SaaS", "앱 만들",
    "개발하고 싶", "아이디어", "서비스 만들", "불편함",
    "문제점", "개선", "자동화", "툴이 없", "프로그램이 없"
]

SUBREDDITS = [
    "Entrepreneur", "startups", "SaaS", "nocode",
    "indiehackers", "webdev", "smallbusiness",
    "freelance", "side_project", "business"
]

def contains_keyword(text, keywords):
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False

# ═══════════════════════════════════════
# 1. Reddit RSS (API 키 없이 무료)
# ═══════════════════════════════════════
def collect_reddit_rss(days_back=1):
    posts = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; IdeaRadar/1.0)"}

    for sub in SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("children", [])
                for item in items:
                    post = item.get("data", {})
                    title = post.get("title", "")
                    body = post.get("selftext", "")[:300]
                    full_text = f"{title} {body}"
                    if contains_keyword(full_text, KEYWORDS_EN):
                        posts.append({
                            "id": post.get("id", ""),
                            "source": "reddit",
                            "community": f"r/{sub}",
                            "title": title,
                            "content": body,
                            "url": f"https://reddit.com{post.get('permalink','')}",
                            "score": post.get("score", 0),
                            "comments": post.get("num_comments", 0),
                            "date": now_kst().strftime("%Y-%m-%d"),
                            "language": "en"
                        })
            time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️  r/{sub} RSS 오류: {e}")
            continue

    print(f"  ✅ Reddit RSS: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 2. Reddit API (키 있을 때만)
# ═══════════════════════════════════════
def collect_reddit_api(days_back=1):
    posts = []
    if not REDDIT_CLIENT_ID:
        return posts
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)
        for sub_name in SUBREDDITS:
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
                            "date": now_kst().strftime("%Y-%m-%d"),
                            "language": "en"
                        })
                time.sleep(0.5)
            except:
                continue
    except Exception as e:
        print(f"  ⚠️  Reddit API 오류: {e}")
    print(f"  ✅ Reddit API: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 3. Hacker News (완전 무료)
# ═══════════════════════════════════════
def collect_hackernews(days_back=1):
    posts = []
    try:
        date_from = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
        search_terms = ["tool", "app", "saas", "automate", "pain", "startup", "build", "problem"]
        for term in search_terms[:5]:
            url = (
                f"https://hn.algolia.com/api/v1/search_by_date"
                f"?query={term}&tags=story"
                f"&numericFilters=created_at_i>{date_from}"
                f"&hitsPerPage=25"
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
                            "date": now_kst().strftime("%Y-%m-%d"),
                            "language": "en"
                        })
            time.sleep(0.3)
    except Exception as e:
        print(f"  ⚠️  HackerNews 오류: {e}")
    print(f"  ✅ Hacker News: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 4. Indie Hackers (창업자 커뮤니티, 완전 무료)
# ═══════════════════════════════════════
def collect_indiehackers(days_back=1):
    posts = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # Indie Hackers 그룹 피드
        groups = ["", "ideas", "need-help", "product-feedback"]
        for group in groups[:3]:
            url = f"https://www.indiehackers.com/group/{group}" if group else "https://www.indiehackers.com/feed"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # 게시물 제목 추출
                    items = soup.select("a.feed-item__title, a.post__title, h2 a, .title a")
                    for item in items[:20]:
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        if title and contains_keyword(title, KEYWORDS_EN):
                            posts.append({
                                "id": f"ih_{hash(title) % 100000}",
                                "source": "indiehackers",
                                "community": "Indie Hackers",
                                "title": title,
                                "content": "",
                                "url": f"https://www.indiehackers.com{href}" if href.startswith("/") else href,
                                "score": 0,
                                "comments": 0,
                                "date": now_kst().strftime("%Y-%m-%d"),
                                "language": "en"
                            })
                time.sleep(0.5)
            except:
                continue
    except Exception as e:
        print(f"  ⚠️  Indie Hackers 오류: {e}")
    print(f"  ✅ Indie Hackers: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 5. Dev.to (개발자 커뮤니티, API 무료)
# ═══════════════════════════════════════
def collect_devto(days_back=1):
    posts = []
    try:
        # Dev.to 공개 API (키 불필요)
        tags = ["discuss", "help", "productivity", "startup", "webdev"]
        for tag in tags[:4]:
            url = f"https://dev.to/api/articles?tag={tag}&per_page=20&state=fresh"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                articles = resp.json()
                for article in articles:
                    title = article.get("title", "")
                    desc = article.get("description", "")[:200]
                    full_text = f"{title} {desc}"
                    if contains_keyword(full_text, KEYWORDS_EN):
                        posts.append({
                            "id": f"devto_{article.get('id')}",
                            "source": "devto",
                            "community": "Dev.to",
                            "title": title,
                            "content": desc,
                            "url": article.get("url", ""),
                            "score": article.get("public_reactions_count", 0),
                            "comments": article.get("comments_count", 0),
                            "date": now_kst().strftime("%Y-%m-%d"),
                            "language": "en"
                        })
            time.sleep(0.3)
    except Exception as e:
        print(f"  ⚠️  Dev.to 오류: {e}")
    print(f"  ✅ Dev.to: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 6. 네이버 카페 (창업/스타트업)
# ═══════════════════════════════════════
def collect_naver_cafe(days_back=1):
    posts = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9"
        }
        # 네이버 카페 검색 (공개 게시물)
        keywords = ["불편한 서비스", "이런 앱 없나", "자동화하고 싶", "창업 아이디어"]
        for kw in keywords[:2]:
            url = f"https://search.naver.com/search.naver?where=article&query={requests.utils.quote(kw)}&sm=tab_opt&nso=so%3Ar%2Cp%3A1d"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".total_area .detail_box, .cafe_area .total_tit")
                for item in items[:10]:
                    title_el = item.select_one("a.total_tit, a.api_txt_lines")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    if title and len(title) > 5:
                        posts.append({
                            "id": f"naver_{hash(title) % 100000}",
                            "source": "naver_cafe",
                            "community": "네이버카페",
                            "title": title,
                            "content": "",
                            "url": href,
                            "score": 0,
                            "comments": 0,
                            "date": now_kst().strftime("%Y-%m-%d"),
                            "language": "ko"
                        })
            time.sleep(1)
    except Exception as e:
        print(f"  ⚠️  네이버 카페 오류: {e}")
    print(f"  ✅ 네이버 카페: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 7. 클리앙
# ═══════════════════════════════════════
def collect_clien(days_back=1):
    posts = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        boards = [("sms", "사고사요"), ("tips", "팁과강좌"), ("cm", "자유게시판")]
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
                            "date": now_kst().strftime("%Y-%m-%d"),
                            "language": "ko"
                        })
        time.sleep(1)
    except Exception as e:
        print(f"  ⚠️  클리앙 오류: {e}")
    print(f"  ✅ 클리앙: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 8. Product Hunt
# ═══════════════════════════════════════
def collect_producthunt(days_back=1):
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
                        "id": f"ph_{hash(title.get_text()) % 100000}",
                        "source": "producthunt",
                        "community": "Product Hunt",
                        "title": title.get_text(strip=True),
                        "content": BeautifulSoup(desc.get_text() if desc else "", "html.parser").get_text()[:300],
                        "url": link.get_text(strip=True),
                        "score": 0,
                        "comments": 0,
                        "date": now_kst().strftime("%Y-%m-%d"),
                        "language": "en"
                    })
    except Exception as e:
        print(f"  ⚠️  Product Hunt 오류: {e}")
    print(f"  ✅ Product Hunt: {len(posts)}개 수집")
    return posts

# ═══════════════════════════════════════
# 메인
# ═══════════════════════════════════════
def run_collection(days_back=1):
    print(f"\n🚀 데이터 수집 시작 ({now_kst().strftime('%Y-%m-%d %H:%M KST')})")
    print(f"   수집 기간: 최근 {days_back}일")
    print("─" * 50)

    all_posts = []

    # Reddit
    if REDDIT_CLIENT_ID:
        print("  📡 Reddit API 키 있음 → API 방식")
        all_posts += collect_reddit_api(days_back)
    else:
        print("  📡 Reddit API 키 없음 → RSS 방식")
        all_posts += collect_reddit_rss(days_back)

    all_posts += collect_hackernews(days_back)
    all_posts += collect_indiehackers(days_back)
    all_posts += collect_devto(days_back)
    all_posts += collect_naver_cafe(days_back)
    all_posts += collect_clien(days_back)
    all_posts += collect_producthunt(days_back)

    # 중복 제거
    seen = set()
    unique = []
    for post in all_posts:
        key = post.get("url") or post.get("id")
        if key and key not in seen:
            seen.add(key)
            unique.append(post)

    print(f"\n📊 총 {len(unique)}개 수집 완료 (중복 제거 후)")

    # 기존 데이터 불러오기
    raw_file = "data/raw_posts.json"
    existing = []
    if os.path.exists(raw_file):
        with open(raw_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except:
                existing = []

    thirty_days_ago = (now_kst() - timedelta(days=30)).strftime("%Y-%m-%d")
    existing = [p for p in existing if p.get("date","") >= thirty_days_ago]
    existing_ids = {p.get("id") for p in existing}
    new_posts = [p for p in unique if p.get("id") not in existing_ids]
    combined = existing + new_posts

    os.makedirs("data", exist_ok=True)
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"✅ 신규 {len(new_posts)}개 추가 → 총 {len(combined)}개 저장")
    return combined

if __name__ == "__main__":
    import sys
    days = 14 if "--init" in sys.argv else 1
    run_collection(days_back=days)
