from fastapi import FastAPI
from match_ai.routers.match_router import router

app = FastAPI(title="Resume Match API")
app.include_router(router, prefix="/api")
