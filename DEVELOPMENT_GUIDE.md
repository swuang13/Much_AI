# Much 개발 환경 설정 가이드 🚀

개발팀원들이 개인 환경에서 Much 프로젝트를 설정하고 작업할 수 있도록 도와주는 가이드입니다.

## 📋 **사전 요구사항**

### 필수 소프트웨어
- **Python 3.8 이상** (3.9, 3.10, 3.11, 3.12 권장)
- **Git** (버전 관리)
- **코드 에디터** (VS Code, PyCharm, Sublime Text 등)

### 권장 소프트웨어
- **VS Code** + Python 확장
- **Postman** (API 테스트)
- **DBeaver** (데이터베이스 관리)

## 🚀 **1단계: 프로젝트 클론 및 환경 설정**

### 1.1 프로젝트 클론
```bash
# 프로젝트 저장소 클론
git clone [repository-url]
cd much

# 또는 기존 프로젝트 폴더에서 시작
cd much
```

### 1.2 Python 가상환경 생성
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 1.3 의존성 설치
```bash
# pip 업그레이드 (권장)
pip install --upgrade pip

# 프로젝트 의존성 설치
pip install -r requirements.txt
```

## ⚙️ **2단계: 환경 변수 설정**

### 2.1 .env 파일 생성
프로젝트 루트에 `.env` 파일을 생성하세요:

```bash
# .env 파일 생성
touch .env
```

### 2.2 .env 파일 내용
```env
# Django 설정
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI 설정 (Hugging Face Inference API)
HF_API_KEY=your-hf-api-token
# 또는
HUGGINGFACEHUB_API_TOKEN=your-hf-api-token
AI_MODEL_NAME=meta-llama/Meta-Llama-3.1-8B-Instruct

# 데이터베이스 설정 (개발용)
DATABASE_URL=sqlite:///db.sqlite3

# 로깅 설정
LOG_LEVEL=DEBUG

# 개발자 정보
DEVELOPER_NAME=your-name
DEVELOPER_EMAIL=your-email@example.com
```

### 2.3 .gitignore 확인
`.gitignore` 파일에 다음 항목들이 포함되어 있는지 확인:

```gitignore
# 가상환경
venv/
env/
ENV/

# 환경 변수
.env
.env.local
.env.*.local

# 데이터베이스
*.sqlite3
*.db

# Python
__pycache__/
*.py[cod]
*$py.class

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

## 🗄️ **3단계: 데이터베이스 설정**

### 3.1 마이그레이션 실행
```bash
# 가상환경이 활성화되어 있는지 확인
which python  # venv/bin/python이 표시되어야 함

# 마이그레이션 생성
python manage.py makemigrations

# 마이그레이션 적용
python manage.py migrate
```

### 3.2 슈퍼유저 생성
```bash
# 관리자 계정 생성
python manage.py createsuperuser

# 사용자명, 이메일, 비밀번호 입력
```

### 3.3 초기 데이터 생성 (선택사항)
```bash
# 개발용 샘플 데이터 생성
python manage.py loaddata initial_data.json
```

## 🔧 **4단계: 개발 서버 실행**

### 4.1 기본 서버 실행
```bash
# 개발 서버 시작
python manage.py runserver

# 특정 포트로 실행
python manage.py runserver 8001

# 모든 IP에서 접근 허용
python manage.py runserver 0.0.0.0:8000
```

### 4.2 서버 접속 확인
- **메인 페이지**: http://localhost:8000/
- **Admin 관리**: http://localhost:8000/admin/
- **자산진단**: http://localhost:8000/
- **AI플랜**: http://localhost:8000/plan/
- **성장리워드**: http://localhost:8000/reward/

## 👥 **5단계: 팀원별 작업 환경 설정**

### 5.1 담당자 1: 자산진단 (Asset App)
```bash
# Asset 앱 관련 작업
cd much/asset

# 템플릿 파일 위치
templates/asset/

# 정적 파일 위치
static/asset/

# 주요 작업 파일
- models.py: 진단 모델 설계
- views.py: 진단 로직 구현
- admin.py: 관리자 인터페이스
- urls.py: URL 라우팅
```

**작업할 페이지들:**
- 진단 질문 입력 폼
- 진단 결과 표시
- 진단 기록 목록
- 점수 계산 알고리즘

### 5.2 담당자 2: AI플랜 (Plan App)
```bash
# Plan 앱 관련 작업
cd much/plan

# 템플릿 파일 위치
templates/plan/

# 정적 파일 위치
static/plan/

# 주요 작업 파일
- models.py: 플랜 및 소득예측 모델
- views.py: AI 예측 로직
- admin.py: 관리자 인터페이스
- urls.py: URL 라우팅
```

**작업할 페이지들:**
- 소득 데이터 입력
- 플랜 생성 설정
- 플랜 결과 표시
- 월별 계획 상세

### 5.3 담당자 3: 성장리워드 (Reward App)
```bash
# Reward 앱 관련 작업
cd much/reward

# 템플릿 파일 위치
templates/reward/

# 정적 파일 위치
static/reward/

# 주요 작업 파일
- models.py: 리워드 시스템 모델
- views.py: 게이미피케이션 로직
- admin.py: 관리자 인터페이스
- urls.py: URL 라우팅
```

**작업할 페이지들:**
- 퀴즈 목록 및 풀이
- 사용자 대시보드
- 업적 및 혜택
- 리더보드

## 🛠️ **6단계: 개발 도구 설정**

### 6.1 VS Code 설정 (권장)
`.vscode/settings.json` 파일 생성:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### 6.2 코드 품질 도구 설치
```bash
# 코드 포맷팅
pip install black

# 린팅
pip install flake8

# Import 정렬
pip install isort

# 타입 체크
pip install mypy
```

### 6.3 Git Hooks 설정 (선택사항)
```bash
# pre-commit 설치
pip install pre-commit

# pre-commit 설정
pre-commit install
```

## 🧪 **7단계: 테스트 환경 설정**

### 7.1 테스트 도구 설치
```bash
# 테스트 프레임워크
pip install pytest
pip install pytest-django

# 테스트 커버리지
pip install pytest-cov

# 테스트 데이터 생성
pip install factory-boy
```

### 7.2 테스트 실행
```bash
# 전체 테스트 실행
python manage.py test

# 특정 앱 테스트
python manage.py test asset
python manage.py test plan
python manage.py test reward

# pytest 사용
pytest
pytest --cov=.
```

## 📱 **8단계: 프론트엔드 개발**

### 8.1 CSS/JS 파일 위치
```bash
# CSS 파일
static/css/style.css

# JavaScript 파일
static/js/main.js

# 이미지 파일
static/images/
```

### 8.2 템플릿 구조
```bash
# 기본 레이아웃
templates/base.html

# 앱별 템플릿
templates/asset/
templates/plan/
templates/reward/
```

### 8.3 정적 파일 수집
```bash
# 개발 환경에서 정적 파일 수집
python manage.py collectstatic --settings=financial_academy.settings

# 프로덕션 환경
python manage.py collectstatic --noinput
```

## 🔍 **9단계: 디버깅 및 로깅**

### 9.1 Django Debug Toolbar 설치
```bash
pip install django-debug-toolbar
```

### 9.2 로깅 설정
`settings.py`에 로깅 설정 추가:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
```

## 🚨 **10단계: 문제 해결**

### 10.1 일반적인 오류들

#### 가상환경 문제
```bash
# 가상환경이 활성화되지 않은 경우
source venv/bin/activate

# Python 경로 확인
which python
which python3

# pip 경로 확인
which pip
```

#### 의존성 문제
```bash
# requirements.txt 재설치
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# 가상환경 재생성
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 데이터베이스 문제
```bash
# 마이그레이션 초기화
rm -rf */migrations/0*.py
python manage.py makemigrations
python manage.py migrate

# 데이터베이스 재생성
rm db.sqlite3
python manage.py migrate
```

#### 포트 충돌 문제
```bash
# 다른 포트 사용
python manage.py runserver 8001

# 포트 사용 중인 프로세스 확인
lsof -i :8000
```

### 10.2 디버깅 팁
```python
# views.py에서 디버깅
import pdb; pdb.set_trace()

# 또는
breakpoint()

# 로그 출력
import logging
logger = logging.getLogger(__name__)
logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.error("오류 메시지")
```

## 📚 **11단계: 유용한 명령어들**

### 11.1 Django 관리 명령어
```bash
# 서버 실행
python manage.py runserver

# 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 정적 파일 수집
python manage.py collectstatic

# 데이터베이스 백업
python manage.py dumpdata > backup.json

# 데이터베이스 복원
python manage.py loaddata backup.json
```

### 11.2 개발 도구 명령어
```bash
# 코드 포맷팅
black .
isort .

# 린팅
flake8 .

# 테스트
pytest
python manage.py test

# 의존성 확인
pip list
pip freeze > requirements.txt
```

## 📞 **12단계: 팀 협업**

### 12.1 Git 워크플로우
```bash
# 새로운 기능 브랜치 생성
git checkout -b feature/asset-diagnosis

# 변경사항 커밋
git add .
git commit -m "Add asset diagnosis form"

# 브랜치 푸시
git push origin feature/asset-diagnosis

# Pull Request 생성 (GitHub/GitLab)
```

### 12.2 코드 리뷰 체크리스트
- [ ] 코드가 요구사항을 만족하는가?
- [ ] 에러 처리가 적절한가?
- [ ] 코드 스타일이 일관적인가?
- [ ] 테스트가 작성되었는가?
- [ ] 문서가 업데이트되었는가?

## 🎯 **13단계: 개발 완료 후**

### 13.1 최종 테스트
```bash
# 전체 테스트 실행
python manage.py test

# 정적 파일 수집
python manage.py collectstatic

# 서버 실행 테스트
python manage.py runserver
```

### 13.2 코드 정리
```bash
# 코드 포맷팅
black .
isort .

# 린팅 체크
flake8 .

# 불필요한 파일 정리
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
```

### 13.3 커밋 및 푸시
```bash
git add .
git commit -m "Complete [feature-name] implementation"
git push origin main
```

## 📋 **체크리스트**

### 초기 설정
- [ ] Python 3.8+ 설치
- [ ] Git 설치
- [ ] 프로젝트 클론
- [ ] 가상환경 생성 및 활성화
- [ ] 의존성 설치
- [ ] 환경 변수 설정
- [ ] 데이터베이스 마이그레이션
- [ ] 슈퍼유저 생성
- [ ] 개발 서버 실행

### 개발 환경
- [ ] 코드 에디터 설정
- [ ] 코드 품질 도구 설치
- [ ] Git 설정
- [ ] 테스트 환경 구성

### 작업 진행
- [ ] 담당 앱 파악
- [ ] 모델 설계
- [ ] 뷰 구현
- [ ] 템플릿 작성
- [ ] 테스트 작성
- [ ] 코드 리뷰

---

**Happy Coding! 🚀**

문제가 발생하면 팀원들과 상의하거나 이 가이드를 참고하세요.
