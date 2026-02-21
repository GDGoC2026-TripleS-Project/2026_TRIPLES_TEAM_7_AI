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
    allow_origins=origins,       # 모든 곳을 허용하려면 ["*"]
    allow_credentials=True,
    allow_methods=["*"],         # GET, POST, PUT, DELETE 등 모두 허용
    allow_headers=["*"],         # 모든 헤더 허용
)

app.include_router(extraction_router, prefix="/fastapi")
app.include_router(match_router, prefix="/fastapi")

@app.get("/fastapi")
def health_check():
    return {"models": ["extraction", "match"]}