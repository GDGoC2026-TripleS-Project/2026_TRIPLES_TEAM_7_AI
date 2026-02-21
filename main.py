from fastapi import FastAPI
from extraction_ai.routers.extraction_router import router as extraction_router
from match_ai.routers.match_router import router as match_router
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

# 허용할 Origin 목록 (프론트엔드 주소)
origins = [
    "http://localhost:3000", 
    "http://localhost:8080",   # 로컬 개발 환경
    "http://http://52.78.20.212",   # 실제 서비스 도메인
    "https://http://52.78.20.212",
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"] 대신 아래 설정을 사용하세요
    allow_origin_regex="https?://.*",  # http 또는 https로 시작하는 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extraction_router, prefix="/fastapi")
app.include_router(match_router, prefix="/fastapi")

@app.get("/fastapi")
def health_check():
    return {"models": ["extraction", "match"]}