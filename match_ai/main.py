from fastapi import FastAPI
from routers.match_router import router

app = FastAPI(title="Resume Match API")
app.include_router(router, prefix="/api")
