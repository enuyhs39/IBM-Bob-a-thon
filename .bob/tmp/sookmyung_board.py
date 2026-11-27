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
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#43;', '+', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# 공지사항 목록 (bbs 1637 = 국내공지)
print("=" * 60)
print("[ 국제처 공지사항 목록 ]")
print("=" * 60)

html = fetch(BASE + '/bbs/exchange/1637/artclList.do?layout=unknown')

# 게시글 링크와 제목 추출
articles = re.findall(r'href="(/bbs/exchange/1637/(\d+)/artclView\.do[^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
if not articles:
    # 다른 패턴 시도
    articles = re.findall(r'(\/bbs\/exchange\/1637\/\d+\/artclView\.do[^"\']*)', html)
    print("대체 패턴:", articles[:10])
else:
    for path, art_id, title in articles[:10]:
        print(f"[{art_id}] {clean(title)}")
        print(f"  URL: {BASE}{path}")
        print()

# 외부공지 (1638)
print("=" * 60)
print("[ 외부공지 목록 ]")
print("=" * 60)
html2 = fetch(BASE + '/bbs/exchange/1638/artclList.do?layout=unknown')
articles2 = re.findall(r'href="(/bbs/exchange/1638/(\d+)/artclView\.do[^"]*)"[^>]*>(.*?)</a>', html2, re.DOTALL)
for path, art_id, title in articles2[:10]:
    print(f"[{art_id}] {clean(title)}")
    print(f"  URL: {BASE}{path}")
    print()
