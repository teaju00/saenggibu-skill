#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""학생부 AI 문체 윤문 — im-not-ai 파이프라인의 결정적(파이썬) 부분을 학교생활기록부에 맞게 옮긴 것.

원본: im-not-ai humanize-korean v2.3.2 (github.com/epoko77-ai/im-not-ai, 커밋 b37e020, 2026-10-12).
MIT 라이선스 — 저작권 고지와 허락 고지는 이 설명 끝에 그대로 둔다.

작동 원리(원본과 같다)
  prepare    입력 위생 → 정량 점수 → route_hint(light · standard · heavy) → 점수 블록을 앞에 붙인 결합 입력
             (원본 prepare_monolith_input.py + references/metrics.py + metrics_v2.py + sanitize_text.py)
  (LLM)      진단 → 윤문 → (heavy 면) 마무리. 역할과 규칙은 지침 묶음 `6. AI 문체 점검.md`
             (원본 agents/humanize-diagnostician · monolith · finalizer + references/quick-rules.md)
  restore    서법이 사라진 문장만 원문으로 되돌린 뒤, 윤문이 새로 만든 연결어미 쉼표를 지운다
             (원본 restore_modality.py + strip_injected_commas.py — Phase 2.4)
  gate       결정적 게이트 P0~P5(원본 5축) + P6 앵커(학생부판 추가). 종료 코드 0 수렴 · 1 경고 · 2 중단 · 3 판정 불가
             (원본 verify_gates.py + checks.py — Phase 2.5)
  calibrate  사람이 쓴 학생부 글로 기준선(평균 · 표준편차)을 계산한다(원본 build_calibration.py 자리)
  metrics    점수 블록만 본다
  clean      작업 폴더를 지운다(학생 글이 남지 않게)

학생부에 맞게 바꾼 것 — 원본과 다른 곳은 모두 여기에 적는다
   1. 작업 폴더   원본은 현재 폴더의 `_workspace/`. 여기는 %LOCALAPPDATA%\\student-record-humanize\\ 이고,
                  구글 드라이브 · OneDrive 같은 동기화 폴더를 가리키면 멈춘다(학생 개인정보 가드레일).
   2. 지표        한다체를 전제한 넷(normalisation_score · da_streak_rate · ending_diversity · lexical_density)을 뺐다.
                  학생부는 명사형 종결(~함 · ~임)이 의무라 사람 글에서도 극단값이 나온다(분류표 E-2 미적용과 같은 이유).
                  피동 · have/make · 무정물 주어 사전에 음슴체 활용(~됨 · ~받음 · 가지고 있음 · 보여줌)을 더했다.
   3. have/make   '~을 만들다' 계열을 뺐다. 학생부에서는 '프로그램을 만듦'처럼 실제로 만든 산출물이다.
   4. 기준선      학생부 셀이 없으면 원본 baseline.json 의 essay 셀(원본 장르 매핑 '공적/기타 → essay')과
                  고정 근사값을 빌리고 '빌림'으로 표시한다.
                  빌린 기준선의 z 는 P1 판정과 점수 블록의 ★ 표시에 쓰지 않는다(원본도 placeholder 기준선은
                  판정에서 뺀다). `calibrate` 로 사람이 쓴 학생부 30편 이상을 넣으면 그 값이 기준이 된다.
   5. 경로        원본 heavy 의 청킹 · 초장문 판정은 뺐다(학생부는 3,000Byte 이하). 나머지 규칙은 같다.
   6. 틀 탐지     원본 라우터의 카운트형 티 + quick-rules 에서 학생부에 나타나는 틀 + [학생부] 고유 틀(학-1~4).
                  틀마다 기준의 출처(원본 / 학생부)를 단다. 원본이 횟수를 정하지 않은 틀만 학생부 기준을 정했다.
   7. 서법(P5)    당위 · 추측 사전에 명사형(필요함 · 수 있음 · 것으로 보임 · 판단됨)을 더하고, 셋째 서법 '시도'
                  (노력함 · ~하려고 · ~하고자 · 시도함)를 넣었다. 노력을 성취로 바꾸면 과장 기재가 된다.
   8. golden(P3)  제목 · 각주 · 구어 종결 검사를 뺐다(학생부에 없다). 상투구 주입 목록에 틀 표 전체를 더하고,
                  발화 표지에 명사형(말함 · 발표함 · 설명함)을 더했다.
   9. 수치 소실   원본은 보고만 한다. 여기서는 경고(종료 1) — 교사 메모의 횟수 · 기간이 빠지면 정보 누락이다.
  10. 대구 전멸(P2) 원본은 원문 5회 이상일 때만 본다. 학생부는 짧아 2회 이상에서 0회가 되면 실패다
                  (quick-rules C-8 '한 번만 살리고 … 전멸 금지').
  11. 위생        ZWJ · ZWNJ 를 모두 지운다(원본은 이모지 옆이면 남긴다 — 학생부에는 이모지가 없다).
  12. 앵커(P6)    원본에 없는 축. 원본은 내용 앵커 보존을 에이전트 자기 점검에만 맡긴다. 여기서는 진단 '보존 지침'의
                  따옴표 낱말(없으면 원문에서 처방 대상 틀을 뺀 내용어)이 고친 글에서 통째로 사라지면 경고한다.
                  노력 수준 비교(2026-11-02)에서 낮음 · 중간이 진단이 남기라고 한 앵커를 지운 채 게이트를 통과했다.

---
MIT License

Copyright (c) 2026 epoko77-ai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import secrets
import shutil
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean, pstdev

VERSION = "학생부-1 (im-not-ai v2.3.2 b37e020)"
GENRE = "학생부"
HERE = Path(__file__).resolve().parent
BASELINE_PATH = HERE / "student_record_humanize_baseline.json"
RUN_ROOT_NAME = "student-record-humanize"

# 동기화 폴더 표지. 경로에 이 낱말이 들어 있으면 작업 폴더로 쓰지 않는다.
SYNC_MARKERS = ("내 드라이브", "my drive", "google drive", "googledrive", "onedrive", "dropbox", "icloud")


# ===========================================================================
# 위생 (원본 sanitize_text.py) — 제거 · 정규화만 한다. 글자를 더하거나 바꾸지 않는다.
# 소스에 비가시 문자를 리터럴로 쓰지 않는다(원본 원칙). 전부 코드포인트로 조립한다.
# ===========================================================================

def _cls(*ranges) -> str:
    out = []
    for r in ranges:
        if isinstance(r, tuple):
            out.append(f"\\U{r[0]:08x}-\\U{r[1]:08x}")
        else:
            out.append(f"\\U{r:08x}")
    return "".join(out)


_INVISIBLE = re.compile("[" + _cls(0x00AD, 0x180E, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF) + "]")
_BIDI = re.compile("[" + _cls(0x061C, (0x200E, 0x200F), (0x202A, 0x202E), (0x2066, 0x2069)) + "]")
_TAG_CHARS = re.compile("[" + _cls((0xE0000, 0xE007F)) + "]")
_SPECIAL_SPACES = re.compile("[" + _cls(0x00A0, 0x1680, (0x2000, 0x200A), 0x202F, 0x205F) + "]")
_UNI_BREAKS = re.compile("[" + _cls(0x2028, 0x2029) + "]")


def sanitize(text: str) -> tuple[str, dict]:
    counts = {}
    for name, rx in (("보이지 않는 문자", _INVISIBLE), ("방향 제어 문자", _BIDI), ("숨은 태그 문자", _TAG_CHARS)):
        counts[name] = len(rx.findall(text))
        text = rx.sub("", text)
    nfc = unicodedata.normalize("NFC", text)
    counts["NFC 정규화"] = int(nfc != text)
    text = nfc
    counts["특수 공백"] = len(_SPECIAL_SPACES.findall(text))
    text = _SPECIAL_SPACES.sub(" ", text)
    text = _UNI_BREAKS.sub("\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text, {k: v for k, v in counts.items() if v}


# ===========================================================================
# 지표 v1.6 (원본 references/metrics.py) — 쉼표 · 결산 lexicon · 한자어 명사화 · 어휘 다양성
# ===========================================================================

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.!?。])\s+")
_EOJEOL_SPLIT_RE = re.compile(r"\s+")
_PUNCT_STRIP_RE = re.compile(r"[\.,!?;:\(\)\[\]\{\}\"'`~、。“”‘’\-]+")
_DIGIT_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")
_ENDING_COMMA_RE = re.compile(r"(?:고|며|지만|면서|아서|어서)\s*,")
_HANJA_SUFFIXES = ("성", "적", "화")
MIN_COMMAS_FOR_SEGMENT_METRIC = 3

# 원본 baseline.json lexicons 그대로.
CONCLUSION_PIVOT = ["결론적으로", "따라서", "이를 통해", "그러므로"]
SAFE_BALANCE = ["양쪽 모두", "두 가지 모두", "장점도 있지만", "신중하게", "균형"]


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    out = []
    for p in _SENTENCE_SPLIT_RE.split(text):
        for line in p.split("\n"):
            line = line.strip()
            if line:
                out.append(line)
    return out


def _eojeols(text: str) -> list[str]:
    return [t for t in _EOJEOL_SPLIT_RE.split(text.strip()) if t]


def _strip_punct(token: str) -> str:
    return _PUNCT_STRIP_RE.sub("", token)


def _tokens(text: str) -> list[str]:
    return [t for t in (_strip_punct(x) for x in _eojeols(text)) if t]


def comma_inclusion_rate(text: str) -> float:
    sents = split_sentences(_DIGIT_COMMA_RE.sub("", text))
    return sum(1 for s in sents if "," in s) / len(sents) if sents else 0.0


def comma_usage_rate(text: str) -> float:
    sents = split_sentences(_DIGIT_COMMA_RE.sub("", text))
    return sum(s.count(",") for s in sents) / len(sents) if sents else 0.0


def ending_comma_rate(text: str) -> float:
    text = _DIGIT_COMMA_RE.sub("", text)
    boundary = re.findall(r"(?:고|며|지만|면서|아서|어서)(?=[\s,\.!?、。]|$)", text)
    return len(_ENDING_COMMA_RE.findall(text)) / len(boundary) if boundary else 0.0


def comma_segment_length(text: str) -> float:
    lens = []
    for s in split_sentences(_DIGIT_COMMA_RE.sub("", text)):
        for seg in (s.split(",") if "," in s else [s]):
            if seg.strip():
                lens.append(len(_eojeols(seg)))
    return sum(lens) / len(lens) if lens else 0.0


def hanja_nominalizer_density(text: str) -> float:
    toks = _tokens(text)
    if not toks:
        return 0.0
    return sum(1 for t in toks if len(t) >= 2 and t[-1] in _HANJA_SUFFIXES) / len(toks)


def lexical_diversity(text: str) -> float:
    toks = _tokens(text)
    return len(set(toks)) / len(toks) if toks else 0.0


# ===========================================================================
# 지표 v2.0 카운트형 (원본 references/metrics_v2.py) — 음슴체 활용을 더했다(머리말 2 · 3)
# ===========================================================================

_PASSIVE_JI = tuple(f"{p}{s}" for p in ("어", "아", "여", "혀", "려", "해", "워")
                    for s in ("지", "진", "질", "짐", "졌", "져"))
_BOUND = r"(?=\s|[\"'”’()\[\]\.,!?…;:「」『』《》〈〉]|$)"
_BY_PASSIVE_RE = re.compile(
    r"에\s*의(?:해|하여)\s+(?:\S+\s+){0,2}?\S*?(?:"
    r"(?:되|받|당하)(?:다|었|았|어|는|은|을|음|고|며|면|지|기|까|던|자|어서)"
    r"|된다|됐|당한다|당했|당함|됩니다|됩니까"
    r"|(?:됨|된|될|되어|당한|당할|" + "|".join(_PASSIVE_JI) + r")"
    r"(?:지|고|며|까|으로써|으로|지만|데)?" + _BOUND +
    r"|(?:" + "|".join(_PASSIVE_JI) + r")(?:다|는|던|자|기|까|고|며|면|서|음|었|았|지|만)"
    r")"
)
DOUBLE_PASSIVE = (
    "되어진다", "되어졌다", "되어진", "되어지는", "되어짐", "여지다", "여진다", "여졌다", "여진", "여짐",
    "잊혀진", "잊혀졌", "잊혀진다", "잊혀짐", "보여진다", "보여졌다", "보여진", "보여짐",
    "쓰여진다", "쓰여졌다", "쓰여진", "쓰여짐", "닫혀진", "열려진", "불려진", "불려짐", "놓여진", "놓여짐",
)
HAVE_MAKE = (
    "가지고 있다", "가지고있다", "가지고 있는", "가지고있는", "가지고 있었", "가지고있었", "가지고 있으",
    "가지고있으", "가지고 있음", "가지고있음", "갖고 있다", "갖고있다", "갖고 있는", "갖고있는", "갖고 있음",
    "갖고있음", "을 가지다", "를 가지다", "을 가졌", "를 가졌", "을 가진다", "를 가진다", "을 가짐", "를 가짐",
    "회의를 가지", "회의를 가졌", "회의를 가짐", "결정을 내리", "결정을 내렸", "결정을 내림",
)
_DOUBLE_PARTICLE_RE = re.compile(r"(?:에서의|에로의|으로의|에의|으로부터의|로부터의)")
_PROGRESSIVE_RE = re.compile(
    r"고\s*있(?:다|었|는|을|던|는다|음|었음|으며|었으며|고|어|어서|으니|기|기에|는지|을지|겠다|겠음)"
)
_PRONOUN_RE = re.compile(
    r"(?:그녀(?:는|가|를|의|에게|와|도|만)?|그것(?:은|이|을|의|에|에게)?|그들(?:은|이|을|의|에게|과|도)?"
    r"|그(?:는|가|를|의|에게|와|도|만)(?=\s|[\.,!?]|$))"
)
_INANIMATE_SUBJECTS = ("연구", "데이터", "분석", "결과", "시스템", "기술", "사례", "현상", "이론", "정책",
                       "보고서", "AI", "인공지능", "모델", "알고리즘", "변화", "위기", "혁신", "사회", "경제")
_UNIVERSAL_VERBS = ("보여준다", "보여줬다", "보여주는", "보여줌", "시사한다", "시사하는", "시사함",
                    "만든다", "만들어", "드러낸다", "드러냈다", "드러내는", "드러냄", "제시한다", "제시했다", "제시함",
                    "나타낸다", "나타냈다", "나타내는", "나타냄", "증명한다", "증명했다", "증명함",
                    "말해준다", "말해주는", "말해줌", "의미한다", "의미하는", "의미함",
                    "가져온다", "가져왔다", "가져오는", "가져옴")


def by_passive_count(text: str) -> int:
    return len(_BY_PASSIVE_RE.findall(text))


def double_passive_count(text: str) -> int:
    return sum(text.count(t) for t in DOUBLE_PASSIVE)


def have_make_literal_count(text: str) -> int:
    return sum(text.count(t) for t in HAVE_MAKE)


def double_particle_count(text: str) -> int:
    return len(_DOUBLE_PARTICLE_RE.findall(text))


def progressive_aspect_rate(text: str) -> float:
    sents = split_sentences(text)
    return sum(len(_PROGRESSIVE_RE.findall(s)) for s in sents) / len(sents) if sents else 0.0


def pronoun_density(text: str) -> float:
    toks = _tokens(text)
    return len(_PRONOUN_RE.findall(text)) / len(toks) if toks else 0.0


def inanimate_subject_rate(text: str) -> float:
    sents = split_sentences(text)
    if not sents:
        return 0.0
    hits = 0
    for s in sents:
        toks = _tokens(s)
        if not toks:
            continue
        head = toks[0]
        for josa in ("은", "는", "이", "가", "도"):
            if head.endswith(josa) and len(head) > 1:
                head = head[:-1]
                break
        if not (head in _INANIMATE_SUBJECTS or (len(head) >= 2 and head[-1] in "성적화도력감원")):
            continue
        if any(any(v in t for v in _UNIVERSAL_VERBS) for t in toks[1:]):
            hits += 1
    return hits / len(sents)


def relative_clause_nesting(text: str) -> int:
    rx = re.compile(r"[가-힣]+(?:는|던|한|된|할|될|온|간)\s+[가-힣]")
    return sum(1 for s in split_sentences(text) if len(rx.findall(s)) >= 3)


# C-8 부정-긍정 대구. 원본 metrics_v2 의 표층형에 quick-rules C-8 이 든 '~것은 아니다'와 '~라기보다'를 더했다.
# '~뿐만 아니라'는 대구가 아니라 덧붙임이라 넣지 않는다.
ANTITHESIS_RE = re.compile(r"(?:가|이)\s*아니라|것은\s*아니|이기\s*이전에|되기\s*이전에|이기보다|(?:이)?라기\s*보다")


def antithesis_count(text: str) -> int:
    return len(ANTITHESIS_RE.findall(text))


# ===========================================================================
# 틀 표 (원본 quick-rules.md + 라우터 v2.6 패턴 + [학생부] 고유)
# (ID, 세기, 이름, 정규식, 최소 횟수, 기준 출처, 라우터 계수, 처방)
#   최소 횟수 1 = 한 번만 보여도, 2 이상 = 그만큼 몰릴 때만 처방 대상
#   라우터 계수 = route_hint 의 '카운트형 티'에 원값을 더하는가(원본 라우터가 세는 계열 + 사람이 거의 안 쓰는 틀)
# ===========================================================================

_HAVE_MAKE_RE = re.compile("|".join(re.escape(t) for t in sorted(HAVE_MAKE, key=len, reverse=True)))
_DOUBLE_PASSIVE_RE = re.compile("|".join(re.escape(t) for t in sorted(DOUBLE_PASSIVE, key=len, reverse=True)))

TELLS = [
    ("A-6", "S2", "근거 이음말 '~을 바탕으로 · ~에 기반하여'", r"에\s*기반(?:하여|해|한|으로)|[을를]\s*바탕으로", 2,
     "학생부 — 원본은 '남발'로만 적어 횟수가 없다", False, "'~로', '~을 보고'로"),
    ("A-7", "S1", "have/make 직역 '가지고 있음'", _HAVE_MAKE_RE.pattern, 1, "원본", True,
     "형용사 · 동사로 되돌림('관심을 가지고 있음' → '관심이 많음')"),
    ("A-8", "S1", "이중 피동 '~되어짐 · ~보여짐'", _DOUBLE_PASSIVE_RE.pattern, 1, "원본", True, "단일 피동이나 능동으로"),
    ("A-9", "S2", "'~에 의해' 피동", _BY_PASSIVE_RE.pattern, 1, "원본", True, "행위자를 주어로"),
    ("A-19", "S2", "이중 조사 '~에서의 · ~으로의'", _DOUBLE_PARTICLE_RE.pattern, 1, "원본", True,
     "'모둠에서 맡은 역할'처럼 절로 풂"),
    ("A-20", "S2", "피동 진행 '~되고 있음'", r"(?:되|지)고\s*있(?:다|으며|고|는|음|었음)", 3,
     "원본(한 문단 3회 이상 — 학생부는 한 문단)", True, "일부만 단순 시제로, 고립 사용은 보존"),
    ("A-21", "S2", "범위 상승 '~을 넘어'", r"[을를]\s*넘어(?:서)?(?=\s|,)", 1, "원본(사람 글 0건)", True,
     "넘어-구를 지우고 한 일을 근거 장면으로"),
    ("C-8", "S1", "부정 대구 'A가 아니라 B'", ANTITHESIS_RE.pattern, 2, "원본", False,
     "한 번만 살리고 나머지는 한 일만. 학생이 실제로 고른 대비가 남길 1순위. 전멸 금지"),
    ("C-11", "S1", "연결어미 뒤 쉼표", _ENDING_COMMA_RE.pattern, 6, "원본(6회 이상 = 강한 신호)", False,
     "쉼표를 지움. 윤문이 새 쉼표를 만들면 실패"),
    ("D-1", "S1", "결산 이음말 '이를 통해 · 따라서'", r"결론적으로|따라서|이를\s*통해|그러므로|요약하면|정리하자면|종합하면|요컨대",
     4, "원본(3회 초과)", True, "1~2건만 남기고 시점 · 원인으로 잇거나 지움"),
    ("D-2", "S1", "의의 과장 '주목할 만함 · 매우 중요함'",
     r"시사하는\s*바|주목할\s*만|매우\s*중요|의미가\s*(?:크|적지\s*않)|간과할\s*수\s*없|무시할\s*수\s*없", 1, "원본", True,
     "지우거나 구체 결론으로"),
    ("D-3", "S1", "열거 도입 '크게 세 가지 · 다음과 같이'", r"크게\s*(?:두|세|네)\s*가지|다음과\s*같", 1, "원본", True,
     "도입구를 지우고 바로 본론"),
    ("D-7", "S2", "변환 공식 'X에서 Y로'",
     r"[가-힣]+에서\s+[가-힣 ]{1,15}?(?:으)?로\s*(?:확장|전환|발전|나아|변화|넘어)|[을를]\s*넘어\s+[가-힣 ]{1,15}?(?:으)?로", 2,
     "원본(문서당 1회 이하)", False, "직접 서술로"),
    ("D-8", "S2", "분열문 '핵심은 ~에 있음'",
     r"(?:필요|중요)한\s*것은|(?:문제는|핵심은|관건은|답은)\s+[^.?!\n]{0,50}(?:점이다|점임|것이다|것임|데\s*있다|데\s*있음)", 1,
     "원본", True, "주어와 서술을 바로 이음"),
    ("D-9", "S2", "인과 결산 '~로 이어짐 · 결국'", r"(?:으)?로\s*이어(?:짐|져|졌|지는|진다|지며|진)|직결|(?<![가-힣])결국(?![가-힣])", 2,
     "원본(문서 2회 이상)", True, "실제 경로(한 일)를 쓰거나 끊음. 새로 만들지 않음"),
    ("D-10", "S2", "이유 도치 '~하는 이유임'", r"이유(?:다|이다|임|입니다)\.", 2, "원본(문서당 1회 이하)", True, "순방향 서술로"),
    ("D-11", "S2", "결말 시간어 '앞으로 · 향후'", None, 1, "원본(후반 30% 문두)", True, "지우거나 실제 시점 · 조건으로(날조 금지)"),
    ("D-12", "S2", "과제 문패 '아쉬운 점도 있음'", r"과제도\s*(?:남아\s*있|남았|뚜렷)|한계도\s*분명|아쉬운\s*점도\s*있", 1, "원본", True,
     "문패를 지우고 실제 과제를 씀"),
    ("D-14", "S2", "사전 은유 '청사진 · 신호탄'", r"잠식|청사진|적신호|경고등|신호탄|움켜쥐|뿌리내리|짓누르", 1, "원본(사람 0건)", True,
     "명제로 풂. 명제가 불명하면 보존"),
    ("F-5", "S2", "'~적 N' 추상 체인", r"(?<![가-힣])(?!(?:목|성|실|업|흔|지)적 )[가-힣]+적 [가-힣]{2,}", 3, "원본", False,
     "명사+명사로 풀거나 풀어 씀"),
    ("F-7", "S2", "범용 정책동사 '강화 · 개선 · 마련'", r"(?:확대|강화|개선|확보|마련|구축)(?:함|하였|했|하여|해|하는|하고|하며|할)", 3,
     "학생부 — 원본은 '밀집'으로만 적어 횟수가 없다", True, "무엇을 어떻게 했는지 구체 동사로"),
    ("I-2", "S2", "형식명사 강조 '주목할 점은'", r"주목할\s*점은|라는\s*점에\s*있", 1, "원본", True, "'X는 ~임'으로 직설"),
    ("학-1", "S2", "[학생부] '~에 그치지 않고'", r"(?:그치지|머무르지|머물지|국한되지)\s*않고", 1, "학생부(A-21 과 같은 범위 상승)", True,
     "앞 절반을 지우고 한 일을 씀"),
    ("학-2", "S1", "[학생부] 총평 마무리",
     r"(?:기대되는|기대가\s*되는|잠재력이\s*(?:큰|높은|풍부한)|가능성이\s*(?:큰|높은|무궁무진한))\s*학생임|무궁무진|"
     r"중요성을\s*(?:깨달|깨닫|인식)|계기가\s*(?:됨|되었|되어)|토대를\s*마련|발판을\s*마련|밑거름이\s*(?:됨|되었|되어)|초석을\s*다|"
     r"한\s*단계\s*성장|의미\s*있는\s*(?:경험|시간)", 1, "학생부(관찰할 수 없는 속마음 · 평가 반복)", True,
     "지우고 마지막 구체 사실에서 끝냄"),
    ("학-3", "S1", "[학생부] 과장 평가어", r"탁월|돋보|깊이\s*있|수준\s*높|남다른|뛰어난|놀라운|인상적|빛나는|독보적", 1,
     "학생부(기재요령 원문 0건 · 과장 기재 위험)", True, "판단의 근거가 된 행동으로"),
    ("학-4", "S2", "[학생부] 포장 종결 '~하는 모습을 보임'", r"(?:모습|역량|능력|태도)(?:을|를)\s*(?:보임|보여\s*줌|보였|발휘함|드러냄)", 2,
     "학생부", False, "동사로 끝냄('설명함')"),
]

_D11_RE = re.compile(r"^(?:향후|앞으로는?|중?장기적으로는?)(?![가-힣])")


def _d11_hits(text: str) -> list[str]:
    sents = split_sentences(text)
    start = int(len(sents) * 0.7)
    return [m.group(0) for s in sents[start:] for m in [_D11_RE.match(s)] if m]


def detect_tells(text: str) -> list[dict]:
    """틀마다 맞은 구절과 처방 대상 여부(met). 원값 집계는 route_hint 가 쓴다."""
    out = []
    for tid, sev, name, pattern, least, basis, route, fix in TELLS:
        if tid == "D-11":
            hits = _d11_hits(text)
        else:
            hits = [m.group(0).strip(" ,") for m in re.finditer(pattern, text)]
        out.append({"id": tid, "sev": sev, "name": name, "hits": hits, "least": least,
                    "met": len(hits) >= least and bool(hits), "basis": basis, "route": route, "fix": fix})
    return out


E1_BAND = (25, 55)  # 분류표 E-1 '모든 문장이 30~50자 부근에 몰려 있음'


def e1_signal(text: str) -> dict | None:
    """E-1 리듬 균일. 분류표 정의 두 조건 — 모든 문장이 30~50자 부근 + 100자 이상 장문 부재.

    장문 부재만으로는 짧은 학생부 글에서 사람 글도 대부분 걸린다(사람 100자+ 문장은 1,000문장당 91.3 —
    5문장 글이면 사람 글의 약 60%가 장문 없음). 그래서 '몰림' 조건을 함께 건다. 4문장 이상일 때만 본다.
    """
    lens = [len(s) for s in split_sentences(text) if len(s) >= 4]
    if len(lens) < 4:
        return None
    m = sum(lens) / len(lens)
    cv = (sum((x - m) ** 2 for x in lens) / len(lens)) ** 0.5 / m
    met = max(lens) < 100 and all(E1_BAND[0] <= x <= E1_BAND[1] for x in lens)
    return {"sentences": len(lens), "longest": max(lens), "cv": round(cv, 3), "met": met}


# ===========================================================================
# 기준선 · z (원본 metrics.py _z · metrics_v2.py _z_simple)
# ===========================================================================

V1_KEYS = (("comma_inclusion_rate", True), ("comma_usage_rate", False),
           ("ending_comma_rate", True), ("comma_segment_length", False))
# 원본 metrics.py 의 고정 근사값(KatFish 셀이 없는 두 지표).
FIXED_PROXY = {"hanja_nominalizer_density": (6.0, 12.0, 100.0), "lexical_diversity": (0.65, 0.55, 1.0)}
CALIBRATION_MIN_N = 30


def load_baseline(path: Path | None = None) -> dict:
    p = Path(path) if path else BASELINE_PATH
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _z(value, human, ai, percent):
    if human is None or ai is None:
        return None
    val = value * 100 if percent else value
    sd = abs(ai - human) / 2.0
    return 0.0 if sd == 0 else (val - human) / sd


def _z_simple(value, cell):
    sd = cell.get("stdev") or 0
    return None if sd <= 0 else (value - cell.get("mean", 0.0)) / sd


def z_scores(metrics: dict, baseline: dict) -> tuple[dict, str]:
    """(z 표, 기준선 상태 '보정' | '빌림'). 학생부 셀이 n≥30 으로 다 차야 '보정'."""
    cells = (baseline.get("genres") or {}).get(GENRE) or {}
    borrowed = baseline.get("borrowed") or {}
    z, calibrated = {}, True
    for key, percent in V1_KEYS:
        cell = cells.get(key)
        if cell and not cell.get("_placeholder"):
            z[key] = _z_simple(metrics[key], cell)
        else:
            calibrated = False
            b = borrowed.get(key) or {}
            z[key] = _z(metrics[key], b.get("human"), b.get("ai"), percent)
    for key, (human, ai, scale) in FIXED_PROXY.items():
        cell = cells.get(key)
        if cell and not cell.get("_placeholder"):
            z[key] = _z_simple(metrics[key], cell)
        else:
            calibrated = False
            z[key] = _z(metrics[key] * scale, human, ai, False)
    return z, ("보정" if calibrated else "빌림")


def classify_risk(z: dict, pivot: int, safe: int) -> tuple[str, int]:
    """원본 _classify_risk 그대로 — 쉼표 계열 상한 3, high 는 독립 계열 2개 이상."""
    punct = min(sum(2 for k in ("comma_inclusion_rate", "ending_comma_rate", "comma_segment_length")
                    if z.get(k) is not None and z[k] > 1.0), 3)
    lexical = int(z.get("lexical_diversity") is not None and z["lexical_diversity"] < -1.0) \
        + int(z.get("hanja_nominalizer_density") is not None and z["hanja_nominalizer_density"] > 1.0)
    rhetoric = int(pivot >= 2) + int(safe >= 2)
    score = punct + lexical + rhetoric
    families = sum(1 for v in (punct, lexical, rhetoric) if v > 0)
    band = "high" if score >= 6 and families >= 2 else ("medium" if score >= 4 else "low")
    return band, score


# ===========================================================================
# 전체 점수 + route_hint (원본 compute_all_v2 + compute_route_hint)
# ===========================================================================

ROUTE_LIGHT_MAX_TELLS = 2
ROUTE_HEAVY_MIN_TELLS = 8


def compute_all(text: str, baseline: dict | None = None) -> dict:
    baseline = load_baseline() if baseline is None else baseline
    metrics = {
        "comma_inclusion_rate": comma_inclusion_rate(text),
        "comma_usage_rate": comma_usage_rate(text),
        "ending_comma_rate": ending_comma_rate(text),
        "comma_segment_length": comma_segment_length(text),
        "conclusion_pivot_count": sum(text.count(w) for w in CONCLUSION_PIVOT),
        "safe_balance_count": sum(text.count(w) for w in SAFE_BALANCE),
        "hanja_nominalizer_density": hanja_nominalizer_density(text),
        "lexical_diversity": lexical_diversity(text),
    }
    z, status = z_scores(metrics, baseline)
    if _DIGIT_COMMA_RE.sub("", text).count(",") < MIN_COMMAS_FOR_SEGMENT_METRIC:
        z_unguarded = {"comma_segment_length": z.get("comma_segment_length")}
        z["comma_segment_length"] = None
    else:
        z_unguarded = {}
    risk, score = classify_risk(z, metrics["conclusion_pivot_count"], metrics["safe_balance_count"])
    v2 = {
        "by_passive_count": by_passive_count(text),
        "double_passive_count": double_passive_count(text),
        "have_make_literal_count": have_make_literal_count(text),
        "double_particle_count": double_particle_count(text),
        "progressive_aspect_rate": progressive_aspect_rate(text),
        "pronoun_density": pronoun_density(text),
        "inanimate_subject_rate": inanimate_subject_rate(text),
        "relative_clause_nesting": relative_clause_nesting(text),
        "antithesis_count": antithesis_count(text),
    }
    tells = detect_tells(text)
    out = {
        "version": VERSION, "genre": GENRE, "char_count": len(text),
        "metrics": metrics, "z_scores": z, "baseline_status": status,
        "risk_band": risk, "risk_score": score, "v2_metrics": v2,
        "tells": tells, "e1": e1_signal(text),
    }
    if z_unguarded:
        out["z_scores_unguarded"] = z_unguarded
    out.update(route_hint(out))
    return out


def route_hint(m: dict) -> dict:
    """원본 3단 판정. 청킹 · 초장문 갈래만 뺐다(머리말 5)."""
    tells = m["metrics"]["safe_balance_count"] + sum(len(t["hits"]) for t in m["tells"] if t["route"])
    risk = m["risk_band"]
    if risk == "high" and tells >= ROUTE_HEAVY_MIN_TELLS:
        hint, reason = "heavy", f"risk_band high + 카운트형 티 {tells}건 — 진단 → 윤문 → 마무리"
    elif tells <= ROUTE_LIGHT_MAX_TELLS and risk in ("low", "medium"):
        hint, reason = "light", (f"카운트형 티 {tells}건 · risk_band {risk} — 진단 없이 보수 윤문 1회. "
                                 f"'티가 없다'가 아니라 '세는 항목에 안 걸렸다'다")
    else:
        hint, reason = "standard", f"카운트형 티 {tells}건 · risk_band {risk} — 진단 + 윤문"
    return {"route_hint": hint, "route_reason": reason, "lexical_tell_count": tells}


# ===========================================================================
# 결합 입력 렌더 (원본 _render_block · _render_combined)
# ===========================================================================

_INVERTED = frozenset({"lexical_diversity"})


def _marker(z, key, status):
    if z is None or status != "보정":
        return ""  # 빌린 기준선이면 ★ 를 달지 않는다 — 윤문이 그 표시를 보고 손댈 곳을 찾는다
    z = -z if key in _INVERTED else z
    return "  ★ S1 트리거" if z >= 1.5 else ("  · S2 시그널" if z >= 1.0 else "")


def render_block(m: dict) -> str:
    z, met = m["z_scores"], m["metrics"]
    status = m["baseline_status"]
    L = ["[정량 사전 점수 — 학생부판(im-not-ai v2.3.2 지표)]",
         f"risk_band: {m['risk_band']}  (score {m['risk_score']})",
         f"route_hint: {m['route_hint']}  (권고 — 사용자 · 오케스트레이터가 무시 가능)",
         f"route_reason: {m['route_reason']}",
         f"genre: {GENRE}  ·  char_count: {m['char_count']}",
         f"기준선: {status}" + ("" if status == "보정" else
                              " — 학생부 사람 글로 보정하지 않았다. z 는 참고값이며 ★ 를 달지 않고 P1 판정에도 쓰지 않는다"),
         "", "[v1.6 지표]"]
    for key, fmt in (("comma_inclusion_rate", "{:.2f}"), ("comma_usage_rate", "{:.2f}"), ("ending_comma_rate", "{:.2f}"),
                     ("comma_segment_length", "{:.2f}"), ("hanja_nominalizer_density", "{:.3f}"), ("lexical_diversity", "{:.2f}")):
        zz = z.get(key)
        zs = "n/a" if zz is None else f"z={zz:+.2f}"
        L.append(f"- {key}: {fmt.format(met[key])}  ({zs}){_marker(zz, key, status)}")
    L.append(f"- conclusion_pivot_count: {met['conclusion_pivot_count']}")
    L.append(f"- safe_balance_count: {met['safe_balance_count']}")
    L += ["", "[v2.0 카운트형 지표 — 원값]"]
    for key, label, tid in (("double_passive_count", "이중 피동", "A-8"), ("by_passive_count", "~에 의해 피동", "A-9"),
                            ("have_make_literal_count", "have/make 직역", "A-7"), ("double_particle_count", "이중 조사", "A-19"),
                            ("relative_clause_nesting", "관형절 3중+ 문장 수", "A-18"), ("pronoun_density", "인칭 대명사 밀도", "A-16"),
                            ("antithesis_count", "부정 대구", "C-8")):
        v = m["v2_metrics"][key]
        L.append(f"- {key} ({label}, {tid}): {v if isinstance(v, int) else round(v, 3)}")
    L += ["", "[틀 탐지 — 처방 대상(기준 횟수 이상)]"]
    met_tells = [t for t in m["tells"] if t["met"]]
    if not met_tells:
        L.append("- 없음")
    for t in met_tells:
        L.append(f"- {t['id']} [{t['sev']}] {t['name']}: {len(t['hits'])}회 (기준 {t['least']}회, {t['basis']}) "
                 f"— {', '.join(repr(h) for h in t['hits'][:6])} → {t['fix']}")
    below = [t for t in m["tells"] if t["hits"] and not t["met"]]
    if below:
        L.append("[기준 미만 — 사람도 쓰는 틀, 손대지 않는다]")
        L += [f"- {t['id']} {t['name']}: {len(t['hits'])}회 (기준 {t['least']}회)" for t in below]
    e1 = m.get("e1")
    if e1:
        L.append(f"[E-1 리듬] 문장 {e1['sentences']}개 · 가장 긴 문장 {e1['longest']}자 · 길이 변동 {e1['cv']:.0%}"
                 + (" — 모든 문장이 30~50자 부근 · 100자 이상 장문 없음(E-1). 인접 사실 문장을 이어 장문 하나를 만들 수 있다(내용 추가 금지)"
                    if e1["met"] else ""))
    L += ["", "[근거 사용 가이드]",
          "- 점수는 근거 보조다. 단독 판정 금지.",
          "- 처방 대상 틀만 손댄다. 기준 미만 틀과 학생부 정상 문체(명사형 종결 · 주어 생략)는 건드리지 않는다.",
          "- 메모에 없는 사실 · 수치를 넣지 않는다. 서법(노력함 · 할 수 있음 · ~하려고)을 단정으로 바꾸지 않는다.", ""]
    return "\n".join(L)


def render_combined(text: str, m: dict | None, diagnosis: str | None = None) -> str:
    parts = []
    if diagnosis:
        parts += ["[진단]", diagnosis.rstrip("\n"), "[진단 끝]", ""]
    if m is not None:
        parts.append(render_block(m))
    parts += ["[원문 시작]", text.rstrip("\n"), "[원문 끝]", ""]
    return "\n".join(parts)


# ===========================================================================
# 서법 사전 (원본 verify_gates.py DEONTIC_RE · HEDGE_RE) + 명사형 · 시도(머리말 7)
# ===========================================================================

_JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_DEONTIC_STEM = "".join(chr(0xAC00 + c) for c in range(11172)
                        if c % 28 == 0 and _JUNG[(c // 28) % 21] in "ㅏㅐㅓㅔㅕㅘㅙㅚㅝㅞ")
DEONTIC_RE = re.compile(
    rf"[{_DEONTIC_STEM}]야\s*(?:한다|합니다|했다|하며|하고|하는|할|함|했어요|했어|해요|해서|해도|하지요|하죠|해)"
    rf"|[{_DEONTIC_STEM}]야만"
    r"|필요가\s*있|필요하다|필요합니다|필요함|필요하였음|필요했음"
    r"|요구된다|요구됩니다|요구됨|시급하다|시급합니다|시급함|바람직하다|바람직합니다|바람직함"
    r"|촉구한다|당부한다"
    r"|[가-힣]지\s*않으면\s*안\s*(?:된다|됩니다|되며|돼|되|됨)"
)
# 명사형 추가분에서 '기대됨'은 뺐다 — '성장이 기대됨'은 학-2 총평 마무리라 지워야 하는 틀이다
# (원본도 카탈로그가 제거를 지시하는 상투구는 완곡 사전에 넣지 않는다).
HEDGE_RE = re.compile(
    r"수\s*(?:있다|있습니다|있을|있음|있었음)"
    r"|것으로\s*(?:보인다|보입니다|보임|전망|판단|추정|알려)"
    r"|가능성[이도은을에]|[을ㄹ]\s*수도|수도\s*있"
    r"|[로으]\s*보인다|[로으]\s*보입니다|[로으]\s*보임"
    r"|판단된다|판단됩니다|판단됨|여겨진다|여겨집니다|여겨짐|생각됨"
    r"|해석된다|추정된다|추정됨|기대된다|우려된다|우려됨"
    r"|듯하|듯\s*싶|것\s*같다|것\s*같음"
    r"|전망(?:이다|된다|한다|했다|입니다|이며|하고|임|됨)|예상(?:된다|이다|한다|했다|됩니다|됨|임)"
    r"|단정하기|여지(?:도|가)?\s*있|배제할\s*수\s*없"
)
ATTEMPT_RE = re.compile(
    r"노력(?:함|하였|했|하며|하고|하는|하여|해|을\s*기울)"
    r"|[가-힣](?:으)?려고(?=\s|,|$)|[가-힣](?:으)?려\s*(?:함|하였|했|애|노력)"
    r"|[가-힣]고자(?=\s|,|$)|시도(?:함|하였|했|하며|하고|하여|해)|애(?:씀|썼|쓰며|쓰고)"
)
MODAL = {"당위": DEONTIC_RE, "추측": HEDGE_RE, "시도": ATTEMPT_RE}


def count_modality(text: str) -> dict:
    return {k: len(rx.findall(text)) for k, rx in MODAL.items()}


# ===========================================================================
# 요약 블록 (원본 checks.split_summary_block) — 윤문본 끝 `<!-- HUMANIZE-SUMMARY -->`
# ===========================================================================

_SUMMARY_BLOCK_RE = re.compile(r"<!--\s*HUMANIZE-SUMMARY\b.*", re.DOTALL)


def split_summary_block(text: str) -> tuple[str, str]:
    m = _SUMMARY_BLOCK_RE.search(text)
    return (text, "") if m is None else (text[:m.start()], text[m.start():])


def strip_summary_block(text: str) -> str:
    return split_summary_block(text)[0].strip()


# ===========================================================================
# 서법 국소 복원 (원본 restore_modality.py) — 확실할 때만 손댄다
# ===========================================================================

MIN_PAIR_SIM = 0.35
MERGE_FOREIGN_TOKENS = 3
MERGE_LEN_RATIO = 1.6
_WORD_RE = re.compile(r"[^\w]", re.UNICODE)
CLICHE_STRIP = [
    re.compile(r"^(?:그러므로|따라서|결론적으로|요약하면|정리하면|이를\s*통해)[,\s]+"),
    re.compile(r"지금이야말로\s*"),
    re.compile(r"바야흐로\s*"),
]


def _tokset(s: str) -> set[str]:
    return {t for t in (_WORD_RE.sub("", w) for w in s.split()) if t}


def _bigrams(s: str) -> Counter:
    c = "".join(ch for ch in s if ch.isalnum())
    return Counter(c[i:i + 2] for i in range(len(c) - 1))


def _sim(a: str, b: str) -> float:
    A, B = _bigrams(a), _bigrams(b)
    if not A or not B:
        return 0.0
    return 2 * sum((A & B).values()) / (sum(A.values()) + sum(B.values()))


def align(before: list[str], after: list[str]) -> list[tuple[str, str]]:
    """Needleman-Wunsch 문장 정렬. 1:1 짝과 gap 만 낸다."""
    n, m = len(before), len(after)
    gap = -0.4
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0] = score[i - 1][0] + gap
    for j in range(1, m + 1):
        score[0][j] = score[0][j - 1] + gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            score[i][j] = max(score[i - 1][j - 1] + _sim(before[i - 1], after[j - 1]),
                              score[i - 1][j] + gap, score[i][j - 1] + gap)
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and abs(score[i][j] - (score[i - 1][j - 1] + _sim(before[i - 1], after[j - 1]))) < 1e-9:
            pairs.append((before[i - 1], after[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and abs(score[i][j] - (score[i - 1][j] + gap)) < 1e-9:
            pairs.append((before[i - 1], ""))
            i -= 1
        else:
            pairs.append(("", after[j - 1]))
            j -= 1
    pairs.reverse()
    return pairs


def _strip_restored_cliche(before: str, after: str) -> str:
    out = before
    for rx in CLICHE_STRIP:
        if rx.search(out) and not rx.search(after):
            stripped = rx.sub("", out, count=1).strip()
            if any(r.search(stripped) for r in MODAL.values()):
                out = stripped
    return out


def find_losses(before: str, after: str) -> list[dict]:
    pairs = align(split_sentences(strip_summary_block(before)), split_sentences(strip_summary_block(after)))
    out = []
    for idx, (b, a) in enumerate(pairs):
        b, a = b.strip(), a.strip()
        if not b or not a:
            continue  # 삭제는 서법이 아니라 내용 소실 — 다른 축이 본다
        near = [j for j in (idx - 1, idx + 1) if 0 <= j < len(pairs)]
        neighbor_gap = any(pairs[j][0].strip() and not pairs[j][1].strip() for j in near)
        bt = _tokset(b)
        split_gap = any(not pairs[j][0].strip() and pairs[j][1].strip()
                        and len([t for t in _tokset(pairs[j][1]) & bt if len(t) > 1]) >= 2 for j in near)
        for kind, rx in MODAL.items():
            if rx.search(b) and not rx.search(a):
                out.append({"kind": kind, "before": b, "after": a, "neighbor_gap": neighbor_gap,
                            "split_gap": split_gap, "low_sim": _sim(b, a) < MIN_PAIR_SIM})
                break
    return out


def restore_modality(before: str, after: str) -> tuple[str, list[dict], list[dict]]:
    body, summary = split_summary_block(after)
    restored, skipped = [], []
    for loss in find_losses(before, after):
        if loss["low_sim"]:
            skipped.append({**loss, "reason": "짝 유사도 낮음 — 정렬 아티팩트 가능성"})
            continue
        if body.count(loss["after"]) != 1:
            skipped.append({**loss, "reason": "결과에서 유일하게 특정되지 않음"})
            continue
        foreign = [t for t in _tokset(loss["after"]) - _tokset(loss["before"]) if len(t) > 1]
        longer = len(loss["after"]) >= len(loss["before"]) * MERGE_LEN_RATIO
        if loss["neighbor_gap"] or loss["split_gap"] or (longer and len(foreign) >= MERGE_FOREIGN_TOKENS):
            skipped.append({**loss, "reason": "문장 분할 의심 — 되돌리면 명제가 중복됨" if loss["split_gap"]
                            else "문장 병합 의심 — 되돌리면 다른 명제가 사라짐"})
            continue
        replacement = _strip_restored_cliche(loss["before"], loss["after"])
        body = body.replace(loss["after"], replacement, 1)
        restored.append({**loss, "restored_as": replacement})
    return body + summary, restored, skipped


# ===========================================================================
# C-11 역주입 제거 (원본 strip_injected_commas.py) — 원문에 있던 문장은 불가침
# ===========================================================================

_CONN_COMMA_RE = re.compile(r"(고|며|지만|면서|는데|아서|어서|여서|해서|져서),(\s)")
_QUOTE_RE = re.compile(r"“[^”]*”|‘[^’]*’|\"[^\"]*\"|「[^」]*」|『[^』]*』")
_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def _strip_in_sentence(sent: str) -> tuple[str, int]:
    spans = [m.span() for m in _QUOTE_RE.finditer(sent)]
    out, last, removed = [], 0, 0
    for m in _CONN_COMMA_RE.finditer(sent):
        if any(a <= m.start() < b for a, b in spans):
            continue
        out += [sent[last:m.start()], m.group(1) + m.group(2)]
        last = m.end()
        removed += 1
    out.append(sent[last:])
    return "".join(out), removed


def strip_injected_commas(before: str, after: str, all_sentences: bool = False) -> tuple[str, dict]:
    originals = set() if all_sentences else {_norm(s) for s in _SENT_SPLIT.split(before) if s.strip()}
    body, summary = split_summary_block(after)
    pieces, seps = _SENT_SPLIT.split(body), _SENT_SPLIT.findall(body)
    parts, total, touched = [], 0, 0
    for i, piece in enumerate(pieces):
        if piece.strip() and _norm(piece) not in originals:
            fixed, n = _strip_in_sentence(piece)
            total += n
            touched += int(n > 0)
            parts.append(fixed)
        else:
            parts.append(piece)
        if i < len(seps):
            parts.append(seps[i])
    return "".join(parts) + summary, {"commas_removed": total, "sentences_touched": touched}


# ===========================================================================
# golden 검사 (원본 checks.py) — 방향성 게이트: 알려진 실패 모드만 잡는다
# ===========================================================================

CLICHE_PATTERNS = [
    ("기록적인 성과", r"기록적인\s*성과"), ("괄목할 만한", r"괄목할\s*만한"), ("~로 평가된다", r"로\s*평가(?:된다|받|되|됨)"),
    ("주목받-", r"주목받"), ("크게 기여", r"크게\s*기여"), ("중요한 역할을 한다", r"중요한\s*역할을\s*(?:한다|했다|할|함|하였)"),
    ("시사하는 바가 크다", r"시사하는\s*바가\s*크"), ("의미가 크다", r"의미가\s*(?:크다|큼)"),
]
_NUM_TOKEN = re.compile(r"\d+(?:[.,]\d+)*")
_KO_UNIT = {"백": 100, "천": 1_000, "만": 10_000, "억": 100_000_000, "조": 1_000_000_000_000}
_SPEECH_MARK_RE = re.compile(
    r"말했|말한다|밝혔|밝힌|강조했|강조한|언급|설명했|설명한다|전했|덧붙|지적했|지적한다|답했|묻자|물었|따르면|촉구|당부|호소|주장했|경고했"
    r"|말함|발표함|설명함|밝힘|답함|질문함|제안함|주장함|[이으]?라고\s*함"
)
_ATTRIB_AFTER_RE = re.compile(r'^["”"]?\s*(?:[이으]?라고|고|[으]?로)\s*[가-힣]{1,8}?(?:하|했|한다|된다|였|입니다|함|음|임)')


def _number_values(text: str) -> set[str]:
    values = set()
    for m in _NUM_TOKEN.finditer(text):
        tok = m.group(0).replace(",", "")
        mult = _KO_UNIT.get(text[m.end():m.end() + 1])
        if mult:
            try:
                v = float(tok) * mult
                values.add(str(int(v)) if v == int(v) else str(v))
                continue
            except ValueError:
                pass
        values.add(tok)
    return values


def _extract_quotes(text: str, min_len: int = 8) -> list[str]:
    qs = []
    for op, cl in (("「", "」"), ("『", "』"), ("“", "”")):
        qs += re.findall(re.escape(op) + r"([^" + cl + r"]+)" + re.escape(cl), text)
    parts = text.split('"')
    if len(parts) % 2 == 1:
        qs += parts[1::2]
    return [q for q in qs if len(q.strip()) >= min_len]


def _is_protected_quote(original: str, span: str) -> bool:
    i = original.find(span)
    if i < 0:
        return True
    before = original[max(0, i - 30):i]
    cut = before.rfind(". ")
    if cut >= 0:
        before = before[cut + 1:]
    after = original[i + len(span):i + len(span) + 24]
    cut = after.find(". ")
    if cut >= 0:
        after = after[:cut + 1]
    return bool(_ATTRIB_AFTER_RE.search(after) or _SPEECH_MARK_RE.search(before) or _SPEECH_MARK_RE.search(after))


def golden_checks(original: str, output: str) -> list[tuple[str, str]]:
    """(코드, 설명) 목록. 비면 PASS."""
    if not output.strip():
        return [("empty_output", "윤문본이 비어 있음")]
    fails = []
    a, b = original.count("하였"), output.count("하였")
    if b > a:
        fails.append(("hayeot_injection", f"'하였' 계열 {a} → {b}회 (격식 상향 주입)"))
    for name, pat in CLICHE_PATTERNS:
        a, b = len(re.findall(pat, original)), len(re.findall(pat, output))
        if b > a:
            fails.append(("cliche_injection", f"상투구 '{name}' {a} → {b}회 (주입 금지)"))
    for tb, ta in zip(detect_tells(original), detect_tells(output)):
        if len(ta["hits"]) > len(tb["hits"]):
            fails.append(("tell_injection", f"{tb['id']} {tb['name']} {len(tb['hits'])} → {len(ta['hits'])}회 "
                                            f"(AI 티는 빼기만 한다)"))
    for q in _extract_quotes(original):
        if q not in output and _is_protected_quote(original, q):
            fails.append(("quote_altered", f"직접 인용 「{q[:30]}」이 원문 그대로 없음 (인용 불변)"))
    injected = sorted(_number_values(output) - _number_values(original))
    if injected:
        fails.append(("number_injected", f"원문에 없던 수치: {injected} (없던 사실 주입 위험)"))
    return fails


def dropped_numbers(original: str, output: str) -> list[str]:
    return sorted(_number_values(original) - _number_values(output))


# ===========================================================================
# 내용 앵커 대조 (P6 — 원본에 없음, 머리말 12)
# 원본은 앵커 보존을 윤문 · 마무리 에이전트의 자기 점검에만 맡긴다. 그런데 standard 경로는 게이트가
# 0이면 마무리를 건너뛰어, 노력 수준 비교(2026-11-02)에서 낮음 · 중간이 진단이 '남길 낱말'로 적은
# '알고리즘의 효율성'을 지운 채 통과했다. 낱말이 통째로 사라졌는지만 코드로 본다.
# 자동으로 되살리지 않는다 — 어느 문장에 넣을지는 기계가 못 정한다(마무리가 정한다).
# ===========================================================================

_JOSA = tuple(sorted(("에서의", "으로의", "에게서", "으로써", "으로는", "에서는", "에서도", "까지", "부터", "에서",
                      "에게", "으로", "처럼", "보다", "에는", "에도", "로는", "와의", "과의", "을", "를", "이", "가",
                      "은", "는", "의", "에", "로", "와", "과", "도", "만"), key=len, reverse=True))
# 맨 어절이 용언으로 끝나는지. 명사 끝 글자와 겹치는 어미(-인 변인 · -서 순서 · -면 장면 · -기 동기 · -지 가지 ·
# -고 사고 · -여 참여 · -임 게임 · -자 문자 · -요 필요)는 홑글자로 넣지 않고 '하-' · '되-' 결합형으로만 본다.
_VERB_END = re.compile(r"(?:함|됨|짐|봄|줌|냄|씀|듦|있음|없음|었음|았음|였음|하였|했|며|면서|지만|도록|려고|고자|게|워|다|듯"
                       r"|는|은|운|던|한|된|할|될|하고|되고|지고|하여|해|해서|어서|아서|여서|워서|하면|되면|으면|하기|되기|하지|되지)$")
_VERB_TAIL = re.compile(r"(?:하|되|시키|하였|했|됐|있|없|이었|였)$")
# 평가 명사 — 틀을 걷으면 같이 빠지는 것이 정상이라 원문 자동 추출에서 뺀다('~적' 평가 관형어도 뺀다).
_ANCHOR_STOP = frozenset({"학생", "모습", "태도", "역량", "능력", "경험", "성장", "계기", "자세", "중요성", "가능성", "잠재력",
                          "사고력", "탐구력", "창의력", "문제해결력", "리더십", "열정", "자신감", "흥미"})
# 이 틀이 있는 문장은 통째로 지우는 것이 처방이라(학-2 총평 · D-11 결말 시간어 · D-12 과제 문패) 그 문장의 낱말은 뺀다.
_WHOLE_SENTENCE_TELLS = frozenset({"학-2", "D-11", "D-12"})
_QUOTED_RE = re.compile(r"'([^'\n]+)'|‘([^’\n]+)’|\"([^\"\n]+)\"|“([^”\n]+)”")


def content_stems(text: str) -> list[str]:
    """어절에서 조사를 떼어 두 글자 이상 내용어 후보를 뽑는다(형태소 분석기 없는 근사 — 원본과 같은 stdlib 원칙)."""
    out = []
    for tok in _tokens(text):
        if not re.fullmatch(r"[가-힣]+", tok):
            continue  # 수치 · 영문 · 기호가 섞인 낱말은 수치 축(P3)이 본다
        stem = next((tok[:-len(j)] for j in _JOSA if tok.endswith(j) and len(tok) - len(j) >= 2), None)
        if stem is None:
            if _VERB_END.search(tok):
                continue
            stem = tok
        if len(stem) >= 2 and not _VERB_TAIL.search(stem):
            out.append(stem)
    return out


_NEGATED_AFTER = re.compile(r"^\s*(?:으로|로|처럼)\s*(?:바꾸지|올리지|고치지|쓰지|넣지|만들지)")


def anchors_from_diagnosis(diagnosis: str) -> list[str]:
    """진단 '## 보존 지침' 절에서 따옴표로 감싼 낱말 · 구절.

    "'노력함'을 '해결함'으로 바꾸지 않음"처럼 금지 예시로 든 쪽(뒤에 '~으로 바꾸지 않음'이 붙은 따옴표)은 뺀다.
    """
    m = re.search(r"^##\s*보존\s*지침\s*$(.*?)(?=^##\s|\Z)", diagnosis, re.M | re.S)
    if not m:
        return []
    body = m.group(1)
    return [next(g for g in q.groups() if g) for q in _QUOTED_RE.finditer(body)
            if not _NEGATED_AFTER.match(body[q.end():])]


def anchors_from_text(text: str) -> list[str]:
    """진단이 없을 때 원문에서 뽑는다. 처방 대상 틀이 걸린 어절과 통째 삭제 처방 문장은 뺀다."""
    spans, whole = [], set()
    for tid, _, _, pattern, least, _, _, _ in TELLS:
        if tid == "D-11" or not pattern:
            continue
        found = [m.span() for m in re.finditer(pattern, text)]
        if len(found) >= least:
            spans += found
            if tid in _WHOLE_SENTENCE_TELLS:
                whole.update(a for a, _ in found)
    for h in _d11_hits(text):
        whole.add(text.find(h))
    out, pos = [], 0
    for sent in split_sentences(text):
        start = text.find(sent, pos)
        end = start + len(sent)
        pos = end
        if any(start <= w < end for w in whole):
            continue
        for w in re.finditer(r"\S+", sent):
            a, b = start + w.start(), start + w.end()
            if any(a < e and s < b for s, e in spans):
                continue
            out += [s for s in content_stems(w.group(0)) if s not in _ANCHOR_STOP and not s.endswith("적")]
    return list(dict.fromkeys(out))


_AMBIGUOUS_TAIL = "어아여고지기면자서"  # 명사 끝 글자이기도 하고 용언 어미이기도 한 글자


def _present(stem: str, flat: str) -> bool:
    if stem in flat:
        return True
    # '넣어' → '넣는'처럼 활용만 바뀐 용언: 마지막 글자를 뗀 어간이 어절 머리에 있으면 남은 것으로 본다.
    return (stem[-1] in _AMBIGUOUS_TAIL
            and re.search(r"(?:^|\s)" + re.escape(stem[:-1]) + r"[가-힣]", flat) is not None)


def lost_anchors(after: str, anchors: list[str]) -> list[str]:
    """앵커 구절이 그대로 있으면 통과, 아니면 그 안의 내용어가 고친 글에 한 번도 없을 때 소실."""
    flat = re.sub(r"\s+", " ", after)
    lost = []
    for a in anchors:
        if re.sub(r"\s+", " ", a.strip()) in flat:
            continue
        for s in content_stems(a):
            if not _present(s, flat) and s not in lost:
                lost.append(s)
    return lost


# ===========================================================================
# 구조 게이트 (원본 verify_gates.py) — P0~P5
# ===========================================================================

CHANGE_RATE_WARN = 0.30
CHANGE_RATE_ABORT = 0.50
S1_CANDIDATE_METRICS = ("comma_inclusion_rate", "comma_usage_rate", "ending_comma_rate",
                        "comma_segment_length", "hanja_nominalizer_density")
S1_SELECT_Z, S1_ACHIEVED_Z, S1_MISSED_Z, S1_OVERCORRECT_Z = 2.0, 1.0, 2.0, -1.5
ANNIHILATION_MIN_BEFORE = 2  # 원본 5 — 머리말 10
MODALITY_TOLERANCE = 0


def change_rate(before: str, after: str) -> float:
    if not before and not after:
        return 0.0
    return 1.0 - difflib.SequenceMatcher(None, before, after, autojunk=False).ratio()


def sentence_touch_rate(before: str, after: str) -> tuple[float, int, int]:
    bs = [_norm(s) for s in split_sentences(before) if s.strip()]
    if not bs:
        return 0.0, 0, 0
    aset = {_norm(s) for s in split_sentences(after)}
    touched = sum(1 for s in bs if s not in aset)
    return touched / len(bs), touched, len(bs)


def judge_s1(z_before: dict, z_after: dict) -> tuple[list[dict], bool]:
    res, warn = [], False
    for key in S1_CANDIDATE_METRICS:
        zb = z_before.get(key)
        if zb is None or zb <= S1_SELECT_Z:
            continue
        za = z_after.get(key)
        if za is None:
            v = "판정불가"
        elif za <= S1_OVERCORRECT_Z:
            v, warn = "과교정", True
        elif za <= S1_ACHIEVED_Z:
            v = "달성"
        elif za > S1_MISSED_Z:
            v, warn = "미달", True
        else:
            v = "부분 개선"
        res.append({"metric": key, "z_before": round(zb, 2), "z_after": None if za is None else round(za, 2), "verdict": v})
    return res, warn


def run_gate(before: str, after: str, baseline: dict | None = None,
             diagnosis: str | None = None) -> tuple[dict, int, list[str]]:
    """(보고, 종료 코드, 출력 줄). 0 수렴 · 1 경고 · 2 중단. diagnosis 가 있으면 P6 앵커를 보존 지침에서 뽑는다."""
    before, after = strip_summary_block(before), strip_summary_block(after)
    baseline = load_baseline() if baseline is None else baseline
    rep, lines, warn = {"genre": GENRE}, [], False

    rate = change_rate(before, after)
    abort = rate >= CHANGE_RATE_ABORT
    warn |= CHANGE_RATE_WARN <= rate < CHANGE_RATE_ABORT
    v0 = "ABORT — 강제 중단. 윤문본 채택 금지" if abort else ("WARN — 과윤문 경고" if rate >= CHANGE_RATE_WARN else "OK")
    rep["change_rate"] = {"rate": round(rate, 4), "verdict": v0}
    lines.append(f"[P0 문자율] {rate * 100:.1f}% — {v0} (경고 30% / 중단 50%)")

    mb, ma = compute_all(before, baseline), compute_all(after, baseline)
    za = {**ma["z_scores"], **(ma.get("z_scores_unguarded") or {})}
    s1, s1_warn = judge_s1(mb["z_scores"], za)
    report_only = mb["baseline_status"] != "보정"
    if not report_only:
        warn |= s1_warn
    rep["s1_targets"] = s1
    rep["s1_report_only"] = report_only
    tag = " (빌린 기준선 — 보고만)" if report_only else ""
    if not s1:
        lines.append("[P1 목표달성] N/A — 어휘 S1 앵커 없음" + tag)
    for r in s1:
        zs = "?" if r["z_after"] is None else f"{r['z_after']:+.2f}"
        lines.append(f"[P1 목표달성] {r['metric']}: z {r['z_before']:+.2f} → {zs}  {r['verdict']}{tag}")

    ab, aa = antithesis_count(before), antithesis_count(after)
    annihilated = ab >= ANNIHILATION_MIN_BEFORE and aa == 0
    warn |= annihilated
    v2 = "FAIL — 전멸(하나는 남긴다)" if annihilated else ("OK" if ab >= ANNIHILATION_MIN_BEFORE else f"스킵 (원문 대구 < {ANNIHILATION_MIN_BEFORE})")
    rep["antithesis"] = {"before": ab, "after": aa, "verdict": v2}
    lines.append(f"[P2 전멸] C-8 대구 {ab} → {aa} — {v2}")

    fails = golden_checks(before, after)
    dropped = dropped_numbers(before, after)
    warn |= bool(fails) or bool(dropped)
    rep["golden"] = [{"code": c, "message": m} for c, m in fails]
    rep["numbers_dropped"] = dropped
    if fails:
        lines.append(f"[P3 golden] FAIL — {len(fails)}건")
        lines += [f"    FAIL [{c}] {m}" for c, m in fails]
    else:
        lines.append("[P3 golden] PASS (수치 · 인용 · 격식 · 틀 주입 없음)")
    if dropped:
        lines.append(f"[P3 수치소실] WARN — 원문 수치 {dropped} 가 사라짐 (학생부: 메모의 횟수 · 기간은 지킨다)")

    tr, t, n = sentence_touch_rate(before, after)
    rep["sentence_touch"] = {"rate": round(tr, 4), "touched": t, "total": n}
    lines.append(f"[P4 터치율] {tr * 100:.1f}% ({t}/{n} 문장) — 보고 전용")

    losses = find_losses(before, after)
    sure = [l for l in losses if not l["low_sim"]]
    unsure = [l for l in losses if l["low_sim"]]
    mfail = len(sure) > MODALITY_TOLERANCE
    warn |= mfail
    cb, ca = count_modality(before), count_modality(after)
    rep["modality"] = {"lost_pairs": [{k: l[k] for k in ("kind", "before", "after")} for l in sure],
                       "uncertain_pairs": [{k: l[k] for k in ("kind", "before", "after")} for l in unsure],
                       "counts": {"before": cb, "after": ca},
                       "verdict": f"FAIL — 서법 소실 {len(sure)}문장" if mfail else "OK"}
    lines.append(f"[P5 서법] 소실 {len(sure)}문장 (참고 총수: " +
                 " / ".join(f"{k} {cb[k]}→{ca[k]}" for k in MODAL) + f") — {rep['modality']['verdict']}")
    for l in sure[:3]:
        lines.append(f"          [{l['kind']}] {l['before'][:34]} → {l['after'][:34]}")
    if unsure:
        lines.append(f"          관찰: 짝 유사도가 낮아 판정 보류 {len(unsure)}건 (확인 요망)")

    anchors = anchors_from_diagnosis(diagnosis) if diagnosis else []
    source = "진단 보존 지침"
    if not anchors:
        anchors, source = anchors_from_text(before), "원문 자동 추출"
    lost = lost_anchors(after, anchors)
    warn |= bool(lost)
    rep["anchors"] = {"source": source, "count": len(anchors), "lost": lost,
                      "verdict": f"WARN — 소실 {len(lost)}개" if lost else "OK"}
    lines.append(f"[P6 앵커] {source} {len(anchors)}개 중 소실 {len(lost)}개 — {rep['anchors']['verdict']}"
                 + (f": {', '.join(repr(x) for x in lost[:8])} (마무리에서 되살릴지 판단)" if lost else ""))

    code = 2 if abort else (1 if warn else 0)
    verdict = {2: "ABORT — 강제 중단. 윤문본 채택 금지", 1: "WARN — 경고. 해당 축 고지 + 마무리 승급", 0: "OK — 수렴"}[code]
    rep["gate"] = {"verdict": verdict, "exit_code": code}
    lines.append(f"gate: {verdict}")
    return rep, code, lines


# ===========================================================================
# 작업 폴더 — 동기화 폴더 금지(머리말 1)
# ===========================================================================

def run_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / RUN_ROOT_NAME


def assert_local(path: Path) -> Path:
    p = Path(path).resolve()
    low = str(p).lower()
    hit = next((mk for mk in SYNC_MARKERS if mk in low), None)
    if hit:
        raise SystemExit(f"error: 작업 폴더가 동기화 폴더({hit})입니다: {p}\n"
                         f"       학생 글은 로컬에만 둡니다. --run-dir 를 지우면 {run_root()} 를 씁니다.")
    return p


def new_run_dir() -> Path:
    root = assert_local(run_root())
    root.mkdir(parents=True, exist_ok=True)
    tag, today = secrets.token_hex(2), date.today().isoformat()
    for n in range(1, 1000):
        d = root / f"{today}-{n:03d}-{tag}"
        try:
            d.mkdir()  # 확인과 생성을 한 번에(원본 _next_run_dir)
            return d
        except FileExistsError:
            continue
    raise SystemExit("error: 작업 폴더 번호가 다 찼습니다. clean --all 로 비우십시오.")


def _read(path: Path) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def _write(path: Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


# ===========================================================================
# 기준선 보정 (원본 build_calibration.py 자리) — 숫자(평균 · 표준편차 · 편수)만 쓴다
# ===========================================================================

def calibrate(paths: list[str], split_blank: bool) -> dict:
    texts = []
    for p in paths:
        pp = Path(p)
        files = sorted(pp.rglob("*.txt")) if pp.is_dir() else [pp]
        for f in files:
            t, _ = sanitize(_read(f))
            chunks = [c.strip() for c in re.split(r"\n\s*\n", t)] if split_blank else [t.strip()]
            texts += [c for c in chunks if len(c) >= 50]
    if not texts:
        raise SystemExit("error: 50자 이상인 글이 없습니다.")
    keys = [k for k, _ in V1_KEYS] + list(FIXED_PROXY)
    rows = [compute_all(t, {})["metrics"] for t in texts]
    cells = {}
    for k in keys:
        vals = [r[k] for r in rows]
        cells[k] = {"mean": round(mean(vals), 5), "stdev": round(pstdev(vals), 5), "n": len(vals)}
        if len(vals) < CALIBRATION_MIN_N:
            cells[k]["_placeholder"] = True
    tells = Counter()
    for t in texts:
        for d in detect_tells(t):
            if d["hits"]:
                tells[d["id"]] += 1
    return {"cells": cells, "n": len(texts),
            "tell_doc_rate": {k: round(v / len(texts), 3) for k, v in sorted(tells.items())}}


# ===========================================================================
# CLI
# ===========================================================================

def _run_dir_arg(a) -> Path:
    if not a.run_dir:
        raise SystemExit("error: --run-dir 가 필요합니다(prepare 가 출력한 폴더).")
    d = assert_local(Path(a.run_dir))
    if not d.is_dir():
        raise SystemExit(f"error: 작업 폴더가 없습니다: {d}")
    return d


def cmd_prepare(a) -> int:
    if a.run_dir:
        d = assert_local(Path(a.run_dir))
        d.mkdir(parents=True, exist_ok=True)
    else:
        d = new_run_dir()
    src = d / "01_input.txt"
    if a.input:
        text = _read(Path(a.input))
    elif src.exists():
        text = _read(src)
    else:
        text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    if not text.strip():
        raise SystemExit("error: 입력이 비었습니다.")
    text, san = sanitize(text)
    _write(src, text)
    if san:
        _write(d / "00_sanitize.json", json.dumps(san, ensure_ascii=False, indent=1))
    m = compute_all(text)
    if a.strict:
        m["route_hint"], m["route_reason"] = "heavy", "사용자 지정(정밀) — route_hint 무시"
    _write(d / "00_metrics.json", json.dumps(m, ensure_ascii=False, indent=1))
    diag = _read(Path(a.diagnosis)) if a.diagnosis else None
    _write(d / "01_input_with_metrics.txt", render_combined(text, m, diag))
    print(f"run_dir={d}")
    print(f"route_hint={m['route_hint']}  ({m['route_reason']})")
    print(f"기준선={m['baseline_status']}  risk_band={m['risk_band']}  처방 대상 틀="
          + (", ".join(f"{t['id']}×{len(t['hits'])}" for t in m["tells"] if t["met"]) or "없음"))
    if san:
        print("위생: " + " · ".join(f"{k} {v}" for k, v in san.items()))
    return 0


def cmd_restore(a) -> int:
    d = _run_dir_arg(a)
    before, final = _read(d / "01_input.txt"), d / "final.txt"
    if not final.exists():
        raise SystemExit(f"error: 윤문본이 없습니다: {final}")
    after = _read(final)
    after, restored, skipped = restore_modality(before, after)
    after, commas = strip_injected_commas(before, after, all_sentences=a.all_commas)
    _write(final, after)
    _write(d / "03_restore.json", json.dumps({"restored": restored, "skipped": skipped, "commas": commas},
                                            ensure_ascii=False, indent=1))
    print(f"[서법 복원] 복원 {len(restored)}문장 / 보류 {len(skipped)}문장")
    for r in restored:
        print(f"  [{r['kind']}] {r['after'][:40]} → 원문")
    for s in skipped:
        print(f"  (보류) {s['after'][:40]} — {s['reason']}")
    print(f"[쉼표 역주입] 제거 {commas['commas_removed']}개 / {commas['sentences_touched']}문장"
          + (" (--all-commas: 전 문장)" if a.all_commas else " (윤문이 새로 쓴 문장만)"))
    return 0


def cmd_gate(a) -> int:
    diag_path = Path(a.diagnosis) if a.diagnosis else None
    if a.before and a.after:
        before, after = _read(Path(a.before)), _read(Path(a.after))
        out_dir = None
    else:
        d = _run_dir_arg(a)
        before, after, out_dir = _read(d / "01_input.txt"), _read(d / "final.txt"), d
        if diag_path is None and (d / "02_diagnosis.md").exists():
            diag_path = d / "02_diagnosis.md"
    rep, code, lines = run_gate(before, after, diagnosis=_read(diag_path) if diag_path else None)
    print("\n".join(lines))
    if out_dir:
        _write(out_dir / "04_gate.json", json.dumps(rep, ensure_ascii=False, indent=1))
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    return code


def cmd_metrics(a) -> int:
    text, _ = sanitize(_read(Path(a.file)) if a.file else sys.stdin.buffer.read().decode("utf-8", "replace"))
    print(render_block(compute_all(text)))
    return 0


def cmd_calibrate(a) -> int:
    res = calibrate(a.paths, a.split_blank)
    base = load_baseline()
    base.setdefault("genres", {})[GENRE] = res["cells"]
    base["calibration"] = {"date": date.today().isoformat(), "n": res["n"], "tell_doc_rate": res["tell_doc_rate"],
                           "note": "사람이 쓴 학생부 글의 지표 평균 · 표준편차 · 편수만 담는다. 글은 담지 않는다."}
    out = Path(a.out) if a.out else BASELINE_PATH
    _write(out, json.dumps(base, ensure_ascii=False, indent=1) + "\n")
    print(f"글 {res['n']}편 → {out}")
    for k, c in res["cells"].items():
        print(f"  {k}: 평균 {c['mean']} · 표준편차 {c['stdev']}" + (" (편수 부족 — 판정에 안 씀)" if c.get("_placeholder") else ""))
    print("  틀이 한 번이라도 나온 글의 비율(사람 글 오탐률): " +
          (", ".join(f"{k} {v:.0%}" for k, v in res["tell_doc_rate"].items()) or "없음"))
    return 0


def cmd_clean(a) -> int:
    targets = []
    if a.all:
        root = run_root()
        targets = [p for p in root.iterdir() if p.is_dir()] if root.exists() else []
    elif a.run_dir:
        d = assert_local(Path(a.run_dir))
        if d.parent != run_root().resolve():
            raise SystemExit(f"error: {run_root()} 아래 작업 폴더만 지웁니다.")
        targets = [d]
    for t in targets:
        shutil.rmtree(t, ignore_errors=True)
    print(f"작업 폴더 {len(targets)}개 삭제")
    return 0


def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="학생부 AI 문체 윤문 — im-not-ai 파이프라인 학생부판")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="위생 · 정량 점수 · route_hint · 결합 입력")
    p.add_argument("--input", help="초안 파일(없으면 run-dir 의 01_input.txt, 그것도 없으면 표준입력)")
    p.add_argument("--run-dir", help="작업 폴더(없으면 새로 만든다)")
    p.add_argument("--diagnosis", help="진단 파일 — 결합 입력 앞에 붙인다")
    p.add_argument("--strict", action="store_true", help="정밀(heavy) 고정")
    p.set_defaults(fn=cmd_prepare)
    p = sub.add_parser("restore", help="서법 복원 + 쉼표 역주입 제거(final.txt 를 고친다)")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--all-commas", action="store_true", help="진단이 C-11 을 지목했을 때만 — 전 문장 쉼표 제거")
    p.set_defaults(fn=cmd_restore)
    p = sub.add_parser("gate", help="게이트 P0~P6(0 수렴 · 1 경고 · 2 중단 · 3 판정 불가)")
    p.add_argument("--run-dir")
    p.add_argument("--before")
    p.add_argument("--after")
    p.add_argument("--diagnosis", help="진단 파일(없으면 run-dir 의 02_diagnosis.md, 그것도 없으면 원문에서 앵커를 뽑는다)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_gate)
    p = sub.add_parser("metrics", help="점수 블록만 출력")
    p.add_argument("file", nargs="?")
    p.set_defaults(fn=cmd_metrics)
    p = sub.add_parser("calibrate", help="사람이 쓴 학생부 글로 기준선 계산")
    p.add_argument("paths", nargs="+", help="글 파일 또는 폴더(.txt) — 파일 하나가 글 하나")
    p.add_argument("--split-blank", action="store_true", help="파일 하나에 여러 글이 빈 줄로 나뉘어 있을 때")
    p.add_argument("--out", help=f"기준선 파일(기본 {BASELINE_PATH.name})")
    p.set_defaults(fn=cmd_calibrate)
    p = sub.add_parser("clean", help="작업 폴더 삭제")
    p.add_argument("--run-dir")
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_clean)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
