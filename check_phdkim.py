import urllib.request, re, sys

url = 'https://phdkim.net/professor/15965/info'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as res:
    html = res.read().decode('utf-8')

# NUXT state 블록 전체 추출
m = re.search(r'window\.__NUXT__\s*=\s*\(function\((.+?)\)\{return (.+?)\}\((.+?)\)\)', html, re.DOTALL)
if not m:
    # 다른 패턴 시도
    m = re.search(r'__NUXT__=(\{.*?\})\s*;?\s*</script>', html, re.DOTALL)

# JSON-like 데이터에서 교수 정보 추출
# 이름
names = re.findall(r'"name":"([^"]{1,30})"', html)
sys.stdout.buffer.write(('names found: ' + str(names[:10]) + '\n').encode('utf-8'))

# 키워드
kws = re.findall(r'keywords:\[([^\]]+)\]', html)
sys.stdout.buffer.write(('keywords: ' + str(kws) + '\n').encode('utf-8'))

# 이메일
emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
sys.stdout.buffer.write(('emails: ' + str(emails[:5]) + '\n').encode('utf-8'))

# 연구실명
labs = re.findall(r'labName[:\s"]+([^"<]{3,50})', html)
sys.stdout.buffer.write(('labs: ' + str(labs[:5]) + '\n').encode('utf-8'))

# og:title (페이지 제목 = 교수명 + 소속)
title = re.search(r'og:title.*?content="([^"]+)"', html)
if title:
    sys.stdout.buffer.write(('og:title: ' + title.group(1) + '\n').encode('utf-8'))

# og:description
desc = re.search(r'og:description.*?content="([^"]+)"', html)
if desc:
    sys.stdout.buffer.write(('og:description: ' + desc.group(1) + '\n').encode('utf-8'))

# 전체 교수 JSON 블록 (처음 5000자 범위에서 정제된 데이터)
# "professor" 객체 패턴
prof_block = re.search(r'"professor":\{[^}]{10,500}\}', html)
if prof_block:
    sys.stdout.buffer.write(('professor block: ' + prof_block.group(0) + '\n').encode('utf-8'))

# 전체 텍스트에서 의미 있는 한글 블록만 추출 (태그 제거)
text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
# 50자 이상 의미 있는 블록
chunks = [c.strip() for c in text.split('  ') if len(c.strip()) > 20]
sys.stdout.buffer.write(('\n\n=== Page text snippets ===\n').encode('utf-8'))
for c in chunks[:30]:
    sys.stdout.buffer.write((c[:200] + '\n').encode('utf-8'))
