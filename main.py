import os
import json
import re
import requests
import openai
from typing import List
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI 애플리케이션 생성
app = FastAPI()

### 📌 데이터 모델 정의 ###
class UserRequest(BaseModel):
    category: List[str]
    gender: str
    age_group: str
    values: List[str]
    favorite_app: str


### 📌 OpenAI 프롬프트 생성 함수 ###
def get_app_recommendation_prompt(user_request: UserRequest):
    return f"""
    사용자 정보:
    - 카테고리: {', '.join(user_request.category)}
    - 성별: {user_request.gender}
    - 연령대: {user_request.age_group}
    - 앱 추구 가치: {', '.join(user_request.values)}
    - 최애 앱: {user_request.favorite_app}

    위 정보를 바탕으로 한국 앱스토어의 앱을 5개 추천해주세요. JSON 형식으로 응답하세요.
    ```json
    [
        {{"app_name": "앱1", "app_store_url": "앱1의 앱스토어 URL", "app_icon_url": "앱1의 아이콘 URL", "strength": "앱1의 강점"}},
        {{"app_name": "앱2", "app_store_url": "앱2의 앱스토어 URL", "app_icon_url": "앱2의 아이콘 URL", "strength": "앱2의 강점"}},
        {{"app_name": "앱3", "app_store_url": "앱3의 앱스토어 URL", "app_icon_url": "앱3의 아이콘 URL", "strength": "앱3의 강점"}},
        {{"app_name": "앱4", "app_store_url": "앱4의 앱스토어 URL", "app_icon_url": "앱4의 아이콘 URL", "strength": "앱4의 강점"}},
        {{"app_name": "앱5", "app_store_url": "앱5의 앱스토어 URL", "app_icon_url": "앱5의 아이콘 URL", "strength": "앱5의 강점"}}
    ]
    ```
    """


### 📌 OpenAI를 활용한 앱 추천 기능 ###
async def get_app_recommendations_with_ai(user_request: UserRequest):
    prompt = get_app_recommendation_prompt(user_request)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )

        ai_output = response['choices'][0]['message']['content'].strip()
        print(ai_output)

        json_match = re.search(r"\[\s*\{.*?\}\s*\]", ai_output, re.DOTALL)
        if json_match:
            apps = json.loads(json_match.group())

            if isinstance(apps, list) and len(apps) == 5:
                corrected_apps = []

                for app in apps:
                    actual_app_data = fetch_itunes_app_data(app["app_name"])  # 앱스토어 데이터 조회
                    if actual_app_data:
                        corrected_apps.append({
                            "app_name": actual_app_data["app_name"],
                            "app_store_url": actual_app_data["app_store_url"],
                            "app_icon_url": actual_app_data["app_icon_url"],
                            "strength": app["strength"]  # AI 제공 강점 유지
                        })
                    else:
                        corrected_apps.append(app)  # 앱스토어에서 찾지 못한 경우 AI 데이터 유지

                return corrected_apps

            return {"error": "AI가 5개의 앱을 제공하지 않았습니다."}
        else:
            return {"error": "AI 응답에서 JSON 형식을 찾을 수 없습니다."}
    except Exception as e:
        return {"error": f"AI 응답 처리 중 오류 발생: {e}"}


### 📌 iTunes API를 활용한 앱스토어 데이터 조회 ###
def fetch_itunes_app_data(app_name, country="KR"):
    """
    iTunes Search API를 사용하여 앱 정보를 조회합니다.
    """
    url = "https://itunes.apple.com/search"
    params = {
        "term": app_name,
        "country": country,
        "media": "software",
        "limit": 1  # 가장 연관된 앱 1개만 가져옴
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            app_info = data["results"][0]
            return {
                "app_name": app_info.get("trackName"),
                "app_store_url": app_info.get("trackViewUrl"),
                "app_icon_url": app_info.get("artworkUrl512"),
                "app_id": app_info.get("trackId")
            }
    return None  # 검색 결과가 없을 경우


### 📌 앱 아이콘 URL 검증 및 최신 아이콘 가져오기 ###
def get_latest_app_icon(app_url: str) -> str:
    """
    앱스토어 URL에서 앱 ID를 추출하여 최신 아이콘 URL을 가져옵니다.
    """
    try:
        match = re.search(r"id(\d+)", app_url)
        if not match:
            return app_url  # 앱스토어 링크가 아니면 원래 URL 반환
        
        app_id = match.group(1)
        lookup_url = f"https://itunes.apple.com/lookup?id={app_id}"
        response = requests.get(lookup_url, timeout=5)
        data = response.json()

        if data.get("resultCount", 0) > 0:
            return data["results"][0].get("artworkUrl512", app_url)  # 최신 아이콘 URL 반환
    except Exception as e:
        print(f"iTunes API 오류: {e}")
    return app_url  # 실패 시 원래 URL 반환


### 📌 이미지 URL 검증 ###
def validate_image_url(image_url: str) -> str:
    """
    이미지 URL이 정상적으로 응답하는지 확인.
    만약 404가 발생하면 기본 아이콘 URL을 반환.
    """
    try:
        response = requests.head(image_url, allow_redirects=True, timeout=3)
        if response.status_code == 200:
            return image_url
    except requests.RequestException:
        pass
    return "https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"  # 기본 아이콘


### 📌 API 엔드포인트 정의 ###
@app.get("/")
async def root():
    return {"message": "앱 추천 서비스를 환영합니다!"}

@app.post("/recommend_apps/")
async def recommend_apps(request: UserRequest):
    return await get_app_recommendations_with_ai(request)
