# AI 모델 설정 가이드

## 문제 해결 완료 ✅

AI 모델이 잘 불러와지지 않는 문제를 해결했습니다. 주요 개선사항은 다음과 같습니다:

### 1. API 키 검증 개선

- 유효하지 않은 API 키 감지 및 경고 메시지 추가
- API 키가 없을 때 자동으로 폴백 모드로 전환

### 2. 모델 호환성 개선

- 여러 API 메서드 지원 (chat_completion, text_generation, conversational)
- 모델별 호환성 문제 해결을 위한 폴백 메커니즘 추가

### 3. 안정성 향상

- AI 서비스 실패 시 통계 기반 폴백 자동 전환
- 상세한 로깅으로 문제 진단 가능

## 현재 상태

현재 AI 모델은 **통계 기반 폴백 모드**로 동작하고 있습니다. 이는 API 키가 설정되지 않았기 때문입니다.

## AI 모델 활성화 방법

### 1. Hugging Face API 키 발급

1. [Hugging Face](https://huggingface.co) 계정 생성
2. [Settings > Access Tokens](https://huggingface.co/settings/tokens)에서 새 토큰 생성
3. 토큰을 복사하여 저장

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가:

```bash
# Hugging Face API 설정
HF_API_KEY=your_actual_api_key_here
HUGGINGFACEHUB_API_TOKEN=your_actual_api_key_here

# AI 모델 설정 (선택사항)
AI_MODEL_NAME=microsoft/DialoGPT-medium
```

### 3. 지원되는 AI 모델

현재 지원되는 모델들:

- `microsoft/DialoGPT-medium` (기본값, 안정적)
- `meta-llama/Llama-3.2-1B-Instruct` (더 강력하지만 API 제한 있음)
- `microsoft/DialoGPT-large` (더 큰 모델)

### 4. 서버 재시작

환경 변수 변경 후 Django 서버를 재시작:

```bash
python manage.py runserver
```

## AI 기능 확인

### 1. 소득 예측 테스트

```python
from plan.ai_services import FreelancerIncomePredictor
from decimal import Decimal

predictor = FreelancerIncomePredictor()
incomes = [Decimal('3000000')] * 12
result = predictor.predict_income(incomes, 'freelance')
print(f"예측 방법: {result['prediction_method']}")
```

### 2. 스마트 플랜 생성 테스트

```python
from plan.smart_plan_generator import SmartPlanGenerator
from decimal import Decimal

generator = SmartPlanGenerator()
plan = generator.generate_smart_plan(user, Decimal('3000000'))
print(f"생성 방법: {plan['generated_by']}")
```

## 폴백 모드

API 키가 없거나 AI 모델 호출이 실패할 경우:

- **소득 예측**: 통계 기반 알고리즘 사용
- **플랜 생성**: 규칙 기반 알고리즘 사용

폴백 모드에서도 기본적인 기능은 모두 동작합니다.

## 문제 해결

### API 키 관련 오류

```
WARNING: 유효한 Hugging Face API 키가 설정되지 않았습니다.
```

→ `.env` 파일에 올바른 API 키를 설정하세요.

### 모델 호출 실패

```
ERROR: AI 계획 생성 실패: ...
```

→ 다른 모델로 변경하거나 폴백 모드를 사용하세요.

### 네트워크 오류

```
ERROR: Connection failed
```

→ 인터넷 연결을 확인하고 Hugging Face 서비스 상태를 확인하세요.

## 성능 최적화

1. **캐싱**: 동일한 입력에 대해 결과 캐싱
2. **배치 처리**: 여러 요청을 한 번에 처리
3. **모델 선택**: 용도에 맞는 적절한 모델 선택

## 보안 주의사항

- API 키를 코드에 직접 하드코딩하지 마세요
- `.env` 파일을 `.gitignore`에 추가하세요
- 프로덕션에서는 환경 변수로 API 키를 관리하세요

## 추가 지원

문제가 지속되면 다음을 확인하세요:

1. Hugging Face API 할당량
2. 모델 가용성
3. 네트워크 연결 상태
4. Django 로그 파일

---

**참고**: AI 모델이 없어도 애플리케이션의 핵심 기능은 모두 동작합니다. AI는 추가적인 정확도와 개인화를 제공하는 옵션입니다.

