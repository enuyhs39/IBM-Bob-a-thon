# 🔬 Lab Finder — 숙명여자대학교 연구실 매칭 서비스

> **IBM Bob-a-thon 2026** 출품작  
> 관심 키워드 입력 → 연구실 추천 → AI 논문 요약 → 컨택 메일 작성까지 한 번에

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🔍 **LITE 검색** | 키워드 1개로 관련 연구실 전체 목록 탐색 |
| 🎯 **MATCH 추천** | 추가 정보 입력 시 AI가 Top 3 맞춤 연구실 추천 + 추천 이유 생성 |
| 📄 **연구실 상세** | rndcircle 논문 데이터를 AI가 읽어 한국어 프로파일 자동 요약 |
| ✉️ **메일 작성** | 대충 적은 내용 → AI가 정중한 컨택 메일(제목+본문) 완성 |

---

## 🏗 시스템 아키텍처

```
[학생]
  │  키워드 + 추가정보 입력
  ▼
[Frontend]  index.html → results.html → detail.html → email.html
  │  HTTP (localhost:3000)
  ▼
[FastAPI Backend]  localhost:8000
  ├── /api/search   → search_labs (Python Tool)
  ├── /api/match    → search_labs + match_labs (Python Tool)
  ├── /api/profile  → professor_profile_agent (wxO Agent)
  └── /api/email    → email_helper_shh (wxO Agent)
         │
         ▼
[watsonx Orchestrate]
  ├── professor_profile_agent  ← get_lab_info / get_lab_papers / get_lab_research
  ├── lab_advisor_agent        ← search_labs / match_labs
  ├── lab_matching_agent
  └── email_helper_shh

[외부 API]
  ├── 김박사넷 오픈랩 API  → 연구실 목록 + 모집 여부
  └── rndcircle API       → 논문 / 연구 주제 / 연구실 정보
```

---

## 🗂 프로젝트 구조

```
IBM_Bob/
├── agents/
│   ├── lab_advisor_agent.yaml        # 오케스트레이터 (LITE/MATCH 분기)
│   ├── lab_matching_agent.yaml       # Top 3 추천 + 자연어 이유 생성
│   ├── professor_profile_agent.yaml  # 논문 읽고 한국어 프로파일 요약
│   ├── email_helper_shh.yaml         # 연구실 컨택 메일 작성
│   └── email_helper_jh.yaml
├── tools/
│   ├── search_labs.py        # 김박사넷 오픈랩 API — 키워드 검색
│   ├── match_labs.py         # 키워드 일치도 점수 계산 → Top N 선정
│   ├── get_lab_info.py       # rndcircle — 연구실 기본 정보
│   ├── get_lab_papers.py     # rndcircle — 논문 목록 + abstract
│   ├── get_lab_research.py   # rndcircle — 대표 연구 주제
│   └── get_today_date.py     # 오늘 날짜 반환
├── frontend/
│   ├── index.html            # 랜딩 + 키워드/추가정보 입력 폼
│   ├── results.html          # LITE/MATCH 결과 카드
│   ├── detail.html           # 연구실 상세 + AI 프로파일
│   └── email.html            # 컨택 메일 작성
├── backend/
│   ├── main.py               # FastAPI 엔드포인트
│   ├── wxo_client.py         # IAM 토큰 + wxO /runs API 호출
│   ├── requirements.txt
│   ├── .env.example
│   ├── Procfile              # Railway 배포용
│   └── runtime.txt
├── scripts/
│   ├── import-all.sh         # 에이전트/도구 일괄 import
│   └── delete-all.sh
└── docs/
    └── IMB_Bob_연구실 매칭.pptx
```

---

## 🚀 로컬 실행 방법

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 패키지 설치
pip install -r backend/requirements.txt
pip install ibm-watsonx-orchestrate-adk
```

### 2. 환경변수 설정

```bash
cp backend/.env.example backend/.env
```

`backend/.env` 파일에 아래 값 입력:

```env
WXO_BASE_URL=https://api.jp-tok.watson-orchestrate.cloud.ibm.com/instances/{your-instance-id}
IBM_API_KEY=your-ibm-cloud-api-key
AGENT_EMAIL_HELPER=email_helper_shh
AGENT_LAB_ADVISOR=lab_advisor_agent
AGENT_PROF_PROFILE=professor_profile_agent
```

### 3. watsonx Orchestrate에 에이전트/도구 등록

```bash
# 환경 활성화
orchestrate env activate wxo-shh --api-key YOUR_API_KEY

# 도구 등록
orchestrate tools import -k tools/search_labs.py
orchestrate tools import -k tools/match_labs.py
orchestrate tools import -k tools/get_lab_info.py
orchestrate tools import -k tools/get_lab_papers.py
orchestrate tools import -k tools/get_lab_research.py
orchestrate tools import -k tools/get_today_date.py

# 에이전트 등록
orchestrate agents import -f agents/lab_matching_agent.yaml
orchestrate agents import -f agents/professor_profile_agent.yaml
orchestrate agents import -f agents/email_helper_shh.yaml
orchestrate agents import -f agents/lab_advisor_agent.yaml
```

### 4. 서버 실행

**터미널 1 — 백엔드**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**터미널 2 — 프론트엔드**
```bash
cd frontend
python -m http.server 3000
```

브라우저에서 `http://localhost:3000/index.html` 열기

---

## 🤖 에이전트 & 도구 역할

### Agents

| 이름 | 역할 |
|------|------|
| `lab_advisor_agent` | LITE/MATCH 분기 판단 오케스트레이터, 하위 에이전트 협업 |
| `lab_matching_agent` | 후보 연구실 중 Top 3 선정 + 자연어 추천 이유 생성 |
| `professor_profile_agent` | 논문·연구주제 읽고 한국어 연구실 프로파일 요약 |
| `email_helper_shh` | 교수 정보 + 대충 쓴 내용 → 연구실 컨택 메일 완성 |

### Tools

| 이름 | 역할 |
|------|------|
| `search_labs` | 김박사넷 API로 숙명여대 연구실 키워드 검색 |
| `match_labs` | 키워드 일치도·모집여부·조회수 점수 계산 → Top N |
| `get_lab_info` | rndcircle 연구실 기본 정보 조회 |
| `get_lab_papers` | rndcircle 논문 목록 + abstract 조회 |
| `get_lab_research` | rndcircle 대표 연구 주제 조회 |
| `get_today_date` | 오늘 날짜 반환 |

---

## 🛠 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Vanilla HTML/CSS/JS (HP 디자인 시스템, Manrope) |
| Backend | Python, FastAPI, uvicorn |
| AI Agent | IBM watsonx Orchestrate (ADK) |
| LLM | IBM Granite 3.3 8B Instruct / GPT-oss-120B |
| 외부 API | 김박사넷 오픈랩, rndcircle |
| 개발 도우미 | IBM Bob |
