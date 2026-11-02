# 중학교 생기부 스킬

중학교 교사가 AI로 학교생활기록부 서술형 항목의 **초안**을 쓰도록 돕는 스킬입니다. 기준은 「2026학년도 학교생활기록부 기재요령(중학교)」과 「2026학년도 학교생활기록부 기재 길라잡이(중학교)」입니다.

- 다루는 항목: 전 교과 과목별 세부능력 및 특기사항, 개인별 세특, 창의적 체험활동(자율·자치, 동아리, 진로), 자유학기활동, 행동특성 및 종합의견
- 바로 쓰지 않고 먼저 묻습니다. 성취기준 원문, 관찰 메모, 목표 분량(Byte)을 확인한 뒤 씁니다.
- 교사가 주지 않은 사실은 쓰지 않고 `[교사 확인 필요]`로 비워 둡니다.
- 초안 끝에 교사가 확인할 목록(사실, 과장, 항목 적합성)을 붙입니다.
- 초안을 낸 뒤 AI처럼 보이는 문장 틀("단순한 X를 넘어", "~로 이어짐", 과장 평가어, 총평 마무리 등)을 걷어 냅니다. 한국어 윤문 스킬 [im-not-ai](https://github.com/epoko77-ai/im-not-ai)의 작동 방식(점수 → 진단 → 윤문 → 서법 복원 → 게이트)을 학생부에 맞게 옮겼습니다. 고친 뒤에는 수치·서법(노력함, ~할 수 있음)·핵심 낱말이 그대로인지, 너무 많이 고치지 않았는지, 새 틀을 만들지 않았는지 검사합니다. 작업 파일은 로컬 앱 데이터 폴더에만 두고 동기화 폴더에는 쓰지 않습니다.
- 코드 실행이 되는 환경에서는 검사 스크립트로 Byte, 금칙어, 문자 규칙, 명사형 종결, AI 문체 틀, 학생 간 문장 중복을 기계 검사합니다.

## 설치

쓰는 앱에 맞는 방법 하나만 하면 됩니다. zip 파일은 [Releases](https://github.com/teaju00/saenggibu-skill/releases/latest)에 있습니다. **Claude용과 Gemini용 zip은 폴더 구조가 달라서 서로 바꿔 쓸 수 없습니다.**

| 쓰는 앱 | 방법 |
|---|---|
| Claude 데스크톱 앱 · claude.ai 웹 | `saenggibu-claude.zip` 업로드 (아래 1) |
| Gemini 앱 · gemini.google.com 웹 | `saenggibu-gemini.zip` 업로드 (아래 2) |
| Antigravity | 폴더 복사 또는 npx (아래 3) |
| Claude Code · Codex · Gemini CLI · Cursor 등 | 명령 한 줄 (아래 4) |
| ChatGPT 등 스킬 기능이 없는 서비스 | 지침 붙여 넣기 (아래 5) |

### 1. Claude 데스크톱 앱 · claude.ai

1. Releases에서 `saenggibu-claude.zip`을 내려받습니다. 압축은 풀지 않습니다.
2. Claude 앱에서 설정 → 기능(Capabilities) → 스킬 → 스킬 업로드를 누르고 zip을 고릅니다.
3. 같은 화면에서 코드 실행 기능을 켜 두면 검사 스크립트가 돕니다.

사용자 스킬 업로드는 유료 요금제(Pro, Max, Team, Enterprise)에서 됩니다. 데스크톱 앱과 웹은 같은 계정이라 한쪽에서 올리면 양쪽에서 쓰입니다.

### 2. Gemini 앱 · gemini.google.com

1. Releases에서 `saenggibu-gemini.zip`을 내려받습니다. 압축은 풀지 않습니다.
2. gemini.google.com 왼쪽 메뉴에서 맞춤설정(Customize) → 스킬(Skills) → 만들기(Create) → 업로드(Upload)를 누르고 zip을 고릅니다.
3. 내용을 확인하고 만들기를 누릅니다.

Google 안내 기준으로 스킬은 Gemini 웹, Mac 앱, 모바일 앱에서 쓸 수 있습니다. Windows에서는 웹(gemini.google.com)에서 올리면 같은 계정의 모바일 앱에서도 쓰입니다. 만 18세 이상 개인 계정이어야 하고 Gemini 앱 활동(Keep Activity)이 켜져 있어야 합니다. **학교·교육청에서 받은 Google Workspace 계정은 이 기능이 막혀 있을 수 있습니다.** 그때는 개인 계정을 쓰거나 아래 5번 방법을 씁니다.

### 3. Antigravity

[Releases](https://github.com/teaju00/saenggibu-skill/releases/latest)에서 `saenggibu-claude.zip`을 내려받아 압축을 풀고, 나온 `school-record-draft` 폴더를 아래 위치에 넣습니다.

- 모든 작업 공간에서 쓰기: `~/.gemini/config/skills/` (Windows는 `C:\Users\<사용자>\.gemini\config\skills\`)
- 지금 작업 공간에서만 쓰기: 작업 폴더의 `.agents/skills/`

Node.js가 있으면 작업 폴더에서 아래 명령으로도 됩니다.

```bash
npx skills add teaju00/saenggibu-skill -a antigravity
```

### 4. Claude Code · Codex · Gemini CLI · Cursor 등 코딩 에이전트

```bash
npx skills add teaju00/saenggibu-skill
```

[skills CLI](https://github.com/vercel-labs/skills)가 설치된 에이전트를 찾아 스킬 폴더에 넣습니다. 모든 프로젝트에서 쓰려면 `-g`를 붙입니다.

Claude Code는 플러그인으로도 설치할 수 있습니다. Claude Code 안에서 입력합니다.

```
/plugin marketplace add teaju00/saenggibu-skill
/plugin install school-record-draft@saenggibu-skill
```

플러그인으로 설치하면 `/생기부`로 부를 수 있습니다. 스킬 이름 그대로 `/school-record-draft`도 됩니다. zip으로 앱에 올렸거나 다른 에이전트에서 쓸 때는 "생기부 써줘", "세특 초안"처럼 말로 부르면 스킬이 켜집니다.

Gemini CLI는 자체 명령으로도 됩니다.

```bash
gemini skills install https://github.com/teaju00/saenggibu-skill.git --path skills/school-record-draft
```

### 5. ChatGPT 등 스킬 기능이 없는 서비스

`skills/school-record-draft/references/`의 파일을 프로젝트(맞춤형 GPT, Gemini Gem 등)에 넣어 씁니다.

1. `0. 내 교과 정보 (교사가 채움).md`에 과목·학년·학기와 이번 학기 **성취기준 원문**을 채웁니다. 과목이 둘 이상이면 과목마다 파일을 하나씩 만듭니다.
2. `1. 지침 (붙여넣기용).md`의 내용을 지침(instructions) 칸에 붙여 넣습니다. 약 4천7백 자입니다.
3. 나머지 md 파일(0, 2, 3, 4, 5, 6)을 지식 파일로 올립니다.
4. 프로젝트 기능이 없으면 대화 첫머리에 여섯 파일을 첨부하고 "첨부한 1번 지침대로 해 주세요"라고 씁니다.
5. 분량은 `tools/바이트 계산기.html`을 내려받아 내 컴퓨터에서 열어 확인합니다. 인터넷 연결 없이 동작하고 입력한 글이 밖으로 나가지 않습니다.

## 쓰는 방법

1. "2학년 과학 세특 써 줘"처럼 항목을 말하고, 관찰 메모가 있으면 함께 붙입니다. `4. 교사 입력 양식`을 채워 붙이면 질문이 줄어듭니다.
2. AI가 먼저 묻습니다. 아는 것만 답하고 모르면 "없음"이라고 하면 됩니다.
3. 초안과 함께 나오는 '교사 확인 필요' 목록을 하나씩 확인합니다.
4. 확인을 마친 뒤 나이스에 입력합니다. 입력 후에는 학교 계획에 따라 출력물을 대조합니다.

여러 학생을 한꺼번에 쓸 때는 `4. 교사 입력 양식`의 E 양식을 씁니다. 학생 사이에 같은 문장이 나오지 않았는지, 초안과 학생의 대응이 맞는지 입력 전에 꼭 확인합니다. 학생 간 기록이 같거나 뒤바뀐 것은 정정 사유가 됩니다.

## 개인정보 — 반드시 지킬 것

AI 서비스에 넣은 내용은 학교 밖 서버로 나갑니다.

- 학생은 '학생1', '학생2'처럼 **임시 기호**로만 씁니다. 기호와 실제 학생의 대응표는 교사만 보관합니다.
- 실명, 학번, 생년월일, 연락처, 사진, 가족 사항, 질병·건강, 상담 내용, 학교폭력 관련 내용은 넣지 않습니다.
- 이름만 지워도 날짜, 신체 특징, 다른 학생 이름, 사건 순서가 남으면 누구인지 알 수 있습니다. 이런 단서도 뺍니다.
- 서비스 설정에서 대화 내용을 모델 학습에 쓰지 않도록 하는 옵션이 있으면 끕니다.
- 소속 학교와 시도교육청의 생성형 AI 활용 지침이 있으면 그것이 먼저입니다.

## 기재요령이 AI에 대해 정한 것

「2026학년도 학교생활기록부 기재요령」 유의사항 4-다는 AI로 생성한 자료를 서술형 항목에 **그대로 입력하는 행위**를 금지합니다. 윤문 등의 보조 수단으로 AI를 쓸 때는 최종 입력 전에 학생의 실제 수행과 무관한 허위·과장 기재가 없는지, 기재요령 유의사항을 지켰는지 철저히 확인해야 합니다.

이 스킬은 그 조건에 맞게 짜여 있습니다. 근거는 교사가 직접 관찰한 내용이고, AI는 초안을 쓰는 보조이며, 입력 전 확인은 '교사 확인 필요' 목록으로 합니다.

## 파일 구성

```
skills/school-record-draft/
  SKILL.md                                  스킬 본문(작업 순서)
  references/
    0. 내 교과 정보 (교사가 채움).md          성취기준 칸(빈 양식)
    1. 지침 (붙여넣기용).md                   역할, 지킬 것, 묻는 순서, 집필 규칙, 분량, 출력 형식
    2. 기재요령 핵심 (2026 중학교).md         항목별 규칙, 금지 목록, 최대 분량
    3. 교과별 관찰 초점.md                    교과마다 무엇을 보고 무엇을 물을지
    4. 교사 입력 양식.md                      관찰 메모 양식
    5. 작성 예시.md                           구조를 보기 위한 가상 예시
    6. AI 문체 점검.md                        AI 문체 점검 순서(진단·윤문·마무리), 틀 표, 자체 검증, 등급
  scripts/student_record_check.py           초안 기계 검사(표준 라이브러리만 사용)
  scripts/student_record_humanize.py        AI 문체 점검의 점수·경로·서법 복원·게이트(im-not-ai 학생부판)
  scripts/student_record_humanize_baseline.json  지표 기준선(처음엔 원본 에세이 기준 빌림, calibrate 로 보정)
commands/생기부.md                          Claude Code 플러그인용 `/생기부` 별칭
tools/
  바이트 계산기.html                        교사용 오프라인 Byte 계산기
  build_release.py                          Releases zip 두 개(Claude용, Gemini용)를 만드는 스크립트
```

## 범위와 한계

- **중학교 전용**입니다. 고등학교는 세특 입력 대상, 창체 이수시간 등 규칙이 다릅니다.
- 2026학년도 기준입니다. 새 학년도 기재요령이 나오면 `2. 기재요령 핵심`부터 고쳐야 합니다.
- 이 자료는 기재요령을 대신하지 않습니다. 판단이 갈리면 기재요령 원문을 확인하고, 그래도 불분명하면 교육지원청에 질의하십시오.
- 초안의 사실 여부와 최종 입력 책임은 입력하는 교사에게 있습니다.

## 라이선스

MIT

AI 문체 틀의 분류와 번호(A-21, C-8 등)와 `scripts/student_record_humanize.py`의 지표·경로 판정·서법 복원·쉼표 역주입 제거·게이트는 [im-not-ai](https://github.com/epoko77-ai/im-not-ai)(MIT, Copyright (c) 2026 epoko77-ai) v2.3.2에서 옮겨 학생부에 맞게 고친 것입니다. 원본 저작권·허락 고지는 그 스크립트 머리말에 그대로 두었고, 원본과 다른 곳도 거기에 모두 적었습니다.
