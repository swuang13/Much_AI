"""
개인 맞춤형 저축/신용 코칭 모듈 (Llama 3.1 8B 시도 + 폴백)
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

import requests
from django.conf import settings
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)


class PersonalizedCoach:
    """Llama 3.1 8B로 코칭 시도, 실패 시 규칙 기반 폴백"""

    def __init__(self) -> None:
        api_key = getattr(settings, "HF_API_KEY", "token_key_here")
        self.model = getattr(
            settings, "AI_MODEL_NAME", "meta-llama/Llama-3.2-1B-Instruct"
        )
        self.client: Optional[InferenceClient] = None
        if api_key:
            try:
                # Novita provider 사용
                self.client = InferenceClient(
                    provider="novita",
                    api_key=api_key,
                )
                logger.info(
                    f"AI 클라이언트 초기화 성공 - 모델: {self.model} (Novita provider)"
                )
            except Exception as e:
                logger.error(f"AI 클라이언트 초기화 실패: {e}")
                self.client = None
        else:
            logger.warning(
                f"AI 설정 누락 - API 키: {'있음' if api_key else '없음'}, 모델: {self.model}"
            )
            self.client = None

    def generate_personalized_advice(self, user, plan, income_prediction) -> Dict:
        """사용자, 플랜, 소득 예측 정보를 기반으로 개인화된 코칭 생성"""
        try:
            logger.info("개인화 코칭 생성 시작")

            # 상세한 사용자 프로필 정보 수집
            profile = self._build_detailed_profile(user, plan, income_prediction)
            logger.info(
                f"사용자 프로필 구축 완료 - 연령: {profile.get('age')}, 소득: {profile.get('monthly_income')}, 신용점수: {profile.get('current_credit_score')}"
            )

            # 플랜 정보
            predicted_monthly_income = income_prediction.predicted_monthly_income
            current_credit_score = plan.current_credit_score

            # 신용 스냅샷 정보 (있다면)
            snapshot = None
            try:
                from .models import CreditScoreSnapshot

                snapshot = (
                    CreditScoreSnapshot.objects.filter(user=user)
                    .order_by("-created_at")
                    .first()
                )
                if snapshot:
                    logger.info(
                        f"신용 스냅샷 로드 완료 - 이용률: {snapshot.utilization_rate}%"
                    )
                else:
                    logger.info("신용 스냅샷 없음")
            except Exception as e:
                logger.warning(f"신용 스냅샷 로드 실패: {e}")

            # AI 코칭 시도
            logger.info("AI 코칭 시도 시작")
            ai_result = self._try_ai(
                predicted_monthly_income,
                current_credit_score,
                profile,
                snapshot,
            )

            if ai_result:
                logger.info("Llama 3.1 8B 모델 성공")
                return ai_result
            else:
                logger.error("Llama 3.1 8B 모델 실패 - 응답 없음")
                return None

        except Exception as e:
            logger.error(f"Llama 3.1 8B 모델 호출 실패: {e}", exc_info=True)
            return None

    def _build_detailed_profile(self, user, plan, income_prediction) -> Dict:
        """상세한 사용자 프로필 정보 구축"""
        # 기본 프로필 정보
        profile = {
            "age": getattr(user, "age", 25),
            "gender": getattr(user, "gender", "unknown"),
            "occupation": getattr(user, "occupation", "freelancer"),
            "location": getattr(user, "location", "seoul"),
        }

        # 소득 관련 정보
        monthly_income = float(income_prediction.predicted_monthly_income)
        yearly_income = monthly_income * 12

        profile.update(
            {
                "monthly_income": monthly_income,
                "yearly_income": yearly_income,
                "income_volatility": getattr(
                    income_prediction, "income_volatility", "stable"
                ),
                "income_type": getattr(income_prediction, "income_type", "freelancer"),
            }
        )

        # 플랜 관련 정보
        profile.update(
            {
                "target_savings_rate": plan.target_savings_rate,
                "emergency_fund_target": float(plan.emergency_fund_target),
                "plan_type": plan.plan_type,
            }
        )

        # 신용 관련 정보
        profile.update(
            {
                "current_credit_score": plan.current_credit_score,
                "credit_level": self._analyze_credit_level(plan.current_credit_score),
            }
        )

        # 생애주기 및 상황 분석
        age = profile["age"]
        profile.update(
            {
                "life_stage": self._analyze_life_stage(age, profile),
                "income_level": self._analyze_income_level(
                    income_prediction.predicted_monthly_income
                ),
                "financial_priority": self._determine_financial_priority(
                    age, monthly_income, plan.current_credit_score
                ),
            }
        )

        # 지역별 특성
        location = profile["location"]
        profile.update(
            {
                "region_characteristics": self._get_region_characteristics(location),
                "available_policies": self._get_available_policies(
                    location, age, monthly_income
                ),
            }
        )

        # 직업별 특성
        occupation = profile["occupation"]
        profile.update(
            {
                "occupation_characteristics": self._get_occupation_characteristics(
                    occupation
                ),
                "income_stability": self._assess_income_stability(
                    occupation, income_prediction
                ),
            }
        )

        return profile

    def _determine_financial_priority(
        self, age: int, monthly_income: float, credit_score: int
    ) -> str:
        """금융 우선순위 결정"""
        if credit_score < 600:
            return "신용점수 개선 우선"
        elif monthly_income < 2000000:
            return "비상자금 마련 우선"
        elif age < 30:
            return "자산 형성 초기"
        elif age < 40:
            return "자산 축적 중점"
        else:
            return "자산 증식 및 보전"

    def _get_region_characteristics(self, location: str) -> Dict:
        """지역별 특성 정보"""
        region_info = {
            "seoul": {
                "living_cost": "높음",
                "housing_cost": "매우 높음",
                "job_opportunities": "풍부",
                "youth_policies": "다양함",
            },
            "busan": {
                "living_cost": "중간",
                "housing_cost": "높음",
                "job_opportunities": "보통",
                "youth_policies": "보통",
            },
            "incheon": {
                "living_cost": "중간",
                "housing_cost": "중간",
                "job_opportunities": "보통",
                "youth_policies": "보통",
            },
        }
        return region_info.get(location.lower(), region_info["seoul"])

    def _get_available_policies(
        self, location: str, age: int, monthly_income: float
    ) -> List[str]:
        """지역, 연령, 소득에 따른 이용 가능한 정책"""
        policies = []

        if age <= 34:
            policies.append("청년도약계좌")
            policies.append("청년정책 통합지원센터")

        if location.lower() == "seoul" and age <= 34:
            policies.append("서울 청년월세지원")
            policies.append("서울 청년수당")

        if monthly_income < 3000000:
            policies.append("청년희망적금")
            policies.append("청년내일채움공제")

        return policies

    def _get_occupation_characteristics(self, occupation: str) -> Dict:
        """직업별 특성 정보"""
        occupation_info = {
            "freelancer": {
                "income_stability": "불안정",
                "tax_benefits": "소득공제 가능",
                "retirement_planning": "개인연금 필요",
                "insurance_needs": "높음",
            },
            "employee": {
                "income_stability": "안정적",
                "tax_benefits": "4대보험 가입",
                "retirement_planning": "퇴직금 + 개인연금",
                "insurance_needs": "보통",
            },
            "business_owner": {
                "income_stability": "가변적",
                "tax_benefits": "사업자 혜택",
                "retirement_planning": "사업자연금",
                "insurance_needs": "높음",
            },
        }
        return occupation_info.get(occupation.lower(), occupation_info["freelancer"])

    def _assess_income_stability(self, occupation: str, income_prediction) -> str:
        """소득 안정성 평가"""
        volatility = getattr(income_prediction, "income_volatility", "stable")

        if occupation == "freelancer":
            if volatility == "high":
                return "매우 불안정"
            elif volatility == "medium":
                return "불안정"
            else:
                return "보통"
        elif occupation == "employee":
            return "안정적"
        else:
            return "가변적"

    def generate_advice(
        self,
        predicted_monthly_income: Decimal,
        current_credit_score: int,
        profile: Dict,
        snapshot,
    ) -> Dict:
        ai = self._try_ai(
            predicted_monthly_income,
            current_credit_score,
            profile,
            snapshot,
        )
        if ai:
            return ai
        return self._fallback(
            predicted_monthly_income, current_credit_score, profile, snapshot
        )

    def _try_ai(
        self,
        predicted_monthly_income: Decimal,
        current_credit_score: int,
        profile: Dict,
        snapshot,
    ) -> Optional[Dict]:
        if not self.client or not self.model:
            logger.warning("AI 클라이언트 또는 모델이 설정되지 않음")
            return None

        logger.info(f"AI 모델 호출 시작 - 모델: {self.model}")
        prompt = self._build_prompt(
            predicted_monthly_income, current_credit_score, profile, snapshot
        )
        logger.info(f"프롬프트 생성 완료 - 길이: {len(prompt)} 문자")

        # Llama 모델 호출 시도 (Novita provider)
        try:
            logger.info("Llama 모델 호출 중... (Novita provider)")

            # chat completions API 사용
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.2,
                top_p=0.9,
            )

            if completion and completion.choices:
                text = completion.choices[0].message.content
                logger.info(f"Llama 모델 응답 수신 - 길이: {len(text)} 문자")
                data = self._parse(text)
                if data:
                    logger.info("Llama 모델 파싱 성공")
                    return data
                else:
                    logger.warning("Llama 모델 파싱 실패")
            else:
                logger.warning("Llama 모델 응답이 비어있음")

        except Exception as e:
            logger.error(f"Llama 모델 호출 실패: {e}")

        return None

    def _build_prompt(
        self,
        predicted_monthly_income: Decimal,
        current_credit_score: int,
        profile: Dict,
        snapshot,
    ) -> str:
        # 퓨샷 러닝을 위한 예시와 개선된 프롬프트
        return self._build_enhanced_prompt_with_few_shot(
            predicted_monthly_income, current_credit_score, profile, snapshot
        )

    def _build_enhanced_prompt_with_few_shot(
        self,
        predicted_monthly_income: Decimal,
        current_credit_score: int,
        profile: Dict,
        snapshot,
    ) -> str:
        # 사용자 상황 분석
        age = profile.get("age", 25)
        location = profile.get("location", "seoul")
        occupation = profile.get("occupation", "freelancer")

        # 상황별 맞춤형 분석
        income_level = self._analyze_income_level(predicted_monthly_income)
        credit_level = self._analyze_credit_level(current_credit_score)
        life_stage = self._analyze_life_stage(age, profile)

        # 퓨샷 러닝 예시
        few_shot_examples = self._get_few_shot_examples()

        return f"""당신은 한국의 금융 전문가입니다. 사용자의 구체적인 상황을 분석하여 개인 맞춤형 금융 조언을 제공하세요.

## 사용자 프로필 분석
- **연령**: {age}세 ({life_stage})
- **직업**: {occupation}
- **지역**: {location}
- **월 소득**: {predicted_monthly_income:,.0f}원 ({income_level})
- **신용점수**: {current_credit_score}점 ({credit_level})
- **신용 이용률**: {snapshot.utilization_rate if snapshot else 0}%
- **결제 성실도**: {snapshot.on_time_payment_ratio if snapshot else 0}%
- **신용 연령**: {snapshot.credit_age_months if snapshot else 0}개월

## 퓨샷 러닝 예시

{few_shot_examples}

## 현재 사용자 맞춤 분석 요청

위 사용자 정보를 바탕으로 다음을 고려하여 개인 맞춤형 조언을 제공하세요:

1. **소득 수준별 전략**: {income_level}에 맞는 저축/투자 전략
2. **신용점수별 개선**: {credit_level}에서 다음 단계로 올라가는 구체적 방법
3. **생애주기별 목표**: {life_stage}에 적합한 금융 목표 설정
4. **지역별 혜택**: {location}에서 활용 가능한 청년 정책
5. **직업별 특성**: {occupation}의 소득 특성을 고려한 현실적 계획

**반드시 JSON 형식으로만 응답하세요:**

{{
  "savings_plan": [
    {{"title": "구체적 제목", "detail": "실행 가능한 상세 계획 (금액, 기간, 방법 포함)"}},
    {{"title": "구체적 제목", "detail": "실행 가능한 상세 계획"}}
  ],
  "credit_plan": [
    {{"title": "구체적 제목", "detail": "신용점수 개선을 위한 구체적 방법"}},
    {{"title": "구체적 제목", "detail": "신용점수 개선을 위한 구체적 방법"}}
  ],
  "priority_actions": [
    {{"title": "즉시 실행할 과제", "detail": "1-3개월 내 실행 가능한 구체적 행동"}},
    {{"title": "중기 과제", "detail": "3-6개월 내 실행 가능한 구체적 행동"}}
  ],
  "kpis": {{
    "target_savings_rate": {self._calculate_target_savings_rate(predicted_monthly_income, age)},
    "target_utilization_rate": {self._calculate_target_utilization_rate(current_credit_score)}
  }},
  "policies": [
    {{"title": "정책명", "summary": "정책 설명", "link": "URL", "eligibility_hint": "신청 조건"}}
  ],
  "summaries": {{
    "credit": "현재 신용점수 {current_credit_score}점을 {self._get_next_credit_goal(current_credit_score)}점으로 개선하기 위한 핵심 전략",
    "income": "월 {predicted_monthly_income:,.0f}원 소득으로 {life_stage}에 맞는 재정 목표 달성 방안"
  }}
}}

**중요**: 모든 조언은 구체적인 금액, 기간, 실행 방법을 포함해야 하며, 사용자의 현재 상황에 맞는 현실적인 목표를 제시하세요."""

    def _analyze_income_level(self, monthly_income: Decimal) -> str:
        """소득 수준 분석"""
        income = float(monthly_income)
        if income < 2000000:
            return "저소득층 (비상자금 우선)"
        elif income < 4000000:
            return "중소득층 (저축+투자 병행)"
        elif income < 6000000:
            return "중상소득층 (다양한 투자 상품)"
        else:
            return "고소득층 (자산 관리 중심)"

    def _analyze_credit_level(self, credit_score: int) -> str:
        """신용점수 수준 분석"""
        if credit_score < 600:
            return "신용점수 개선 필요 (기초 신용 관리)"
        elif credit_score < 700:
            return "보통 수준 (신용도 향상 중)"
        elif credit_score < 800:
            return "양호한 수준 (신용상품 활용)"
        else:
            return "우수한 수준 (프리미엄 상품 활용)"

    def _analyze_life_stage(self, age: int, profile: Dict) -> str:
        """생애주기 분석"""
        if age < 30:
            return "청년기 (자산 형성 초기)"
        elif age < 40:
            return "성인 초기 (자산 축적기)"
        elif age < 50:
            return "성인 중기 (자산 증식기)"
        else:
            return "성인 후기 (자산 보전기)"

    def _calculate_target_savings_rate(
        self, monthly_income: Decimal, age: int
    ) -> float:
        """연령과 소득을 고려한 목표 저축률 계산"""
        base_rate = 20.0
        if age < 30:
            base_rate = 15.0  # 청년기는 소득이 낮아 저축률 조정
        elif age > 40:
            base_rate = 25.0  # 중년기는 높은 저축률 필요

        # 소득 수준별 조정
        income = float(monthly_income)
        if income < 2000000:
            base_rate *= 0.8  # 저소득층은 현실적 목표
        elif income > 5000000:
            base_rate *= 1.2  # 고소득층은 높은 목표

        return min(max(base_rate, 10.0), 40.0)  # 10-40% 범위

    def _calculate_target_utilization_rate(self, credit_score: int) -> float:
        """신용점수에 따른 목표 이용률 계산"""
        if credit_score < 600:
            return 15.0  # 낮은 이용률로 신용점수 개선
        elif credit_score < 700:
            return 25.0  # 보통 이용률
        else:
            return 30.0  # 양호한 이용률

    def _get_next_credit_goal(self, current_score: int) -> int:
        """다음 신용점수 목표 설정"""
        if current_score < 600:
            return 650
        elif current_score < 700:
            return 750
        elif current_score < 800:
            return 850
        else:
            return 900

    def _get_few_shot_examples(self) -> str:
        """퓨샷 러닝을 위한 예시"""
        return """### 예시 1: 25세 프리랜서, 월 250만원, 신용점수 580점
{
  "savings_plan": [
    {"title": "비상자금 3개월치 마련", "detail": "월 30만원씩 9개월간 저축하여 270만원 목표"},
    {"title": "청년도약계좌 가입", "detail": "월 5만원씩 정부 기여금 30만원 + 우대금리 혜택"}
  ],
  "credit_plan": [
    {"title": "신용카드 이용률 15% 이하 유지", "detail": "한도 200만원 기준 월 30만원 이하 사용"},
    {"title": "소액대출 우선 상환", "detail": "이자율 높은 대출부터 단계적 상환으로 신용도 개선"}
  ],
  "priority_actions": [
    {"title": "월 예산 200만원 설정", "detail": "고정비 150만원, 변동비 50만원, 저축 30만원"},
    {"title": "신용정보 정기 확인", "detail": "나이스/올크레딧에서 월 1회 무료 조회"}
  ],
  "kpis": {"target_savings_rate": 12.0, "target_utilization_rate": 15.0},
  "policies": [
    {"title": "청년도약계좌", "summary": "정부 기여금 지원", "link": "https://youthaccount.moef.go.kr", "eligibility_hint": "만 19-34세"}
  ],
  "summaries": {
    "credit": "현재 신용점수 580점을 650점으로 개선하기 위해 카드 이용률을 낮추고 정기적 상환을 실시하세요.",
    "income": "월 250만원 소득으로 청년기에 맞는 비상자금 마련과 신용도 개선에 집중하세요."
  }
}

### 예시 2: 28세 직장인, 월 400만원, 신용점수 720점
{
  "savings_plan": [
    {"title": "비상자금 6개월치 마련", "detail": "월 80만원씩 12개월간 저축하여 960만원 목표"},
    {"title": "청년도약계좌 최대 활용", "detail": "월 70만원씩 정부 기여금 500만원 + 우대금리 혜택"}
  ],
  "credit_plan": [
    {"title": "신용카드 이용률 25% 유지", "detail": "한도 500만원 기준 월 125만원 이하 사용"},
    {"title": "신용상품 다양화", "detail": "우대금리 대출이나 혜택 좋은 신용카드 활용"}
  ],
  "priority_actions": [
    {"title": "월 예산 350만원 설정", "detail": "고정비 250만원, 변동비 100만원, 저축 80만원"},
    {"title": "투자 상품 검토", "detail": "펀드, ETF 등 장기 투자 상품 조사"}
  ],
  "kpis": {"target_savings_rate": 20.0, "target_utilization_rate": 25.0},
  "policies": [
    {"title": "청년도약계좌", "summary": "정부 기여금 지원", "link": "https://youthaccount.moef.go.kr", "eligibility_hint": "만 19-34세"}
  ],
  "summaries": {
    "credit": "현재 신용점수 720점을 750점으로 개선하기 위해 신용상품을 다양화하고 이용률을 관리하세요.",
    "income": "월 400만원 소득으로 성인 초기에 맞는 자산 축적과 투자를 병행하세요."
  }
}"""

    def _parse(self, text: str) -> Optional[Dict]:
        """개선된 JSON 파싱 - 더 유연하고 강력한 파싱"""
        try:
            # 텍스트 정리
            t = text.strip()

            # 다양한 JSON 마커 제거
            json_markers = ["```json", "```", "json", "JSON"]
            for marker in json_markers:
                if t.startswith(marker):
                    t = t[len(marker) :].strip()
                if t.endswith(marker):
                    t = t[: -len(marker)].strip()

            # JSON 객체 찾기
            import json
            import re

            # JSON 객체 패턴 찾기
            json_pattern = r"\{.*\}"
            matches = re.findall(json_pattern, t, re.DOTALL)

            if matches:
                # 가장 긴 JSON 객체 선택 (보통 가장 완전한 것)
                json_str = max(matches, key=len)
            else:
                json_str = t

            # JSON 파싱 시도
            data = json.loads(json_str)

            # 필수 키 검증
            required_keys = ("savings_plan", "credit_plan", "priority_actions", "kpis")
            if not all(k in data for k in required_keys):
                logger.warning(f"필수 키 누락: {required_keys}")
                return None

            # 데이터 검증 및 정리
            validated_data = self._validate_and_clean_data(data)
            return validated_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"데이터 파싱 중 오류: {e}")
            return None

    def _validate_and_clean_data(self, data: Dict) -> Dict:
        """데이터 검증 및 정리"""
        try:
            # 기본 구조 보장
            cleaned_data = {
                "savings_plan": [],
                "credit_plan": [],
                "priority_actions": [],
                "kpis": {"target_savings_rate": 20.0, "target_utilization_rate": 20.0},
                "policies": [],
                "summaries": {"credit": "", "income": ""},
            }

            # savings_plan 검증
            if "savings_plan" in data and isinstance(data["savings_plan"], list):
                for item in data["savings_plan"]:
                    if isinstance(item, dict) and "title" in item and "detail" in item:
                        cleaned_data["savings_plan"].append(
                            {
                                "title": str(item["title"]).strip(),
                                "detail": str(item["detail"]).strip(),
                            }
                        )

            # credit_plan 검증
            if "credit_plan" in data and isinstance(data["credit_plan"], list):
                for item in data["credit_plan"]:
                    if isinstance(item, dict) and "title" in item and "detail" in item:
                        cleaned_data["credit_plan"].append(
                            {
                                "title": str(item["title"]).strip(),
                                "detail": str(item["detail"]).strip(),
                            }
                        )

            # priority_actions 검증
            if "priority_actions" in data and isinstance(
                data["priority_actions"], list
            ):
                for item in data["priority_actions"]:
                    if isinstance(item, dict) and "title" in item and "detail" in item:
                        cleaned_data["priority_actions"].append(
                            {
                                "title": str(item["title"]).strip(),
                                "detail": str(item["detail"]).strip(),
                            }
                        )

            # kpis 검증
            if "kpis" in data and isinstance(data["kpis"], dict):
                kpis = data["kpis"]
                if "target_savings_rate" in kpis:
                    try:
                        cleaned_data["kpis"]["target_savings_rate"] = float(
                            kpis["target_savings_rate"]
                        )
                    except (ValueError, TypeError):
                        pass
                if "target_utilization_rate" in kpis:
                    try:
                        cleaned_data["kpis"]["target_utilization_rate"] = float(
                            kpis["target_utilization_rate"]
                        )
                    except (ValueError, TypeError):
                        pass

            # policies 검증
            if "policies" in data and isinstance(data["policies"], list):
                for item in data["policies"]:
                    if isinstance(item, dict) and "title" in item:
                        policy = {
                            "title": str(item["title"]).strip(),
                            "summary": str(item.get("summary", "")).strip(),
                            "link": str(item.get("link", "")).strip(),
                            "eligibility_hint": str(
                                item.get("eligibility_hint", "")
                            ).strip(),
                        }
                        cleaned_data["policies"].append(policy)

            # summaries 검증
            if "summaries" in data and isinstance(data["summaries"], dict):
                summaries = data["summaries"]
                if "credit" in summaries:
                    cleaned_data["summaries"]["credit"] = str(
                        summaries["credit"]
                    ).strip()
                if "income" in summaries:
                    cleaned_data["summaries"]["income"] = str(
                        summaries["income"]
                    ).strip()

            return cleaned_data

        except Exception as e:
            logger.error(f"데이터 검증 중 오류: {e}")
            return data  # 원본 데이터 반환

    def _fallback(
        self,
        predicted_monthly_income: Decimal,
        current_credit_score: int,
        profile: Dict,
        snapshot,
    ) -> Dict:
        # richer, structured fallback items so frontend can render details
        savings: List[Dict] = []
        credit: List[Dict] = []
        priority: List[Dict] = []
        income = float(predicted_monthly_income or 0)

        if income < 2500000:
            savings += [
                {
                    "title": "비상금 우선 목표",
                    "detail": "비상금: 월 소득의 3~6개월치(약 {:,.0f}원). 우선 자유적금으로 시작하세요.".format(
                        income * 3
                    ),
                },
                {
                    "title": "저축 습관 만들기",
                    "detail": "월 2~3회 소액 자동이체(예: 월 50,000원)로 저축 습관을 형성하세요.",
                },
            ]
        elif income <= 4000000:
            savings += [
                {
                    "title": "월 소득 20% 저축",
                    "detail": f"권장 저축률: 월 소득의 20% ({income*0.2:,.0f}원)",
                },
                {
                    "title": "장기 투자 비중 확대",
                    "detail": "연금저축/ETF 비중을 늘려 장기 성장을 도모하세요.",
                },
            ]
        else:
            savings += [
                {
                    "title": "월 소득 25% 저축",
                    "detail": f"권장 저축률: 25% ({income*0.25:,.0f}원) - 단기/장기 균형 유지",
                },
                {
                    "title": "투자 포트폴리오 분산",
                    "detail": "CMA(단기) + ETF(장기) 혼합으로 유동성 확보 및 장기수익 추구",
                },
            ]

        if snapshot.utilization_rate > 30:
            credit.append(
                {
                    "title": "카드 이용률 관리",
                    "detail": "현재 이용률 {:.1f}%. 목표: 20~30% 이하 유지".format(
                        snapshot.utilization_rate
                    ),
                }
            )
        if snapshot.on_time_payment_ratio < 98:
            credit.append(
                {
                    "title": "연체 방지",
                    "detail": "자동이체 설정으로 연체를 0%에 가깝게 유지하세요.",
                }
            )
        if snapshot.hard_inquiries_12m > 1:
            credit.append(
                {
                    "title": "신용조회/대출 제한",
                    "detail": "최근 조회가 많습니다. 12개월 내 신규 대출·조회 최소화하세요.",
                }
            )
        if snapshot.credit_age_months < 36:
            credit.append(
                {
                    "title": "신용연령 쌓기",
                    "detail": "오래된 계좌 유지로 신용연령을 늘리세요(현재 {}개월).".format(
                        snapshot.credit_age_months
                    ),
                }
            )
        if snapshot.credit_mix_score < 50:
            credit.append(
                {
                    "title": "신용 믹스 개선",
                    "detail": "카드·할부·소액대출의 균형을 맞추어 신용프로필을 개선하세요.",
                }
            )

        priority += [
            {
                "title": "비상금 자동이체",
                "detail": "다음 급여일에 비상금 자동이체(월 {}) 설정".format(
                    int(income * 0.1)
                ),
            },
            {
                "title": "지출 알림",
                "detail": "결제일 3일 전 잔액 알림을 설정하여 연체를 예방",
            },
        ]

        kpis = {
            "target_savings_rate": 25 if income > 4000000 else 20,
            "target_utilization_rate": 30,
        }

        advice = {
            "savings_plan": savings,
            "credit_plan": credit,
            "priority_actions": priority,
            "kpis": kpis,
            "source": "rule_based_fallback",
        }

        # 간단 요약
        advice["summaries"] = {
            "credit": "이용률을 30% 이하로 유지하고 연체를 방지하면 단기적으로 점수 개선에 도움이 됩니다.",
            "income": "월 소득의 20~25%를 저축하고 장기 상품 비중을 확대하면 목표 비상금과 투자 밸런스를 달성할 수 있습니다.",
        }

        # 정책 추천(폴백 규칙)
        try:
            advisor = PolicyAdvisor()
            age = int(profile.get("age") or 0)
            region = str(profile.get("region") or "")
            employment = str(profile.get("employment") or "")
            income = float(predicted_monthly_income or 0)
            advice["policies"] = advisor.recommend(
                age=age, region=region, employment=employment, monthly_income=income
            )
        except Exception:
            advice["policies"] = []

        return advice

    def _fallback_personalized(self, user, plan, income_prediction) -> Dict:
        """사용자 데이터 기반 개인화된 폴백 코칭"""
        try:
            # 사용자 정보 추출
            monthly_income = float(income_prediction.predicted_monthly_income)
            credit_score = plan.current_credit_score
            target_savings_rate = plan.target_savings_rate

            # 소득 기반 저축 목표 계산
            monthly_savings_target = monthly_income * (float(target_savings_rate) / 100)

            # 신용점수 기반 조언
            if credit_score < 600:
                credit_advice = "신용점수가 낮습니다. 정기적인 신용정보 확인과 소액대출 상환을 우선하세요."
                credit_actions = [
                    {
                        "title": "신용정보 정기 확인",
                        "detail": "나이스/올크레딧에서 월 1회 무료 조회",
                    },
                    {
                        "title": "소액대출 우선 상환",
                        "detail": "이자 부담이 큰 대출부터 단계적 상환",
                    },
                ]
            elif credit_score < 700:
                credit_advice = "신용점수가 보통입니다. 카드 이용률 관리와 정기적 상환으로 개선하세요."
                credit_actions = [
                    {
                        "title": "카드 이용률 관리",
                        "detail": "한도 대비 30% 이하로 유지",
                    },
                    {
                        "title": "정기적 상환",
                        "detail": "연체 없이 정시 상환으로 신용도 향상",
                    },
                ]
            else:
                credit_advice = "신용점수가 양호합니다. 현재 상태를 유지하면서 추가 신용상품 활용을 고려하세요."
                credit_actions = [
                    {
                        "title": "신용상품 활용",
                        "detail": "우대금리 대출이나 신용카드 혜택 활용",
                    },
                    {
                        "title": "신용점수 유지",
                        "detail": "현재 상태 유지를 위한 지속적 관리",
                    },
                ]

            # 소득 기반 저축 조언 (사용자 맞춤형)
            if monthly_income < 2000000:
                savings_advice = (
                    f"월 {monthly_income:,.0f}원 소득으로는 비상자금 마련이 우선입니다. "
                    f"현재 소득 대비 {target_savings_rate}% 저축률로 월 {monthly_savings_target:,.0f}원씩 저축하세요."
                )
                savings_actions = [
                    {
                        "title": f"비상자금 마련 (월 {monthly_savings_target:,.0f}원)",
                        "detail": f"월 {monthly_savings_target:,.0f}원씩 3개월치 비상자금 목표 (총 {monthly_savings_target * 3:,.0f}원)",
                    },
                    {
                        "title": "소액 적금 활용",
                        "detail": f"월 {monthly_savings_target:,.0f}원 기준 은행별 소액 적금 상품 검토",
                    },
                ]
            elif monthly_income < 4000000:
                savings_advice = (
                    f"월 {monthly_income:,.0f}원 소득으로는 저축과 투자를 병행할 수 있습니다. "
                    f"현재 소득 대비 {target_savings_rate}% 저축률로 월 {monthly_savings_target:,.0f}원씩 저축하세요."
                )
                savings_actions = [
                    {
                        "title": f"비상자금 마련 (월 {monthly_savings_target:,.0f}원)",
                        "detail": f"월 {monthly_savings_target:,.0f}원씩 6개월치 비상자금 목표 (총 {monthly_savings_target * 6:,.0f}원)",
                    },
                    {
                        "title": "청년도약계좌 활용",
                        "detail": f"월 {monthly_savings_target:,.0f}원 기준 정부 기여금과 우대금리로 목돈 마련",
                    },
                ]
            else:
                savings_advice = (
                    f"월 {monthly_income:,.0f}원 소득으로는 다양한 투자 상품을 고려할 수 있습니다. "
                    f"현재 소득 대비 {target_savings_rate}% 저축률로 월 {monthly_savings_target:,.0f}원씩 저축하세요."
                )
                savings_actions = [
                    {
                        "title": f"비상자금 마련 (월 {monthly_savings_target:,.0f}원)",
                        "detail": f"월 {monthly_savings_target:,.0f}원씩 12개월치 비상자금 목표 (총 {monthly_savings_target * 12:,.0f}원)",
                    },
                    {
                        "title": "투자 상품 검토",
                        "detail": f"월 {monthly_savings_target:,.0f}원 기준 펀드, ETF 등 장기 투자 상품 검토",
                    },
                ]

            # 우선 과제 (사용자 맞춤형)
            priority_actions = [
                {
                    "title": f"예산 설정 (월 {monthly_income:,.0f}원 기준)",
                    "detail": f"월 {monthly_income:,.0f}원 소득에서 {monthly_savings_target:,.0f}원 저축 후 {monthly_income - monthly_savings_target:,.0f}원으로 생활비 계획 수립",
                },
                {
                    "title": f"신용관리 (현재 {credit_score}점)",
                    "detail": f"현재 신용점수 {credit_score}점에서 {'800점 이상' if credit_score < 800 else '900점 이상'} 목표로 개선 계획 수립",
                },
            ]

            # KPI 설정
            kpis = {
                "target_savings_rate": target_savings_rate,
                "target_utilization_rate": 20.0 if credit_score < 600 else 30.0,
            }

            # 정책 추천
            try:
                from .coaching import PolicyAdvisor

                advisor = PolicyAdvisor()
                policies = advisor.recommend(
                    age=25,  # 기본값
                    region="seoul",
                    employment="freelancer",
                    monthly_income=monthly_income,
                )
            except Exception as e:
                logger.warning(f"정책 추천 실패: {e}")
                policies = [
                    {
                        "title": "청년정책 통합지원센터",
                        "summary": "맞춤형 정책 검색",
                        "link": "https://www.youthcenter.go.kr",
                        "eligibility_hint": "모든 청년",
                    },
                ]

            return {
                "savings_plan": savings_actions,
                "credit_plan": credit_actions,
                "priority_actions": priority_actions,
                "kpis": kpis,
                "policies": policies,
                "summaries": {
                    "credit": credit_advice,
                    "income": savings_advice,
                },
            }

        except Exception as e:
            logger.error(f"개인화 폴백 코칭 생성 실패: {str(e)}")
            # 최종 폴백
            return {
                "savings_plan": [
                    {
                        "title": "비상자금 마련",
                        "detail": "월 50만원씩 3개월치 비상자금 목표",
                    },
                    {
                        "title": "청년도약계좌 활용",
                        "detail": "정부 기여금과 우대금리로 목돈 마련",
                    },
                ],
                "credit_plan": [
                    {
                        "title": "신용카드 이용률 관리",
                        "detail": "한도 대비 20% 이하 유지",
                    },
                    {
                        "title": "정기적 신용정보 확인",
                        "detail": "나이스/올크레딧에서 무료 조회",
                    },
                ],
                "priority_actions": [
                    {
                        "title": "예산 설정",
                        "detail": "매월 고정/변동 지출 계획 수립",
                    },
                    {
                        "title": "소액대출 상환",
                        "detail": "이자 부담이 큰 대출부터 우선 상환",
                    },
                ],
                "kpis": {"target_savings_rate": 20.0, "target_utilization_rate": 20.0},
                "policies": [
                    {
                        "title": "청년정책 통합지원센터",
                        "summary": "맞춤형 정책 검색",
                        "link": "https://www.youthcenter.go.kr",
                        "eligibility_hint": "모든 청년",
                    },
                ],
                "summaries": {
                    "credit": "신용점수 개선을 위해 카드 사용률을 낮추고 정기적인 신용관리를 실시하세요.",
                    "income": "안정적인 소득 기반으로 월 50만원 저축 목표를 설정하여 비상자금을 마련하세요.",
                },
            }


class PolicyAdvisor:
    """청년 정책/제도 추천 (규칙 기반 폴백)

    외부 API 없이 간단한 규칙으로 대표 정책을 추천합니다.
    실제 신청 가능 여부는 기관 요건을 반드시 확인해야 합니다.
    """

    def recommend(
        self,
        *,
        age: int,
        region: str,
        employment: str,
        monthly_income: float,
    ) -> List[Dict]:
        items: List[Dict] = []

        is_youth = age <= 34 if age else True
        if is_youth:
            items.append(
                {
                    "title": "청년도약계좌",
                    "summary": "5년 만기 장기저축, 정부 기여 및 우대금리로 목돈 마련 지원",
                    "link": "https://www.gov.kr/portal/service/serviceInfo/PAK000000000285343?from=topSearch",
                    "eligible": True,
                    "eligibility_hint": "만 34세 이하 대상",
                }
            )
            items.append(
                {
                    "title": "청년희망적금(대체상품 포함)",
                    "summary": "근로·사업소득 청년에 대한 비과세 및 저축장려금 지원",
                    "link": "https://www.fss.or.kr",
                }
            )

        seoul_like = any(
            k in (region or "") for k in ["서울", "Seoul"]
        )  # 간단 표기 대응
        if seoul_like and is_youth:
            items.append(
                {
                    "title": "서울 청년월세지원",
                    "summary": "월세 부담 완화를 위한 청년 대상 월세 지원 사업",
                    "link": "https://youth.seoul.go.kr",
                    "eligible": True,
                    "eligibility_hint": "서울 거주 청년 우대",
                }
            )

        # 신용 고도화/금융생활 개선 관련
        items.append(
            {
                "title": "신용회복위원회 소액채무 조정·금융교육",
                "summary": "연체 예방 및 금융역량 강화를 위한 컨설팅/교육 안내",
                "link": "https://www.ccrs.or.kr",
                "eligible": True,
                "eligibility_hint": "연체 이력이나 소액 채무자 대상 권장",
            }
        )

        # 청년정책 통합포털
        items.append(
            {
                "title": "청년정책 통합지원센터",
                "summary": "지역·소득·고용형태 조건으로 맞춤형 정책 검색",
                "link": "https://www.youthcenter.go.kr",
                "eligible": True,
                "eligibility_hint": "조건별 맞춤 검색을 통해 신청 가능 여부 확인",
            }
        )

        return items
