"""
PIEC 공고 추출 통합 API
"""

from dotenv import load_dotenv
from fastapi import FastAPI

from routers.extraction_router import router

load_dotenv()

app = FastAPI()
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)