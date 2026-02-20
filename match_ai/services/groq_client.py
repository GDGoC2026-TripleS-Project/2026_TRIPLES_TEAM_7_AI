from __future__ import annotations
from dotenv import load_dotenv
import json, os
from fastapi import HTTPException
from groq import AsyncGroq

load_dotenv()

client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])


def build_comment_prompt(ctx: dict, match_percent: int) -> str:
    def fmt(lst): return ", ".join(lst) if lst else "없음"

    return f"""
당신은 채용 전문가 AI입니다.
**모든 comment는 반드시 한국어로만 작성하세요. 영어 기술 스택 명칭(React, TypeScript 등)은 그대로 사용하되, 설명은 한국어로만 작성하세요. 중국어, 일본어 등 다른 언어는 절대 사용하지 마세요.**
아래는 이력서와 채용 공고를 비교 분석한 결과입니다.
이 데이터를 바탕으로 JSON만 반환하세요. 설명이나 마크다운 없이 JSON만 출력하세요.

## 분석 결과 데이터
- 최종 매칭 점수: {match_percent}점
- 필수 스택 중 이력서에 있는 것: {fmt(ctx['necessary_matched'])}
- 필수 스택 중 이력서에 없는 것: {fmt(ctx['necessary_unmatched'])}
- 우대 스택 중 이력서에 있는 것: {fmt(ctx['prefer_matched'])}
- 우대 스택 중 이력서에 없는 것: {fmt(ctx['prefer_unmatched'])}
- 담당 업무 중 경험 있는 것: {fmt(ctx['role_matched'])}
- 담당 업무 중 경험 없는 것: {fmt(ctx['role_unmatched'])}
- 요구 경력: {fmt(ctx['experienceLevel'])}
- 고용 형태: {fmt(ctx['employmentType'])}
- 근무지: {ctx['locationText'] or '미제공'}
- 근무일: {ctx['workDay'] or '미제공'}

## 각 항목 작성 기준
- strengthTop3: 이력서가 공고와 잘 맞는 강점 3개, 각 comment는 "React 실무 경험 보유" 처럼 기술명 + 짧은 설명으로 20자 내외 작성
- gapTop3: 공고 요건 중 이력서에서 부족한 항목 3개, 각 comment는 "TypeScript 경험 부족" 처럼 기술명 + 짧은 설명으로 20자 내외 작성
  - isRequired: 필수 스택이면 true, 우대 스택이면 false
- riskTop3: 지원 시 주의해야 할 리스크 3개, 각 comment는 "경력 요건 미충족" 처럼 상황 + 짧은 설명으로 20자 내외 작성

## 출력 형식 (JSON만)
{{
  "strengthTop3": [
    {{"comment": "강점 설명"}},
    {{"comment": "강점 설명"}},
    {{"comment": "강점 설명"}}
  ],
  "gapTop3": [
    {{"comment": "부족한 항목", "isRequired": true}},
    {{"comment": "부족한 항목", "isRequired": false}},
    {{"comment": "부족한 항목", "isRequired": false}}
  ],
  "riskTop3": [
    {{"comment": "리스크 설명"}},
    {{"comment": "리스크 설명"}},
    {{"comment": "리스크 설명"}}
  ]
}}
""".strip()


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def generate_comments(ctx: dict, match_percent: int) -> dict:
    prompt = build_comment_prompt(ctx, match_percent)

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Groq API 오류: {e}")

    raw = response.choices[0].message.content
    try:
        return _parse_json(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"JSON 파싱 실패: {raw}")