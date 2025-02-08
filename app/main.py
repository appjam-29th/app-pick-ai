from fastapi import FastAPI
from app.api.routes import router

app = FastAPI()

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "앱 추천 서비스를 환영합니다!"}
