import urllib.request, re

BASE = 'https://exchange.sookmyung.ac.kr'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
    try:
        return raw.decode('utf-8')
    except:
        return raw.decode('euc-kr', errors='ignore')

def clean(text):
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#[0-9]+;', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_article(url):
    html = fetch(url)
    # 본문 영역 추출 (artclView 영역)
    body_match = re.search(r'class="artclView"[^>]*>(.*?)(?:class="artclEditor"|id="reply|</div>\s*</div>\s*</div>)', html, re.DOTALL)
    if body_match:
        return clean(body_match.group(1))
    # 대안: 본문 div
    body_match = re.search(r'id="artclCntn"[^>]*>(.*?)</div>', html, re.DOTALL)
    if body_match:
        return clean(body_match.group(1))
    # 최후 수단: 전체에서 본문 추정
    main = re.search(r'class="contentsView"[^>]*>(.*?)(?:id="reply|class="pagerArea")', html, re.DOTALL)
    if main:
        return clean(main.group(1))[:2000]
    return "(본문 추출 실패)"

# 공지사항 목록 가져오기
print("=" * 70)
print("숙명여자대학교 국제처 - 최신 공지사항")
print("=" * 70)

board_html = fetch(BASE + '/bbs/exchange/1637/artclList.do?layout=unknown')
articles = re.findall(r'href="(/bbs/exchange/1637/(\d+)/artclView\.do[^"]*)"[^>]*>(.*?)</a>', board_html, re.DOTALL)

for i, (path, art_id, title_html) in enumerate(articles[1:6], 1):  # 고정공지 제외, 5개
    title = clean(title_html)
    print(f"\n[{i}] 제목: {title}")
    print(f"    번호: {art_id}")
    
    # 본문 읽기
    art_html = fetch(BASE + path.split('?')[0])
    
    # 날짜/작성자 추출
    date_match = re.search(r'(\d{4}[.\-]\d{2}[.\-]\d{2})', art_html)
    if date_match:
        print(f"    날짜: {date_match.group(1)}")
    
    # 본문 추출
    content = get_article(BASE + path.split('?')[0])
    print(f"    내용 미리보기: {content[:500]}")
    print(f"    URL: {BASE}{path.split('?')[0]}")
    print("-" * 70)

print("\n\n외부공지 최신 5개도 확인:")
print("=" * 70)
board_html2 = fetch(BASE + '/bbs/exchange/1638/artclList.do?layout=unknown')
articles2 = re.findall(r'href="(/bbs/exchange/1638/(\d+)/artclView\.do[^"]*)"[^>]*>(.*?)</a>', board_html2, re.DOTALL)
for i, (path, art_id, title_html) in enumerate(articles2[:5], 1):
    title = clean(title_html)
    print(f"\n[{i}] {title} (번호: {art_id})")
