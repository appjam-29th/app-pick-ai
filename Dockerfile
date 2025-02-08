# Python 3.9 기반 이미지 사용
FROM python:3.9

# 작업 디렉토리 생성
WORKDIR /app

# main.py, requirements.txt, .env 복사
COPY main.py /app/
COPY requirements.txt /app/
COPY .env /app/

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 실행 (host=0.0.0.0, 포트 8000)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
