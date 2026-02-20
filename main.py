from fastapi import FastAPI
from extraction_ai.routers.extraction_router import router as extraction_router
from match_ai.routers.match_router import router as match_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.include_router(extraction_router, prefix="/fastapi/extract")
app.include_router(match_router, prefix="/fastapi/match/api")

@app.get("/fastapi")
def health_check():
    return {"models": ["extraction", "match"]}