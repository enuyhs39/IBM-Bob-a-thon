import urllib.request, re

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
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
    for ent, rep in [('&nbsp;',' '),('&amp;','&'),('&lt;','<'),('&gt;','>'),('&#43;','+')]:
        text = text.replace(ent, rep)
    text = re.sub(r'&#[0-9]+;', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

html = fetch('https://exchange.sookmyung.ac.kr/bbs/exchange/1637/217473/artclView.do')

# div class 목록 확인
divs = re.findall(r'<div[^>]+class="([^"]+)"', html)
keywords = ['artcl','content','view','body','text','cntn','detail','editor']
for d in divs:
    if any(k in d.lower() for k in keywords):
        print("CLASS:", d)

print("\n--- 본문 div 주변 HTML 샘플 ---")
# artcl 관련 위치 찾기
for m in re.finditer(r'artcl', html, re.IGNORECASE):
    start = max(0, m.start()-100)
    end = min(len(html), m.end()+200)
    print(repr(html[start:end]))
    print()
