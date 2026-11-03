#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Releases 에 붙일 스킬 zip 두 개를 만든다.

  saenggibu-claude.zip  — 스킬 폴더가 zip 맨 위에 있다(school-record-draft/SKILL.md).
                          Claude 앱·claude.ai 업로드 규격. Antigravity 등은 풀어서 폴더째 복사.
  saenggibu-gemini.zip  — SKILL.md 가 zip 맨 위에 있다. Gemini 앱 업로드 규격.
  saenggibu-chatgpt.zip — 스킬 기능이 없는 서비스(ChatGPT 프로젝트 · 맞춤형 GPT 등)용. 지침 md 일곱 개 +
                          바이트 계산기 + 설정 안내(docs/ChatGPT 설정 방법.md → '먼저 읽어 주세요.md')만 담는다.

사용법: python tools/build_release.py [출력 폴더(기본 dist)]
"""

import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = "school-record-draft"
SKILL_DIR = os.path.join(ROOT, "skills", SKILL)


def skill_files():
    for d, dirs, files in os.walk(SKILL_DIR):
        # 숨김 파일과 캐시는 Gemini 업로드를 실패하게 만든다.
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and x != "__pycache__")
        for f in sorted(files):
            if f.startswith(".") or f.endswith(".pyc"):
                continue
            path = os.path.join(d, f)
            yield path, os.path.relpath(path, SKILL_DIR).replace(os.sep, "/")


def build(out_path, prefix):
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path, rel in skill_files():
            z.write(path, prefix + rel)
    with zipfile.ZipFile(out_path) as z:
        names = z.namelist()
        assert z.testzip() is None
    assert prefix + "SKILL.md" in names, out_path
    print("%s  (%d files)" % (out_path, len(names)))


CHATGPT_DIR = "생기부 지침 (ChatGPT용)/"


def build_chatgpt(out_path):
    refs = os.path.join(SKILL_DIR, "references")
    md = sorted(f for f in os.listdir(refs) if f.endswith(".md"))
    assert len(md) == 7 and md[0].startswith("0.") and md[-1].startswith("6."), md
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(ROOT, "docs", "ChatGPT 설정 방법.md"), CHATGPT_DIR + "먼저 읽어 주세요.md")
        for f in md:
            z.write(os.path.join(refs, f), CHATGPT_DIR + f)
        z.write(os.path.join(ROOT, "tools", "바이트 계산기.html"), CHATGPT_DIR + "바이트 계산기.html")
    with zipfile.ZipFile(out_path) as z:
        names = z.namelist()
        assert z.testzip() is None
    print("%s  (%d files)" % (out_path, len(names)))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
    os.makedirs(out, exist_ok=True)
    build(os.path.join(out, "saenggibu-claude.zip"), SKILL + "/")
    build(os.path.join(out, "saenggibu-gemini.zip"), "")
    build_chatgpt(os.path.join(out, "saenggibu-chatgpt.zip"))


if __name__ == "__main__":
    main()
