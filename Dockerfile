# Python 3.9 기반 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 생성
WORKDIR /app

# Poetry 설치
RUN pip install --no-cache-dir poetry

# pyproject.toml과 poetry.lock 복사
COPY pyproject.toml poetry.lock /app/

# 의존성 설치 (가상환경 비활성화)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# 애플리케이션 파일 복사
COPY main.py /app/
COPY .env /app/


# FastAPI 실행 (host=0.0.0.0, 포트 8000)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
