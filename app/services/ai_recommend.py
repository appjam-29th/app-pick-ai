import openai
import os
import json
import re
from utils.fetch_utils import get_latest_app_icon, validate_image_url
from utils.prompt_templates import get_app_recommendation_prompt
from utils.fetch_itunes_app_data import fetch_itunes_app_data  # 앱스토어 데이터 조회 함수 추가

openai.api_key = os.getenv("OPENAI_API_KEY")

async def get_app_recommendations_with_ai(user_request):
    prompt = get_app_recommendation_prompt(user_request)  # 프롬프트 가져오기

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
                    actual_app_data = fetch_itunes_app_data(app["앱 이름"])  # 실제 앱스토어 데이터 조회
                    if actual_app_data:
                        corrected_apps.append({
                            "app_name": actual_app_data["앱 이름"],
                            "app_url": actual_app_data["앱 URL"],
                            "app_store_url": actual_app_data["앱 아이콘 URL"],
                            "strength": app["강점"]  # AI가 제공한 강점 그대로 유지
                        })
                    else:
                        corrected_apps.append(app)  # 앱스토어에서 찾지 못한 경우 AI 데이터 유지

                return corrected_apps

            return {"error": "AI가 5개의 앱을 제공하지 않았습니다."}
        else:
            return {"error": "AI 응답에서 JSON 형식을 찾을 수 없습니다."}
    except Exception as e:
        return {"error": f"AI 응답 처리 중 오류 발생: {e}"}