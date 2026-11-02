#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""학교생활기록부 서술형 항목 초안 정적 검사기.

세특(과목별/개인별 세부능력 및 특기사항)과 행특(행동특성 및 종합의견) 초안을
NEIS 입력 전에 기계적으로 검사한다. 사람이 매번 눈으로 세지 말아야 할 것만 센다.

검사 항목
  1. 분량      — NEIS Byte(한글 3B / 그 외 1B) 기준 목표 대비 초과·임박·미달
  2. 금칙어    — 기재금지사항에 해당하는 단어·패턴 탐지
  3. 문자      — 한자·영어 외 외국 문자(기재 불가), 글머리표·번호·특수문자(지양)
  4. 문체      — 개조식 서술형(~함/~하였음/~보임 등) 종결 여부
  5. 개별성    — 여러 학생 초안 간 문장 중복률
  6. AI 문체   — student_record_humanize.py(im-not-ai 학생부판) 틀 표의 처방 대상(WARN), E-1 리듬(INFO)
  7. 윤문 게이트 — --before 원래초안: 같은 모듈의 게이트 P0~P6(변경률·목표·대구 전멸·주입·수치·서법·앵커)

규칙 정본: ../references/2. 기재요령 핵심 (2026 중학교).md

분량 단위는 Byte다(NEIS가 Byte로 센다: 한글 3B / 영문·숫자 1B / 엔터 1B).
매 작업마다 --limit(Byte) 또는 --chars(한글자)로 지정하는 것이 원칙이다.
생략하면 DEFAULT_LIMITS 폴백을 쓰고 그 사실을 출력한다.
지정값이 기재요령 표기 상한을 넘으면 경고만 내고 계속한다.

사용법
  단일 초안(표준입력):
    python student_record_check.py --type 세특 --limit 1500 < draft.txt

  단일 초안(파일):
    python student_record_check.py --type 행특 --limit 900 draft.txt

  여러 학생 일괄(개별성 비교 포함):
    python student_record_check.py --type 세특 --limit 1500 반전체/*.txt

종료 코드: 0 = 통과, 1 = 위반 검출, 2 = 잘못된 인자(--type 오타 등)
"""

import argparse
import glob
import os
import re
import sys
import unicodedata

# 분량 단위는 Byte다. NEIS가 Byte로 세기 때문이다(한글 3B / 영문·숫자 1B / 엔터 1B).
# 목표 분량 기본값(Byte). 매 작업마다 --limit 로 지정하는 것이 원칙이고, 아래는 폴백일 뿐이다.
DEFAULT_LIMITS = {
    "세특": 1500,
    "과목별세특": 1500,
    "개인별세특": 1500,
    "행특": 900,      # 2026 최대. 한글 약 300자
    "자율자치": 1500,
    "자율": 1500,     # 3학년(2015 개정) 영역명
    "동아리": 1500,
    "진로": 1500,
    "자유학기": 1500,  # 범용 지침 기본 목표. 최대는 3,000
}

# 「2026학년도 학교생활기록부 기재요령(중)」 [참고자료 7](162쪽) 최대 글자수(Byte 환산).
# 2025학년도 대비 행특 1,500 → 900, 진로 2,100 → 1,500.
# 지정값이 이 값을 넘으면 경고만 내고 검사는 지정값 기준으로 계속한다.
SPEC_LIMITS = {
    "세특": 1500,
    "과목별세특": 1500,
    "개인별세특": 1500,
    "행특": 900,
    "자율자치": 1500,
    "자율": 1500,
    "동아리": 1500,
    "진로": 1500,
    "자유학기": 3000,
}

# 문자 규칙(기재요령 28·30쪽). 한글 원칙, 부득이한 경우 영문만. 한자 등 다른 외국어 불가.
FOREIGN_SCRIPT = [
    ("한자", r"[㐀-䶿一-鿿豈-﫿]",
     "한자는 학생부에 쓸 수 없음(한문 과목 포함). 한글 음이나 뜻으로 바꿀 것"),
    ("외국 문자", r"[぀-ヿЀ-ӿͰ-Ͽ฀-๿؀-ۿ]",
     "영어 외 외국어 문자는 쓸 수 없음. 한글로 바꿀 것"),
]
BULLET = (r"(?m)^\s*(?:[0-9]+[.)]|[-*•·▪○●□■◆▶]|[①-⑳])\s*",
          "특수문자·문단 구분 기호(번호) 입력 지양. 문장으로 이어 쓸 것")
# 문장 안 특수문자(기재요령 30쪽 '지양'). 가운뎃점·괄호·따옴표·마침표류는 일상 표기라 뺀다.
SPECIAL = (r"[→←↑↓⇒⇔※★☆♥♡◎◇△▲▽▼▷@^|「」『』【】《》〈〉{}\[\]]",
           "특수문자 입력 지양. 낱말로 풀어 쓸 것")

# 기재금지사항 탐지 패턴. (라벨, 정규식, 설명)
# 오탐이 나올 수 있는 항목은 [주의]로 표시하고 사람이 최종 판단한다.
BANNED = [
    ("대회·수상", r"대회|수상|입상|우승|준우승|최우수상|우수상|장려상|공모전|경진",
     "'대회' 용어 자체가 수상경력 이외 항목에서 금칙어. 명칭을 행사로 바꾸는 우회도 불가"),
    ("상·표창", r"표창|감사장|공로상|"
               r"(장관|교육감|교육장|군수|구청장|도지사|(?<![가-힣])시장|(?<![가-힣])의장)상(?=[을를이과와은도에으,.\s]|$)",
     "교외상(표창장·감사장·공로상 포함)은 어느 항목에도 기재 불가, 교내상은 수상경력 항목에만"),
    ("자격증", r"자격증|자격(을)? ?취득|[0-9]+급(을|에)? ?(자격|취득|합격)|급수 ?(시험|자격|취득)|검정 합격|자격 ?시험",
     "자격증 명칭 및 취득 사실 기재 불가"),
    ("공인어학시험", r"TOEIC|TOEFL|TEPS|HSK|JPT|JLPT|DELF|DALF|TESTDAF|TORFL|DELE|한자능력검정|한검",
     "공인어학시험 참여 사실·성적·수상실적 기재 불가"),
    ("인증시험", r"인증시험|인증 시험|모의고사 등급|급수 인증",
     "교내·외 인증시험 참여 사실이나 성적 기재 불가"),
    ("논문·출간·특허", r"논문|학회|투고|등재|저서 출간|도서 출간|출간함|특허|실용신안|지식재산권|상표 등록",
     "논문 투고·등재·발표, 도서출간, 지식재산권 출원·등록 사실 기재 불가"),
    ("해외활동", r"어학연수|해외 봉사|해외봉사|해외 연수|현지 학교|교환학생",
     "어학연수·봉사활동 등 해외 활동실적 및 관련 내용 기재 불가"),
    ("부모 지위", r"아버지(가|는|의)|어머니(가|는|의)|부모(가|는|의) (직업|회사|근무)|가정 형편|아버님|어머님",
     "[주의] 부모·친인척의 사회·경제적 지위 암시 내용 기재 불가"),
    ("장학금", r"장학금|장학생|장학 재단",
     "장학생·장학금 관련 내용 기재 불가"),
    ("대학·기관명", r"[가-힣A-Za-z]{2,}(대학교|대학|고등학교 부설|연구원|연구소|재단|협회|학회|공사|공단)",
     "[주의] 구체적 대학명·기관명 기재 불가. 교육부/시도교육청/교육지원청 계열만 예외"),
    ("상호·제품명", r"구글|Google|코랩|Colab|엑셀|Excel|파워포인트|PowerPoint|한글과컴퓨터|"
                    r"챗지피티|ChatGPT|GPT-?[0-9]|Claude|클로드|제미나이|Gemini|퍼플렉시티|Perplexity|"
                    r"유튜브|YouTube|네이버|카카오|인스타그램|틱톡|TikTok|"
                    r"아두이노|Arduino|마이크로비트|micro:bit|햄스터봇|Scratch|앱 ?인벤터|"
                    r"티처블 ?머신|Teachable Machine|오토드로우|파파고|뤼튼|코파일럿|Copilot|"
                    r"캔바|Canva|미리캔버스|패들렛|Padlet|띵커벨|클래스팅|노션|Notion|ZEP|한컴|아이패드|iPad|크롬북",
     "상업 제품명·브랜드명 기재 불가. 일반 기술·제품군 명칭으로 치환할 것"),
    ("상호·제품명", r"엔트리|스크래치",
     "[주의] 교육용 프로그래밍 환경 이름이면 '블록 기반 프로그래밍 환경'으로 치환. 일반 낱말이면 무시"),
    ("강사명", r"강사(님)?(이|가|은|께서)|외부 강사 [가-힣]{2,4}",
     "[주의] 강사명 기재 불가"),
    ("MOOC", r"K-?MOOC|MOOC|KOCW",
     "K-MOOC, MOOC, KOCW 기재 불가"),
    ("방과후학교", r"방과후학교|방과후 학교|방과후 수업",
     "방과후학교 활동은 세특·행특 등에 기재 불가(기재요령 104·116쪽)"),
    ("정치활동", r"정당 ?(활동|가입)|정당에 가입|선거운동|당원으로|정치 ?활동에 참여",
     "[주의] 정치활동 참여 관련 사항은 출결 특기사항 외 어디에도 기재 불가(기재요령 56쪽)"),
    ("기부", r"(?<!동)기부",
     "[주의] 물품·현금의 단순 기부는 어느 항목에도 기재 불가(기재요령 82쪽)"),
]

GIFTED = r"영재교육|영재학급|영재학교"

# 행특 전용 추가 금칙(개인 봉사활동)
BANNED_HAENGTEUK = [
    ("개인 봉사활동", r"개인(적으로)? (봉사|봉사활동)|가족과 함께 봉사",
     "개인계획에 따른 봉사활동 특기사항은 행특 기재 불가(학교교육계획 봉사활동만 가능)"),
    ("영재교육", GIFTED,
     "영재교육 관련 내용은 행특 기재 불가(기재요령 116쪽). 관련 교과 세특의 영재교육 기록사항에 입력"),
]

# 창체·자유학기 추가 금칙(항목 혼동). 세특·개인별세특은 영재교육 이수 내용을 쓸 수 있다(104쪽).
BANNED_CHANGCHE = [
    ("영재교육 위치", GIFTED,
     "[주의] 영재교육 이수 내용은 관련 교과 세특(영재교육 기록사항) 또는 개인별 세특에 입력"),
]

# 항목 유형별 추가 금칙. 세특·과목별세특·개인별세특은 공통 금칙만 본다.
EXTRA_RULES = {"행특": BANNED_HAENGTEUK}
EXTRA_RULES.update((k, BANNED_CHANGCHE) for k in ("자율자치", "자율", "동아리", "진로", "자유학기"))

# 개조식 서술형 종결 판정.
# 학생부 종결은 사실상 명사형 어미 '-(으)ㅁ'이므로, 어미 목록을 나열하는 대신
# 마지막 음절의 종성이 'ㅁ'인지 본다. 나열식은 '학생임'·'만들어 감'·'갖춤' 등을
# 오탐으로 잡는다(2026-08-18 수정).
_NOMINAL_JONG = (16, 10)  # 명사형 종성 인덱스: ㅁ, ㄻ(만듦·줄어듦)


def is_gaejo_ending(sentence):
    s = sentence.rstrip().rstrip(".!?").rstrip()
    if not s:
        return False
    ch = s[-1]
    if not ("가" <= ch <= "힣"):
        return False
    return (ord(ch) - ord("가")) % 28 in _NOMINAL_JONG

# 추상적 상찬 표현(금지는 아니나 구체화 필요)
VAGUE = [
    "열정적", "성실하", "적극적", "훌륭한", "대단한", "최고의",
    "리더십이 있", "책임감이 강", "밝고 명랑", "예의 바르",
]

# AI 문체 틀과 윤문 게이트는 student_record_humanize.py(im-not-ai 학생부판) 한 곳에만 있다.
# 이 검사기는 그 틀 표로 처방 대상만 WARN 으로 보이고, --before 는 그 게이트를 그대로 돌린다.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import student_record_humanize as humanize  # noqa: E402


def neis_bytes(text):
    """NEIS 입력 바이트 수. 한글(및 기타 다바이트 문자) 3B, ASCII 1B, 개행 1B.

    엔터 1회 = 1B 이므로 Windows 줄바꿈(\\r\\n)은 하나로 센다.
    """
    text = text.replace("\r\n", "\n")
    total = 0
    for ch in text:
        if ch in ("\n", "\r"):
            total += 1
        elif ord(ch) < 128:
            total += 1
        else:
            total += 3
    return total


def hangul_equiv(text):
    """한글 기준 환산 글자수. NEIS 바이트를 3으로 나눈 상한 개념."""
    return neis_bytes(text) / 3.0


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def normalize(s):
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w가-힣]", "", s)
    return s


def check_one(name, text, kind, cap_bytes):
    findings = []

    # 1. 분량
    chars = len(re.sub(r"\s", "", text))
    b = neis_bytes(text)
    he = hangul_equiv(text)
    if b > cap_bytes:
        findings.append(
            ("분량초과", "ERROR",
             "%d Byte로 목표 %d Byte(한글 약 %d자) 초과. %d Byte 감축 필요"
             % (b, cap_bytes, cap_bytes // 3, b - cap_bytes)))
    elif b > cap_bytes * 0.98:
        findings.append(
            ("분량임박", "WARN",
             "%d Byte로 목표의 %.1f%%. 학기 분할 입력 시 합계가 상한임에 주의"
             % (b, b / cap_bytes * 100)))
    elif b < cap_bytes * 0.90:
        findings.append(
            ("분량미달", "INFO",
             "%d Byte로 목표의 %.1f%%. 문장을 늘려 채우지 말고 교사에게 추가 관찰(판단 근거 장면)을 물어 채울 것"
             % (b, b / cap_bytes * 100)))

    # 2. 금칙어
    rules = BANNED + EXTRA_RULES.get(kind, [])
    for label, pattern, desc in rules:
        for m in re.finditer(pattern, text):
            sev = "WARN" if desc.startswith("[주의]") else "ERROR"
            findings.append(
                ("금칙:" + label, sev,
                 "'%s' — %s" % (m.group(0), desc)))

    # 3. 문자
    for label, pattern, desc in FOREIGN_SCRIPT:
        hits = re.findall(pattern, text)
        if hits:
            findings.append(
                ("문자:" + label, "ERROR",
                 "'%s' 등 %d자 — %s" % ("".join(hits[:5]), len(hits), desc)))
    for m in re.finditer(BULLET[0], text):
        findings.append(
            ("문자:글머리", "WARN",
             "'%s' — %s" % (m.group(0).strip(), BULLET[1])))
    specials = sorted(set(re.findall(SPECIAL[0], text)))
    if specials:
        findings.append(
            ("문자:특수문자", "WARN",
             "'%s' — %s" % (" ".join(specials), SPECIAL[1])))

    # 4. 문체
    sents = split_sentences(text)
    for s in sents:
        if len(s) < 4:
            continue
        if not is_gaejo_ending(s):
            findings.append(
                ("문체", "WARN",
                 "개조식 종결 아님: ...%s" % s[-24:]))

    # 5. 추상 표현
    for v in VAGUE:
        if v in text:
            findings.append(
                ("추상표현", "INFO",
                 "'%s' — 판단 근거가 된 구체적 행동으로 치환 권장" % v))

    # 6. AI 문체 틀 — 기준 횟수 이상인 처방 대상만(E-1 리듬은 INFO)
    for t in humanize.detect_tells(text):
        if t["met"]:
            for h in t["hits"]:
                findings.append(("AI:%s" % t["id"], "WARN",
                                 "%s '%s' — %s (%d회, 기준 %d회 · %s · %s)"
                                 % (t["name"], h, t["fix"], len(t["hits"]), t["least"], t["sev"], t["basis"])))
    e1 = humanize.e1_signal(text)
    if e1 and e1["met"]:
        findings.append(
            ("AI:E-1 리듬", "INFO",
             "문장 %d개가 모두 30~50자 부근이고 100자 이상 장문이 없음(가장 긴 문장 %d자). 인접 사실 문장을 이어 장문 하나를 만들 수 있음(내용 추가 금지)"
             % (e1["sentences"], e1["longest"])))

    return {
        "name": name,
        "chars": chars,
        "bytes": b,
        "hangul_equiv": he,
        "cap_bytes": cap_bytes,
        "sentences": len(sents),
        "findings": findings,
        "sents": sents,
        "text": text,
    }


def rewrite_gate(before, after):
    """AI 문체를 고친 뒤의 결정적 검증 — student_record_humanize 의 게이트(P0~P6)를 그대로 돌린다(앵커는 원문 자동 추출).

    중단(변경률 50% 이상)과 수치 주입·소실은 ERROR(출력 전에 고친다), 나머지 경고 축은 WARN.
    """
    rep, code, _ = humanize.run_gate(before, after)
    out = []
    rate = rep["change_rate"]["rate"] * 100
    if code == 2:
        out.append(("게이트:P0 변경률", "ERROR", "%.0f%% — 과윤문. 고친 글을 버리고 원래 초안에서 덜 고쳐 다시 할 것" % rate))
    elif rate >= humanize.CHANGE_RATE_WARN * 100:
        out.append(("게이트:P0 변경률", "WARN", "%.0f%% — 과윤문 의심. 내용 앵커가 남았는지 대조할 것" % rate))
    else:
        out.append(("게이트:P0 변경률", "INFO", "%.0f%%" % rate))
    if not rep["s1_report_only"]:
        for r in rep["s1_targets"]:
            if r["verdict"] in ("미달", "과교정"):
                out.append(("게이트:P1 목표", "WARN", "%s z %+.2f → %s %s" % (r["metric"], r["z_before"], r["z_after"], r["verdict"])))
    if rep["antithesis"]["verdict"].startswith("FAIL"):
        out.append(("게이트:P2 전멸", "WARN", "C-8 대구 %d → 0회. 하나는 남길 것" % rep["antithesis"]["before"]))
    for g in rep["golden"]:
        sev = "ERROR" if g["code"] == "number_injected" else "WARN"
        out.append(("게이트:P3 " + ("주입" if g["code"].endswith("injection") else g["code"]), sev, g["message"]))
    for n in rep["numbers_dropped"]:
        out.append(("게이트:P3 수치", "ERROR", "'%s' 이(가) 고친 글에서 빠짐. 수치는 건드리지 않음" % n))
    for l in rep["modality"]["lost_pairs"]:
        out.append(("게이트:P5 서법", "WARN", "[%s] '%s' → '%s' — 원래 문장으로 되돌릴 것(restore)" % (l["kind"], l["before"][:30], l["after"][:30])))
    for a in rep["anchors"]["lost"]:
        out.append(("게이트:P6 앵커", "WARN", "'%s' 이(가) 고친 글에서 사라짐(%s). 사실이면 되살리고, 지운 껍데기면 그대로 둘 것" % (a, rep["anchors"]["source"])))
    return out


def check_overlap(results, threshold=0.6):
    """학생 간 문장 중복 검사. 개별성 위반 신호."""
    dupes = []
    norm = {}
    for r in results:
        norm[r["name"]] = set(normalize(s) for s in r["sents"] if len(s) >= 10)
    names = [r["name"] for r in results]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = norm[names[i]], norm[names[j]]
            if not a or not b:
                continue
            inter = a & b
            ratio = len(inter) / min(len(a), len(b))
            if ratio >= threshold:
                dupes.append((names[i], names[j], ratio, len(inter)))
    return dupes


def decode_text(raw):
    """UTF-8(BOM 포함)로 읽고, 안 되면 메모장 ANSI 저장본(cp949)으로 읽는다."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def main():
    # Windows 콘솔 기본 인코딩(cp949)에서 출력·입력이 깨지지 않도록 UTF-8로 맞춘다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="학교생활기록부 서술형 항목 초안 검사")
    ap.add_argument("files", nargs="*", help="검사할 초안 파일(미지정 시 표준입력)")
    ap.add_argument("--type", dest="kind", default="세특", choices=list(DEFAULT_LIMITS),
                    help="항목 유형(기본 세특)")
    ap.add_argument("--limit", type=int, default=None,
                    help="이번 작업의 목표 분량(Byte). 매번 지정하는 것이 원칙")
    ap.add_argument("--chars", type=int, default=None,
                    help="목표 분량을 한글 글자수로 지정(내부에서 x3 Byte로 환산)")
    ap.add_argument("--before", default=None,
                    help="AI 문체를 고치기 전 초안. 지정하면 윤문 게이트(변경률·수치·틀 주입)를 함께 본다")
    args = ap.parse_args()

    if args.limit and args.chars:
        ap.error("--limit(Byte)와 --chars(한글자)는 함께 쓸 수 없습니다.")

    if args.limit:
        cap, cap_src = args.limit, "지정"
    elif args.chars:
        cap, cap_src = args.chars * 3, "지정(한글 %d자 환산)" % args.chars
    else:
        cap, cap_src = DEFAULT_LIMITS[args.kind], "기본값"

    spec = SPEC_LIMITS.get(args.kind)

    targets = []
    for pat in args.files:
        expanded = glob.glob(pat)
        targets.extend(expanded if expanded else [pat])

    results = []
    if targets:
        for path in targets:
            if not os.path.isfile(path):
                print("건너뜀(파일 없음): %s" % path)
                continue
            with open(path, "rb") as f:
                results.append(check_one(os.path.basename(path), decode_text(f.read()), args.kind, cap))
    else:
        text = decode_text(sys.stdin.buffer.read())
        if not text.strip():
            ap.error("검사할 내용이 없습니다. 파일을 지정하거나 표준입력으로 넘기세요.")
        results.append(check_one("(표준입력)", text, args.kind, cap))

    if args.before:
        if len(results) != 1:
            ap.error("--before 는 초안 하나와만 쓸 수 있습니다.")
        with open(args.before, "rb") as f:
            results[0]["findings"] += rewrite_gate(decode_text(f.read()), results[0]["text"])

    has_error = False
    print("=" * 68)
    print("학교생활기록부 서술형 항목 검사 | 유형: %s | 목표: %d Byte(한글 약 %d자, %s)"
          % (args.kind, cap, cap // 3, cap_src))
    if spec and cap > spec:
        print("주의: 2026 기재요령 [참고자료 7] 최대는 %d Byte(한글 %d자)입니다."
              % (spec, spec // 3))
        print("      지정값 기준으로 검사하되, 소속교 NEIS 실측 상한을 확인하십시오.")
    print("=" * 68)

    for r in results:
        print()
        print("[%s]" % r["name"])
        print("  분량: %d Byte / %d Byte  (한글 환산 %.0f자, 공백제외 %d자, %d문장)"
              % (r["bytes"], r["cap_bytes"], r["hangul_equiv"], r["chars"], r["sentences"]))
        if not r["findings"]:
            print("  지적사항 없음")
            continue
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        for label, sev, msg in sorted(r["findings"], key=lambda x: order[x[1]]):
            if sev == "ERROR":
                has_error = True
            print("  %-5s %-14s %s" % (sev, label, msg))

    if len(results) > 1:
        dupes = check_overlap(results)
        print()
        print("-" * 68)
        print("개별성 검사(학생 간 문장 중복)")
        if not dupes:
            print("  중복 문장 비율 60% 이상인 쌍 없음")
        else:
            has_error = True
            for a, b, ratio, n in dupes:
                print("  ERROR %s ↔ %s : 중복률 %.0f%% (동일 문장 %d개)"
                      % (a, b, ratio * 100, n))

    print()
    print("=" * 68)
    print("※ 이 검사는 기계적 정적 검사입니다. 사실 검증(관찰 기록과의 대조),")
    print("   과장 여부, 항목 적합성은 반드시 교사가 직접 확인해야 합니다.")
    print("   기재요령 유의사항 4-다가 요구하는 것은 수정이 아니라 '최종 입력 전 확인'입니다.")
    print("   확인을 마쳤다면 초안 문장이 그대로 입력되어도 조문 요건은 충족됩니다.")
    print("=" * 68)

    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
