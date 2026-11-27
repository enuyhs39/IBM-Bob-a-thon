import urllib.request, re, sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
    for ent, rep in [('&nbsp;',' '),('&amp;','&'),('&lt;','<'),('&gt;','>'),('&#43;','+'),('&quot;','"')]:
        text = text.replace(ent, rep)
    text = re.sub(r'&#[0-9]+;', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_article(url):
    html = fetch(url)
    result = {}

    title_m = re.search(r'class="artclViewTitle"[^>]*>\s*(.*?)\s*</h2>', html, re.DOTALL)
    result['title'] = clean(title_m.group(1)) if title_m else ''

    date_m = re.search(r'(\d{4}\.\d{2}\.\d{2})', html)
    result['date'] = date_m.group(1) if date_m else ''

    view_m = re.search(r'(\d+)</dd>\s*</dl>\s*</div>\s*</div>\s*</div>\s*<div class="artclViewTitleWrap"', html)
    # 조회수는 artclViewHead에서
    views_m = re.search(r'<dt>[^<]*조회[^<]*</dt>\s*<dd>(\d+)</dd>', html)
    result['views'] = views_m.group(1) if views_m else '-'

    body_m = re.search(r'<div class="artclView">(.*?)</div>\s*\n?\s*<div class="artclItem', html, re.DOTALL)
    if body_m:
        result['content'] = clean(body_m.group(1))
    else:
        body_m2 = re.search(r'<div class="artclView">(.*?)</div>\s*\n?\s*<div class="_areaButton"', html, re.DOTALL)
        result['content'] = clean(body_m2.group(1)) if body_m2 else '(본문 없음)'

    files = re.findall(r'href="(/bbs/[^"]+/download\.do)"[^>]*>\s*\n?\s*([^\n<]+)', html)
    result['files'] = [(BASE + path, name.strip()) for path, name in files if name.strip()]

    return result

# ================================================================
print("=" * 70)
print("[국제처 공지사항] 최신 5개")
print("=" * 70)

board_html = fetch(BASE + '/bbs/exchange/1637/artclList.do?layout=unknown')
articles = re.findall(r'href="(/bbs/exchange/1637/(\d+)/artclView\.do[^"]*)"[^>]*>(.*?)</a>', board_html, re.DOTALL)

for i, (path, art_id, title_html) in enumerate(articles[1:6], 1):
    art = parse_article(BASE + path.split('?')[0])
    print(f"\n[{i}] {art['title']}")
    print(f"    날짜: {art['date']}  |  조회: {art['views']}")
    print(f"    본문 요약: {art['content'][:500]}{'...' if len(art['content']) > 500 else ''}")
    if art['files']:
        print(f"    첨부파일:")
        for furl, fname in art['files']:
            print(f"      - {fname}")
            print(f"        {furl}")
    print("-" * 70)

print()
print("=" * 70)
print("[외부공지] 최신 5개")
print("=" * 70)

board_html2 = fetch(BASE + '/bbs/exchange/1638/artclList.do?layout=unknown')
articles2 = re.findall(r'href="(/bbs/exchange/1638/(\d+)/artclView\.do[^"]*)"[^>]*>(.*?)</a>', board_html2, re.DOTALL)

for i, (path, art_id, title_html) in enumerate(articles2[:5], 1):
    art = parse_article(BASE + path.split('?')[0])
    print(f"\n[{i}] {art['title']}")
    print(f"    날짜: {art['date']}  |  조회: {art['views']}")
    print(f"    본문 요약: {art['content'][:300]}{'...' if len(art['content']) > 300 else ''}")
    if art['files']:
        print(f"    첨부파일 {len(art['files'])}개:")
        for furl, fname in art['files'][:3]:
            print(f"      - {fname}")
    print("-" * 70)
