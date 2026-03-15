# 💡 Idea Radar — 설정 가이드
## (코딩 몰라도 30분이면 완성됩니다)

---

## 📋 필요한 것 (전부 무료 or 거의 무료)

| 항목 | 비용 | 소요시간 |
|------|------|----------|
| GitHub 계정 | 무료 | 5분 |
| Reddit API 키 | 무료 | 5분 |
| Claude API 키 | 월 $1~3 | 3분 |
| 총합 | **월 약 1,500~4,000원** | **30분** |

---

## 🚀 STEP 1 — GitHub 저장소 만들기

1. **https://github.com** 에서 계정 가입 (이미 있으면 로그인)

2. 오른쪽 상단 **[+]** 버튼 클릭 → **New repository**

3. 아래처럼 입력:
   - Repository name: `idea-radar`
   - 공개 설정: **Public** 선택 (꼭 Public이어야 대시보드가 데이터를 읽을 수 있음)
   - ✅ **Add a README file** 체크

4. **Create repository** 클릭

---

## 🚀 STEP 2 — 파일 업로드

1. 방금 만든 저장소 페이지에서 **Add file → Upload files** 클릭

2. 이 폴더(`idea-radar`) 안의 **모든 파일과 폴더**를 통째로 드래그앤드롭

3. 아래 목록이 다 올라갔는지 확인:
   ```
   .github/workflows/daily.yml
   scripts/collector.py
   scripts/analyzer.py
   dashboard/index.html
   requirements.txt
   ```

4. **Commit changes** 클릭

---

## 🚀 STEP 3 — Reddit API 키 발급 (무료)

1. **https://www.reddit.com** 에서 Reddit 계정 로그인

2. 오른쪽 상단 아이디 클릭 → **Settings**

3. 왼쪽 메뉴에서 **Safety & Privacy** → 아래 스크롤 → **Manage third-party app authorization**

4. 또는 직접 이 주소로 이동: **https://www.reddit.com/prefs/apps**

5. 아래쪽 **create an app** 또는 **create another app** 클릭

6. 아래처럼 입력:
   - name: `IdeaRadar`
   - 타입: **script** 선택
   - description: 비워도 됨
   - redirect uri: `http://localhost:8080`

7. **create app** 클릭

8. 생성되면 두 가지 값 메모:
   - **앱 이름 아래 짧은 코드** = `CLIENT_ID` (예: `aBcDeF123`)
   - **secret** 옆 값 = `CLIENT_SECRET` (예: `xYz789AbcDef`)

---

## 🚀 STEP 4 — Claude API 키 발급

1. **https://console.anthropic.com** 에서 계정 생성/로그인

2. 왼쪽 메뉴 **API Keys** 클릭

3. **Create Key** 클릭 → 이름 입력 (예: `IdeaRadar`)

4. 생성된 키 복사 (예: `sk-ant-api03-...`)
   > ⚠️ 이 키는 한 번만 보여집니다. 반드시 복사해두세요!

5. 카드 등록: 월 $1~3 정도만 청구됩니다 (Haiku 모델 사용)

---

## 🚀 STEP 5 — GitHub에 API 키 등록

1. GitHub 저장소 페이지에서 **Settings** 탭 클릭

2. 왼쪽 메뉴 **Secrets and variables → Actions** 클릭

3. **New repository secret** 을 눌러 아래 3개 등록:

| Name | Value |
|------|-------|
| `REDDIT_CLIENT_ID` | Reddit에서 복사한 CLIENT_ID |
| `REDDIT_CLIENT_SECRET` | Reddit에서 복사한 CLIENT_SECRET |
| `CLAUDE_API_KEY` | Anthropic에서 복사한 키 |

---

## 🚀 STEP 6 — 대시보드 파일 수정

1. GitHub 저장소에서 `dashboard/index.html` 파일 클릭

2. 오른쪽 상단 **연필(편집)** 아이콘 클릭

3. 아래 부분을 찾아서 수정:
   ```javascript
   const GITHUB_USER = "YOUR_GITHUB_USERNAME";  // ← 여기를 본인 GitHub 아이디로 변경
   ```

4. **Commit changes** 클릭

---

## 🚀 STEP 7 — 첫 번째 실행 (최근 2주 데이터 수집)

1. GitHub 저장소 → **Actions** 탭 클릭

2. 왼쪽 **Daily Idea Radar** 클릭

3. 오른쪽 **Run workflow** 버튼 클릭 → **Run workflow** 확인

4. 초록색 체크 표시가 뜰 때까지 기다림 (약 2~5분)

5. 완료되면 저장소에 `data/` 폴더가 생성됨

---

## 🚀 STEP 8 — 대시보드 접속

대시보드를 여는 방법 두 가지:

**방법 A: 파일로 열기 (가장 쉬움)**
- `dashboard/index.html` 파일을 컴퓨터에 다운로드
- 더블클릭으로 크롬에서 열기

**방법 B: GitHub Pages (URL로 접속)**
1. 저장소 Settings → Pages
2. Source: **Deploy from a branch**
3. Branch: **main**, Folder: **/dashboard**
4. Save 클릭
5. `https://YOUR_GITHUB_USERNAME.github.io/idea-radar` 로 접속

---

## ✅ 완료!

이제부터 **매일 오전 8시**에 자동으로:
1. Reddit, Hacker News, 클리앙, Product Hunt에서 게시물 수집
2. Claude AI가 분석해서 사업 아이디어 생성
3. 대시보드에서 바로 확인 가능

---

## ❓ 자주 묻는 질문

**Q: Actions가 실행 안 돼요**
A: 저장소가 Public인지 확인, Secrets가 정확히 등록됐는지 확인

**Q: 대시보드가 비어있어요**
A: GITHUB_USER를 본인 아이디로 변경했는지 확인

**Q: Reddit 데이터가 0개예요**
A: Reddit API 키 확인 (CLIENT_ID, SECRET 순서 맞는지)

**Q: 비용이 얼마나 나오나요?**
A: Claude Haiku 기준 하루 약 50-100원, 월 1,500~3,000원

---

## 💬 문제 발생 시

대시보드 HTML 파일 안의 에러 메시지를 캡처해서 Claude에게 보내주세요.
