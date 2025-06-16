from fastapi import FastAPI
from pydantic import BaseModel, RootModel
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.output_parsers import PydanticOutputParser

from langchain_openai import ChatOpenAI
from starlette.concurrency import run_in_threadpool
import httpx
import os

# 환경 변수 로딩
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# ============================
# 데이터 모델 정의
# ============================

class UserRequest(BaseModel):
    category: list[str]
    gender: str
    age_group: str
    values: list[str]
    favorite_app: str

# LangChain 출력용 모델
class AppRecommendResponse(BaseModel):
    app_name: str
    app_store_url: str
    app_icon_url: str
    strength: str

class AppListResponse(RootModel[list[AppRecommendResponse]]):
    pass

# ============================
# LangChain 구성
# ============================

parser = PydanticOutputParser(pydantic_object=AppListResponse)

prompt = PromptTemplate(
    template="""
사용자 정보:
- 카테고리: {category}
- 성별: {gender}
- 연령대: {age_group}
- 앱 추구 가치: {values}
- 최애 앱: {favorite_app}

위 정보를 바탕으로 한국 앱스토어에서 인기 있는 앱 5개를 추천해 주세요.
아래와 같은 JSON 형식으로 응답해 주세요:

{format_instructions}
""",
    input_variables=["category", "gender", "age_group", "values", "favorite_app"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

llm = ChatOpenAI(model="gpt-4o", api_key=api_key, temperature=0)

# Runnable 체인
chain = prompt | llm | parser

# ============================
# iTunes 앱 정보 API 호출
# ============================

async def fetch_itunes_app_data(app_name: str, country="KR"):
    url = "https://itunes.apple.com/search"
    params = {
        "term": app_name,
        "country": country,
        "media": "software",
        "limit": 1
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                app_info = data["results"][0]
                return {
                    "app_name": app_info.get("trackName"),
                    "app_store_url": app_info.get("trackViewUrl"),
                    "app_icon_url": app_info.get("artworkUrl512"),
                }
    return None

# ============================
# FastAPI 엔드포인트 비즈니스 로직 함수화
# ============================

def process_app_recommendation(request: UserRequest):
    input_data = {
        "category": ", ".join(request.category),
        "gender": request.gender,
        "age_group": request.age_group,
        "values": ", ".join(request.values),
        "favorite_app": request.favorite_app
    }
    # LangChain Runnable 실행은 sync -> thread pool에서 실행
    try:
        result: AppListResponse = chain.invoke(input_data)
    except Exception as e:
        raise RuntimeError(f"AI 호출 중 오류 발생: {str(e)}")

    # iTunes 데이터 보강
    import asyncio
    async def enhance():
        enhanced_apps = []
        for app in result.root:
            itunes_data = await fetch_itunes_app_data(app.app_name)
            if itunes_data:
                enhanced_apps.append({
                    "app_name": itunes_data["app_name"],
                    "app_store_url": itunes_data["app_store_url"],
                    "app_icon_url": itunes_data["app_icon_url"],
                    "strength": app.strength
                })
            else:
                enhanced_apps.append(app.dict())
        return enhanced_apps
    return asyncio.run(enhance())

# ============================
# FastAPI 엔드포인트
# ============================

@app.post("/recommend_apps/")
async def recommend_apps(request: UserRequest):
    try:
        # 비즈니스 로직 함수 호출 (비동기 보강)
        import asyncio
        loop = asyncio.get_event_loop()
        enhanced_apps = await loop.run_in_executor(None, process_app_recommendation, request)
        return enhanced_apps
    except Exception as e:
        return {"error": str(e)}
