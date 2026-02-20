# PIEC AI 파이프라인 구축 가이드

## 📋 프로젝트 개요

채용공고 URL을 입력받아 핵심 정보를 추출하는 파인튜닝 AI 모델 개발

### 추출 대상 필드 (ERD `AI 요약 카드` 테이블 기준)

| 필드명 | 설명 | 예시 |
|--------|------|------|
| `jobTitle` | 직무명 | Backend Developer (Java) |
| `companyName` | 회사명 | 네이버랩스 |
| `employmentType` | 고용형태 | 인턴/계약직, 정규직 |
| `roleText` | 업무 설명 요약 | 대규모 트래픽 API 설계 및 운영, Spring 기반 서버 개발 및 유지보수 |
| `necessaryStack` | 필수 스킬 | Java, Spring, RDB 경험 |
| `preferStack` | 우대 스킬 | Java, Spring, RDB 경험 |
| `experienceLevel` | 경력 요구사항 | 신입, 경력 무관 |
| `salaryText` | 연봉 | 2000만원 • 협상 가능 |
| `workDay` | 근무일 | 주 5일 (월,화,수,목,금) |
| `locationText` | 주소 | 서울특별시 성동구 성수이로 24길 32, 7층 |
| `deadlineAt` | 마감일 | D-3 |

---

## 🗂️ 디렉토리 구조

```
piec_ai_pipeline/
├── README.md                    # 이 문서
├── requirements.txt             # 의존성
├── 1_crawlers/                  # 크롤러
│   ├── base_crawler.py          # 베이스 크롤러 클래스
│   ├── wanted_crawler.py        # 원티드 크롤러
│   ├── jobkorea_crawler.py      # 잡코리아 크롤러
│   └── linkareer_crawler.py     # 링커리어 크롤러
├── 2_data_processing/           # 데이터 전처리
│   ├── data_format.py           # 학습 데이터 포맷 정의
│   ├── labeling_tool.py         # 라벨링 도구
│   └── data_validator.py        # 데이터 검증
├── 3_finetuning/                # 파인튜닝
│   ├── prepare_dataset.py       # 데이터셋 준비
│   ├── finetune_unsloth.py      # Unsloth 파인튜닝
│   └── inference.py             # 추론 코드
├── data/                        # 데이터 저장
│   ├── raw/                     # 원본 크롤링 데이터
│   ├── labeled/                 # 라벨링된 데이터
│   └── processed/               # 전처리된 학습 데이터
└── models/                      # 학습된 모델 저장
```

---

## 🚀 진행 순서

### Phase 1: 데이터 수집 (1~2주)
1. 크롤러 개발 및 테스트
2. IT 개발자 채용공고 100~500개 수집
3. 수집 데이터 검증

### Phase 2: 데이터 라벨링 (1주)
1. 라벨링 가이드라인 작성
2. 수동 라벨링 (최소 100개)
3. 데이터 품질 검증

### Phase 3: 파인튜닝 (1주)
1. 베이스 모델 선택
2. 학습 데이터 포맷팅
3. 파인튜닝 실행
4. 평가 및 개선

### Phase 4: 통합 및 배포
1. 백엔드 API 연동
2. 추론 최적화
3. 테스트 및 배포
