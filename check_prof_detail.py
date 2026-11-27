import urllib.request, re, sys

# PI 등록된 교수 찾기 - 다른 학과 시도
# 먼저 학과 목록에서 교수 ID를 제대로 가져오기
url = 'https://phdkim.net/professor/search/department/3789'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as res:
    html = res.read().decode('utf-8')

# 교수 링크에서 ID 추출
ids = re.findall(r'href="/professor/(\d+)/info"', html)
sys.stdout.buffer.write(f'Found professor IDs: {ids}\n'.encode('utf-8'))

# 각 교수 개별 키워드 확인 (첫 3명)
for pid in ids[:3]:
    purl = f'https://phdkim.net/professor/{pid}/info'
    preq = urllib.request.Request(purl, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(preq, timeout=5) as pres:
        phtml = pres.read().decode('utf-8')

    # og:title
    title = re.search(r'property="og:title"[^>]*content="([^"]+)"', phtml)
    name_dept = title.group(1).replace(' - 김박사넷', '') if title else '?'

    # 개별 키워드 - window.__NUXT__ 블록 내에서 찾기
    # 이 교수 고유 키워드 위치
    all_kw = re.findall(r'keywords:\[([^\]]*)\]', phtml)
    
    # description에서 키워드 힌트
    desc = re.search(r'property="og:description"[^>]*content="([^"]+)"', phtml)
    
    # 전체 HTML에서 고유하게 등장하는 한글 텍스트 (연구 분야 등)
    research_area = re.findall(r'researchArea["\s:]+([^"<,}]{3,100})', phtml)
    interest = re.findall(r'interest["\s:]+([^"<,}]{3,100})', phtml)

    sys.stdout.buffer.write((
        f'\n=== Prof {pid}: {name_dept} ===\n'
        f'  all_keywords sets: {all_kw}\n'
        f'  description: {desc.group(1) if desc else "NONE"}\n'
        f'  researchArea: {research_area[:3]}\n'
        f'  interest: {interest[:3]}\n'
    ).encode('utf-8'))
