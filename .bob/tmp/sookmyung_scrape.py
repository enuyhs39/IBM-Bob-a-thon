import urllib.request, re, json

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
    try:
        return raw.decode('utf-8')
    except:
        return raw.decode('euc-kr', errors='ignore')

# 메인 페이지
html = fetch('https://exchange.sookmyung.ac.kr/exchange/index.do')

# href 링크 추출
links = re.findall(r"href=[\"']([^\"']+)[\"']", html)
print("=== 주요 링크 ===")
seen = set()
for l in links:
    if l not in seen and len(l) > 2 and not l.startswith('#') and not l.startswith('javascript'):
        seen.add(l)
        print(l)

print("\n=== 공지/게시판 관련 텍스트 ===")
lines = html.split('\n')
for line in lines:
    s = line.strip()
    if any(kw in s for kw in ['공지', '게시', 'board', 'bbs', 'notice', 'menu', 'gnb', 'lnb', '프로그램', '장학']):
        clean = re.sub(r'<[^>]+>', '', s).strip()
        if clean and len(clean) > 1:
            print(clean[:200])
