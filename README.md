## **프로젝트 실행 방법**

### **1. 깃허브 저장소 클론**
아래 명령어를 사용하여 프로젝트를 클론합니다.
```bash
git clone https://github.com/appjam-29th/app-pick-ai.git
```


### **2. Docker Desktop 설치 및 로그인**
1. [Docker 공식 사이트](https://www.docker.com/products/docker-desktop/)에서 Docker Desktop을 설치합니다.
2. 설치 후 터미널에서 Docker에 로그인합니다.
```bash
docker login
```

### 🛠 3. 도커 이미지 빌드
```bash
docker build -t fastapi-app .
```

### 🚀 4. 컨테이너 실행
```bash
docker run -d -p 8000:8000 fastapi-app
```

✅ 실행 후 `http://localhost:8000` 에 접속하면 FastAPI 응답이 확인됩니다.
