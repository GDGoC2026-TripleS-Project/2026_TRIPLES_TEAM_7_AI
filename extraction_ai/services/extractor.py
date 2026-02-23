import re
import json
import os
from datetime import datetime

from openai import OpenAI

from extraction_ai.crawlers.wanted_crawler import crawl_wanted_job
from extraction_ai.crawlers.jobkorea_crawler import crawl_jobkorea_job
from extraction_ai.crawlers.linkareer_crawler import crawl_linkareer_job


# ── 공통 출력 스키마 ───────────────────────────────────────────────

OUTPUT_SCHEMA = """
────────────────────────
[출력 스키마 — 절대 변경 금지]
────────────────────────
{
  "jobTitle": string,
  "companyName": string,
  "employmentType": "FULL_TIME" | "CONTRACT" | "INTERN",
  "roleText": string,
  "necessaryStack": string[],
  "preferStack": string[],
  "salaryText": string,
  "locationText": string,
  "experienceLevel": string,
  "workDay": string,
  "deadlineAt": "YYYY-MM-DD"
}

타입 규칙:
- employmentType: 반드시 FULL_TIME / CONTRACT / INTERN 셋 중 하나 (단일값)
- roleText: 담당업무를 하나의 문자열로 요약 (배열 금지)
- experienceLevel: 경력 조건을 하나의 문자열로 (배열 금지)
- necessaryStack / preferStack: 기술명 배열
- 값 없을 경우: 문자열 → ""  /  배열 → []
"""

# ── 사이트별 프롬프트 ──────────────────────────────────────────────

PROMPT_JOBKOREA = """
너는 JobKorea(잡코리아) 채용공고 전문 데이터 추출 모델이다.

입력으로 주어지는 JSON은 잡코리아 공고 페이지에서 크롤링되었으며,
다음과 같은 특징을 가진다:
- "[잡코리아 지정 영역 데이터]" : 상단 메타 요약 영역
- "[공고 이미지 추출 상세내용]" : 실제 공고 본문(OCR 포함)
- 동일 정보가 여러 번 반복될 수 있음
- OCR 오류, 깨진 문자, 중복 문단이 포함될 수 있음

────────────────────────
[핵심 규칙]
────────────────────────
1. 출력은 반드시 JSON만 작성한다. (설명 문장, 주석 절대 금지)
2. 모든 필드는 반드시 포함한다.
3. OCR 오류는 문맥 기반으로 자연스럽게 교정한다. 예: ReactNative → React Native
4. 기술 스택은 중복 제거 후 대표 명칭으로 통일한다.
5. 괄호 포함 기술은 분리한다. 예: "Spring Framework(Spring Boot)" → ["Spring Framework", "Spring Boot"]

────────────────────────
[JobKorea 해석 규칙]
────────────────────────
- "[잡코리아 지정 영역 데이터]"는 메타 요약 정보 → roleText 추출 시 사용 금지
- "[공고 이미지 추출 상세내용]" 이하를 실제 채용공고 본문으로 간주하고 최우선 분석
- roleText에 포함하지 않는 항목: 모집분야/모집인원, 급여/근무시간/근무지역, 접수방법/마감안내, 회사소개/복리후생

────────────────────────
[필드별 추출 기준]
────────────────────────
▶ jobTitle: 
- 직무명만 추출한다 (예: "Java개발자", "백엔드개발자", "데이터엔지니어")
- 경력 조건 제거: "[경력3년]", "(신입)", "경력 5년 이상" 등
- 채용 관련 문구 제거: "채용", "모집", "구인" 등
- AI 도구/기술 스택 나열 제거: "Claude, Cursor 등 AI 도구 능숙자" 등
- 슬래시(/) 이후 부연 설명 제거
- 결과는 핵심 직무명 하나만 출력
▶ companyName: 입력 JSON의 company_name 값 그대로
▶ employmentType: "고용형태" 기준 → FULL_TIME / CONTRACT / INTERN 중 하나
▶ roleText: "담당업무"/"주요업무" 문단 내용을 하나의 문자열로 1~2문장으로 자연스럽게 요약 
- 마침표(.)로 끝내지 말 것. 예) "서버 API 개발 및 유지보수, 결제 시스템 연동"
▶ necessaryStack: "지원자격"/"필수요건"/"자격요건" 문단에서 기술명 뽑거나 자연스럽게 요약 (최대 6개, 글자 수 10자 내외)
▶ preferStack: 우대사항에서 기술명 또는 짧은 역량 표현으로 추출 (최대 6개)
  - 기술명: "Java", "AWS" 등 그대로
  - 역량/경험: "클린코드 구조 이해", "팀 단위 개발 경험" 처럼 10자 내외로 자연스럽게 요약
  - "~하신 분", "~을 갖추신 분" 같은 문장 형태는 제거
▶ experienceLevel: "지원자격" 본문의 경력 조건을 하나의 문자열로
▶ salaryText: 급여 문구 요약
▶ workDay: 근무 요일 요약 ("주 5일" 등만 요약)
▶ locationText: 근무지역 전체 주소 그대로 사용
▶ deadlineAt: "마감일" 기준. 예: "~2/26(목)" → "2026-02-26"
""" + OUTPUT_SCHEMA

PROMPT_WANTED = """
너는 Wanted(원티드) 채용공고 전문 데이터 추출 모델이다.

입력 JSON은 원티드 채용공고에서 크롤링된 데이터이며,
"role_text" 필드에 전체 공고 원문이 포함되어 있다.

────────────────────────
[핵심 규칙]
────────────────────────
1. 출력은 반드시 JSON만 작성한다. (설명 금지)
2. 모든 필드는 반드시 포함한다.
3. OCR 영역은 무시한다.
4. 기술 스택은 중복 제거 후 대표 명칭으로 통일한다.
5. 괄호 포함 기술은 분리한다. 예: "Spring Framework(Spring Boot)" → ["Spring Framework", "Spring Boot"]

────────────────────────
[Wanted 해석 규칙]
────────────────────────
- "[공고 원본 텍스트]" 이하를 실제 공고로 간주
- "[이미지 추출 텍스트 (OCR)]" 영역은 무시
- "포지션 상세"는 회사 소개 → roleText에 포함하지 않는다
- "주요업무" 문단만 roleText로 사용
- "자격요건" → necessaryStack
- "우대사항" → preferStack
- "혜택 및 복지"에서 고용형태 및 근무일 추출

────────────────────────
[필드별 추출 기준]
────────────────────────
▶ jobTitle: 
- 직무명만 추출한다 (예: "Java개발자", "백엔드개발자", "데이터엔지니어")
- 경력 조건 제거: "[경력3년]", "(신입)", "경력 5년 이상" 등
- 채용 관련 문구 제거: "채용", "모집", "구인" 등
- AI 도구/기술 스택 나열 제거: "Claude, Cursor 등 AI 도구 능숙자" 등
- 슬래시(/) 이후 부연 설명 제거
- 결과는 핵심 직무명 하나만 출력
▶ companyName: 입력 JSON company_name 그대로
▶ employmentType: FULL_TIME / CONTRACT / INTERN 중 하나
▶ roleText: "주요업무" 문단 내용을 하나의 문자열로 1~2문장으로 자연스럽게 요약
- 마침표(.)로 끝내지 말 것. 예) "서버 API 개발 및 유지보수, 결제 시스템 연동"
▶ necessaryStack: 자격요건에서 기술 스택 뽑거나 자연스럽게 요약 (최대 6개, 글자 수 10자 내외)
▶ preferStack: 우대사항에서 기술명 또는 짧은 역량 표현으로 추출 (최대 6개)
  - 기술명: "Java", "AWS" 등 그대로
  - 역량/경험: "클린코드 구조 이해", "팀 단위 개발 경험" 처럼 10자 내외로 자연스럽게 요약
  - "~하신 분", "~을 갖추신 분" 같은 문장 형태는 제거
▶ experienceLevel: 자격요건의 경력 기준을 하나의 문자열로. 예: "경력 2-6년"
▶ salaryText: 명시 없으면 ""
▶ workDay: "주 5일" 등만 요약
▶ locationText: 근무지역 전체 주소 그대로
▶ deadlineAt: YYYY-MM-DD
""" + OUTPUT_SCHEMA

PROMPT_LINKAREER = """
너는 Linkareer(링커리어) 채용공고 전문 데이터 정제 모델이다.

입력 JSON의 "role_text"에는
[공고 요약], [상세 내용], [이미지 텍스트]가 모두 포함되어 있다.
- 동일 정보가 여러 번 반복될 수 있음
- OCR 오류, 깨진 문자, 중복 문단이 포함될 수 있음

────────────────────────
[핵심 규칙]
────────────────────────
1. 출력은 반드시 JSON만 작성한다. (설명 금지)
2. 모든 필드는 반드시 포함한다.
3. OCR 오류는 문맥 기반으로 자연스럽게 교정한다. 예: ReactNative → React Native
4. 기술 스택은 중복 제거 후 대표 명칭으로 통일한다.
5. 괄호 포함 기술은 분리한다. 예: "Spring Framework(Spring Boot)" → ["Spring Framework", "Spring Boot"]

────────────────────────
[Linkareer 해석 규칙]
────────────────────────
- "[공고 요약]" 영역은 메타 정보 (D-숫자 마감 정보는 여기서 추출)
- "[상세 내용]" 영역을 실제 채용공고 본문으로 간주
- "담당업무" 문단만 roleText로 사용
- "자격요건" → necessaryStack
- "우대사항" → preferStack
- "채용형태" 또는 상세 제목에서 고용형태 추출

────────────────────────
[필드별 추출 기준]
────────────────────────
▶ jobTitle: 
- 직무명만 추출한다 (예: "Java개발자", "백엔드개발자", "데이터엔지니어")
- 경력 조건 제거: "[경력3년]", "(신입)", "경력 5년 이상" 등
- 채용 관련 문구 제거: "채용", "모집", "구인" 등
- AI 도구/기술 스택 나열 제거: "Claude, Cursor 등 AI 도구 능숙자" 등
- 슬래시(/) 이후 부연 설명 제거
- 결과는 핵심 직무명 하나만 출력
▶ companyName: 입력 JSON company_name 그대로
▶ employmentType: FULL_TIME / CONTRACT / INTERN 중 하나
▶ roleText: "담당업무" 항목을 하나의 문자열로 1~2문장으로 자연스럽게 요약
- 마침표(.)로 끝내지 말 것. 예) "서버 API 개발 및 유지보수, 결제 시스템 연동"
▶ necessaryStack: 자격요건에서 기술 키워드 뽑거나 자연스럽게 요약 (최대 6개, 글자 수 10자 내외)
▶ preferStack: 우대사항에서 기술명 또는 짧은 역량 표현으로 추출 (최대 6개)
  - 기술명: "Java", "AWS" 등 그대로
  - 역량/경험: "클린코드 구조 이해", "팀 단위 개발 경험" 처럼 10자 내외로 자연스럽게 요약
  - "~하신 분", "~을 갖추신 분" 같은 문장 형태는 제거
▶ experienceLevel: 채용형태 + 자격요건 기반을 하나의 문자열로. 예: "신입"
▶ salaryText: 급여조건 문구 그대로, 없으면 ""
▶ workDay: 명시 없으면 ""
▶ locationText: 상세 내용의 근무지역 전체 주소
▶ deadlineAt: [공고 요약]의 날짜를 YYYY-MM-DD로 변환. 없으면 ""
""" + OUTPUT_SCHEMA

SITE_PROMPTS = {
    "wanted": PROMPT_WANTED,
    "jobkorea": PROMPT_JOBKOREA,
    "linkareer": PROMPT_LINKAREER,
}


def detect_site(url: str) -> str:
    if "wanted.co.kr" in url:
        return "wanted"
    elif "jobkorea.co.kr" in url:
        return "jobkorea"
    elif "linkareer.com" in url:
        return "linkareer"
    else:
        raise ValueError(f"지원하지 않는 사이트: {url}")


def crawl(url: str, site: str):
    crawlers = {
        "wanted": crawl_wanted_job,
        "jobkorea": crawl_jobkorea_job,
        "linkareer": crawl_linkareer_job,
    }
    return crawlers[site](url)


def extract_with_ai(posting, site: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    today = datetime.now().strftime("%Y년 %m월 %d일")

    input_data = {
        "job_title": posting.job_title,
        "company_name": posting.company_name,
        "original_url": posting.original_url,
        "role_text": posting.role_text,
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SITE_PROMPTS[site]},
            {"role": "user", "content": f"오늘 날짜: {today}\n\n{json.dumps(input_data, ensure_ascii=False)}"}
        ]
    )

    text = response.choices[0].message.content.strip()
    text = re.sub(r'^```json\s*|\s*```$', '', text)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("AI 응답에서 JSON을 찾을 수 없음")

    result = json.loads(match.group(0))
    result["original_url"] = posting.original_url

    if result.get("deadlineAt"):
        try:
            dt = datetime.strptime(result["deadlineAt"], "%Y-%m-%d")
            result["deadlineAt"] = dt.strftime("%Y-%m-%dT23:59:59.000Z")
        except:
            pass

    return result
