# Much 🏦

AI가 코칭하는 스마트 자산 관리 서비스, Much입니다.

**Much(머치)**는 청년층 및 프리랜서를 위한, 소득 변동성에 최적화된 AI 자산관리 서비스입니다. Much는 Money(자산)와 Coach(코칭)의 결합어로, 고객의 자산이 보다 이상적으로 사용될 수 있도록 AI가 코칭하고, 그 결과 더 많은(Much) 금융 혜택을 얻을 수 있도록 지원하는 서비스 철학을 담고 있습니다.

## 🎯 프로젝트 개요

Much는 고객의 자산 관리 역량을 진단하고, AI 기반 소득 예측을 통해 맞춤형 자산 관리 플랜을 제공하며, 게이미피케이션을 통한 성장 리워드를 제공하는 웹 애플리케이션입니다.

## ✨ 주요 기능

### 1. 자산 관리 역량 진단 (`/asset`)
- 현재 자산 관리 역량을 종합적으로 진단
- 4개 영역별 세부 점수 제공 (금융 리터러시, 위험 관리, 투자 지식, 부채 관리)
- 개인별 맞춤 피드백 및 권장사항 제공

### 2. AI 기반 자산 관리 플랜 (`/plan`) 🤖
- **Llama 3.1 8B 모델**: Hugging Face를 통한 최신 AI 모델 활용
- **프리랜서 특화 소득 예측**: 과거 12개월 데이터 기반 정교한 소득 예측
- **동적 플랜 조정**: AI가 실시간으로 변동성을 분석하여 플랜 자동 조정
- **계절성 분석**: 프리랜서 소득의 계절적 패턴을 고려한 예측
- **위험 요소 식별**: AI가 소득 변동성과 위험 요소를 자동으로 분석
- **맞춤형 권장사항**: 개인별 상황에 맞는 구체적인 개선 방안 제시
- **신용등급 관리**: 현재 신용등급을 고려한 맞춤형 개선 계획
- **월별 세부 계획**: 12개월 단위의 구체적인 지출/저축/투자 계획
- **실시간 API**: AJAX를 통한 실시간 소득 예측 및 플랜 미리보기

### 3. 성장 리워드 시스템 (`/reward`)
- **게이미피케이션**: 레벨업, 포인트, 업적 시스템
- **금융 리터러시 퀴즈**: 카테고리별 난이도별 퀴즈 제공
- **금융사 제휴 혜택**: 대출 금리 인하, 카드 추가 혜택 등
- **리더보드**: 사용자 간 경쟁 요소

## 🏗️ 기술 스택

- **Backend**: Django 5.2.5
- **Database**: SQLite (개발), PostgreSQL/MySQL (운영)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5.3.0
- **Icons**: Font Awesome 6.4.0
- **Language**: Python 3.8+
- **AI**: Llama 3.1 8B 모델 (Hugging Face), 소득 예측 및 자산 관리 코칭 시스템
- **API**: Hugging Face Inference API
- **Charts**: Chart.js (데이터 시각화)

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 설정
```bash
# 마이그레이션 실행
python manage.py makemigrations
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 3. 개발 서버 실행
```bash
python manage.py runserver
```

### 4. 브라우저에서 접속
```
http://localhost:8000
```

## 📁 프로젝트 구조

```
Much/
├── financial_academy/          # 메인 프로젝트 설정
│   ├── settings.py            # 프로젝트 설정
│   ├── urls.py                # 메인 URL 설정
│   └── wsgi.py                # WSGI 설정
├── asset/                      # 자산 관리 역량 진단 앱
│   ├── models.py              # 진단 관련 모델
│   ├── views.py               # 진단 관련 뷰
│   └── urls.py                # 진단 URL 설정
├── plan/                       # 자산 관리 플랜 생성 앱
│   ├── models.py              # 플랜 및 소득예측 모델
│   ├── views.py               # 플랜 생성 뷰
│   └── urls.py                # 플랜 URL 설정
├── reward/                     # 성장 리워드 앱
│   ├── models.py              # 리워드 시스템 모델
│   ├── views.py               # 리워드 관련 뷰
│   └── urls.py                # 리워드 URL 설정
├── templates/                  # HTML 템플릿
│   ├── base.html              # 기본 레이아웃
│   ├── asset/                 # 진단 관련 템플릿
│   ├── plan/                  # 플랜 관련 템플릿
│   └── reward/                # 리워드 관련 템플릿
├── static/                     # 정적 파일
│   ├── css/                   # 스타일시트
│   ├── js/                    # JavaScript
│   └── images/                # 이미지 파일
├── manage.py                   # Django 관리 명령어
└── requirements.txt            # Python 패키지 의존성
```

## 👥 개발팀 구성

### 3명이 각각 하나씩 기능을 담당

1. **자산 관리 역량 진단 담당자** (`/asset`)
   - 진단 질문 관리
   - 점수 계산 알고리즘
   - 피드백 생성 시스템

2. **AI 기반 플랜 생성 담당자** (`/plan`)
   - 소득 예측 모델
   - 자산 관리 플랜 생성
   - 신용등급 개선 계획

3. **게이미피케이션 담당자** (`/reward`)
   - 포인트 및 레벨 시스템
   - 퀴즈 시스템
   - 업적 및 리워드

## 🎨 디자인 가이드라인

- **대표색**: `#1d5091` (진한 파란색) - Money(자산)의 안정성과 신뢰성
- **보조색**: `#f8f9fa` (연한 회색) - Coach(코칭)의 친근함과 접근성
- **강조색**: `#28a745` (초록색) - 성장과 발전을 상징
- **경고색**: `#ffc107` (노란색) - 주의와 경계를 상징
- **위험색**: `#dc3545` (빨간색) - 위험 요소를 상징

## 🔧 개발 환경 설정

### 개발 도구
- **코드 포맷팅**: Black
- **린팅**: Flake8
- **Import 정렬**: isort
- **테스트**: pytest

### 환경 변수 설정
```bash
# .env 파일 생성
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Hugging Face API 설정 (AI 기능 사용 시 필수)
HF_API_KEY=your_huggingface_api_key_here
HUGGINGFACEHUB_API_TOKEN=your_huggingface_api_key_here
AI_MODEL_NAME=meta-llama/Meta-Llama-3.1-8B-Instruct
```

**Hugging Face API 키 발급 방법:**
1. [Hugging Face](https://huggingface.co/) 계정 생성
2. Settings > Access Tokens에서 새 토큰 생성
3. 위의 환경 변수에 토큰 값 입력

## 🤖 AI 기능 상세 설명

### Llama 3.1 8B 모델 활용
- **모델**: Meta Llama 3.1 8B Instruct
- **플랫폼**: Hugging Face Inference API
- **특화 기능**: 프리랜서 소득 패턴 분석 및 예측

### 소득 예측 프로세스
1. **데이터 입력**: 최근 12개월 소득 데이터
2. **AI 분석**: Llama 모델이 소득 패턴, 계절성, 트렌드 분석
3. **예측 생성**: 다음 달 및 연간 소득 예측
4. **신뢰도 평가**: 예측의 신뢰도와 변동성 지수 제공
5. **위험 분석**: 소득 변동성 기반 위험 요소 식별
6. **권장사항**: 개인별 맞춤형 개선 방안 제시

### 동적 플랜 생성
- **실시간 조정**: 소득 변동성에 따른 플랜 비율 자동 조정
- **계절성 고려**: 프리랜서 특성상 연말/연초 프로젝트 집중 고려
- **위험도 기반**: 변동성에 따른 보수형/균형형/공격형 플랜 자동 선택
- **적응 전략**: 성장 트렌드에 따른 투자/저축 비율 동적 조정

### API 엔드포인트
- `POST /plan/api/predict-income/`: 실시간 소득 예측
- `POST /plan/api/generate-plan/`: 동적 플랜 생성
- `GET /plan/analytics/<plan_id>/`: 플랜 분석 및 인사이트

## 📊 데이터베이스 모델

### Asset App
- `AssetAssessment`: 진단 결과
- `AssessmentQuestion`: 진단 질문
- `AssessmentAnswer`: 사용자 답변

### Plan App
- `IncomePrediction`: 소득 예측
- `FinancialPlan`: 자산 관리 플랜
- `MonthlyPlan`: 월별 세부 계획

### Reward App
- `UserProfile`: 사용자 프로필 및 포인트
- `Quiz`: 퀴즈 정보
- `Achievement`: 업적 시스템
- `FinancialBenefit`: 금융 혜택

## 🚀 배포

### 프로덕션 환경
```bash
# 환경 변수 설정
DEBUG=False
SECRET_KEY=production-secret-key

# 정적 파일 수집
python manage.py collectstatic

# 데이터베이스 마이그레이션
python manage.py migrate

# Gunicorn 실행 (예시)
gunicorn financial_academy.wsgi:application
```

## 🤝 기여 방법

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📖 사용법 가이드

### 1. AI 소득 예측 사용하기
1. `/plan/income-prediction/` 페이지 접속
2. 소득 유형 선택 (프리랜서/사업자/급여소득자/혼합소득)
3. 최근 12개월 소득 데이터 입력
4. 실시간으로 AI 예측 결과 확인
5. 예측 결과를 바탕으로 플랜 생성

### 2. 동적 플랜 생성하기
1. 소득 예측 완료 후 플랜 설정 페이지로 이동
2. 플랜 유형 선택 (보수형/균형형/공격형)
3. 목표 저축률 및 비상금 목표 설정
4. 현재 신용등급 입력
5. AI가 생성한 맞춤형 플랜 확인

### 3. 플랜 분석 및 모니터링
1. 생성된 플랜의 상세 정보 확인
2. 월별 계획 및 지출 비율 검토
3. 분석 페이지에서 차트를 통한 시각적 분석
4. AI 인사이트 및 권장사항 확인
5. 신용등급 개선 계획 실행

## 🔧 문제 해결

### Hugging Face API 오류
- API 키가 올바르게 설정되었는지 확인
- 인터넷 연결 상태 확인
- API 사용량 한도 확인

### AI 예측이 작동하지 않는 경우
- 최소 3개월 이상의 소득 데이터 입력 필요
- 소득 데이터에 0이 아닌 값이 포함되어야 함
- API 키가 유효한지 확인

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해 주세요.

---

**Much** - AI가 코칭하는 스마트 자산 관리 🚀

*Money + Coach = Much*
