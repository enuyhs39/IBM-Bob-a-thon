import urllib.request, json, sys

# open-lab API 전체 구조 확인
url = 'https://phdkim.net/api/professor/open-lab?university=47&size=3'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read().decode('utf-8'))

payload = data['payload']
sys.stdout.buffer.write(f'총 교수 수: {payload.get("totalElements", "?")}\n'.encode('utf-8'))
sys.stdout.buffer.write(f'총 페이지: {payload.get("totalPages", "?")}\n'.encode('utf-8'))
sys.stdout.buffer.write(f'페이지당: {payload.get("size", "?")}\n\n'.encode('utf-8'))

# 첫 번째 항목 전체 출력
item = payload['content'][0]
sys.stdout.buffer.write(json.dumps(item, ensure_ascii=False, indent=2).encode('utf-8'))
