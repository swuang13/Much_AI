"""
AI 기반 스마트 자산 관리 계획 생성기
사용자의 소득, 거래내역, 개인 상황을 종합 분석하여 맞춤형 계획을 생성합니다.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.contrib.auth.models import User

from .mydata import MyDataClient

logger = logging.getLogger(__name__)


class SmartPlanGenerator:
    """AI 기반 스마트 자산 관리 계획 생성기"""

    def __init__(self):
        self.api_key = getattr(settings, "HF_API_KEY", None)
        self.model_name = getattr(
            settings, "AI_MODEL_NAME", "microsoft/DialoGPT-medium"
        )
        self.mydata_client = MyDataClient()

        # API 키 유효성 검사
        if not self.api_key or self.api_key == "your_huggingface_api_key_here":
            logger.warning(
                "유효한 Hugging Face API 키가 설정되지 않았습니다. 규칙 기반 계획 생성을 사용합니다."
            )

    def generate_smart_plan(
        self,
        user: User,
        monthly_income: Decimal,
        transaction_history: List[Dict] = None,
        user_profile: Dict = None,
    ) -> Dict:
        """
        사용자 맞춤형 스마트 계획 생성

        Args:
            user: 사용자 객체
            monthly_income: 월 소득
            transaction_history: 거래내역 (선택사항)
            user_profile: 사용자 프로필 정보 (선택사항)

        Returns:
            Dict: 맞춤형 계획 정보
        """
        try:
            # 1. 사용자 프로필 분석
            profile = self._analyze_user_profile(user, monthly_income, user_profile)

            # 2. 거래내역 분석 (있다면)
            spending_patterns = self._analyze_spending_patterns(
                transaction_history or []
            )

            # 3. AI 기반 계획 생성 시도
            ai_plan = self._generate_ai_plan(profile, spending_patterns, monthly_income)

            if ai_plan:
                return ai_plan

            # 4. AI 실패 시 규칙 기반 폴백
            logger.warning("AI 계획 생성 실패, 규칙 기반 폴백 사용")
            return self._generate_rule_based_plan(
                profile, spending_patterns, monthly_income
            )

        except Exception as e:
            logger.error(f"스마트 계획 생성 실패: {e}")
            return self._generate_fallback_plan(monthly_income)

    def generate_smart_plan_from_mydata(self, user: User) -> Dict:
        """마이데이터에서 자동으로 데이터를 가져와서 스마트 계획 생성"""
        try:
            # 1. 마이데이터에서 사용자 프로필 가져오기
            mydata_profile = self.mydata_client.get_user_profile(user)

            # 2. 마이데이터에서 월 소득 가져오기
            monthly_income = self.mydata_client.get_monthly_income(user)

            # 3. 마이데이터에서 거래내역 가져오기
            transaction_history = self.mydata_client.get_transaction_history(
                user, months=3
            )

            # 4. 마이데이터에서 소득 이력 가져오기 (12개월)
            income_history = self.mydata_client.get_income_history(user, months=12)

            # 5. 계좌 요약 정보 가져오기
            account_summary = self.mydata_client.get_account_summary(user)

            # 6. 대출 정보 가져오기
            loan_info = self.mydata_client.get_loan_info(user)

            # 7. 신용카드 정보 가져오기
            credit_card_info = self.mydata_client.get_credit_card_info(user)

            # 8. 사용자 프로필 구성 (마이데이터 + 추가 정보)
            user_profile = {
                "age": mydata_profile.get("age", 25),
                "location": mydata_profile.get("region", "seoul"),
                "occupation": mydata_profile.get("employment", "freelancer"),
                "housing": mydata_profile.get("housing", "rent"),
                "has_children": mydata_profile.get("has_children", False),
                "account_summary": account_summary,
                "loan_info": loan_info,
                "credit_card_info": credit_card_info,
            }

            # 9. 스마트 계획 생성
            smart_plan = self.generate_smart_plan(
                user=user,
                monthly_income=monthly_income,
                transaction_history=transaction_history,
                user_profile=user_profile,
            )

            # 10. 마이데이터 정보 추가
            smart_plan["mydata_info"] = {
                "monthly_income": float(monthly_income),
                "income_history": [float(income) for income in income_history],
                "transaction_count": len(transaction_history),
                "account_balance": float(account_summary.get("total_balance", 0)),
                "loan_count": len(loan_info),
                "credit_card_count": len(credit_card_info),
                "data_source": "mydata_auto",
            }

            return smart_plan

        except Exception as e:
            logger.error(f"마이데이터 기반 계획 생성 실패: {e}")
            # 폴백: 기본 소득으로 계획 생성
            fallback_income = Decimal("3000000")
            return self._generate_fallback_plan(fallback_income)

    def _analyze_user_profile(
        self, user: User, monthly_income: Decimal, user_profile: Dict = None
    ) -> Dict:
        """사용자 프로필 분석"""

        # 기본 프로필 정보
        profile = {
            "age": getattr(user, "age", 25),
            "gender": getattr(user, "gender", "unknown"),
            "location": getattr(user, "location", "seoul"),
            "occupation": getattr(user, "occupation", "freelancer"),
            "monthly_income": float(monthly_income),
            "income_level": self._classify_income_level(monthly_income),
            "life_stage": self._determine_life_stage(getattr(user, "age", 25)),
        }

        # 사용자 제공 프로필 정보 병합
        if user_profile:
            profile.update(user_profile)

        # 추가 분석
        profile.update(
            {
                "is_youth": profile["age"] <= 34,
                "is_high_income": profile["income_level"] == "high",
                "needs_emergency_fund": profile["income_level"] in ["low", "medium"],
                "can_invest": profile["income_level"] in ["medium", "high"],
            }
        )

        return profile

    def _analyze_spending_patterns(self, transaction_history: List[Dict]) -> Dict:
        """거래내역 분석"""
        if not transaction_history:
            return self._get_default_spending_patterns()

        # 카테고리별 지출 분석
        category_spending = {}
        total_spending = 0

        for transaction in transaction_history:
            category = transaction.get("category", "기타")
            amount = float(transaction.get("amount", 0))

            if category not in category_spending:
                category_spending[category] = 0
            category_spending[category] += amount
            total_spending += amount

        # 비율 계산
        spending_ratios = {}
        if total_spending > 0:
            for category, amount in category_spending.items():
                spending_ratios[category] = (amount / total_spending) * 100

        return {
            "total_monthly_spending": total_spending,
            "category_spending": category_spending,
            "spending_ratios": spending_ratios,
            "top_categories": sorted(
                category_spending.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "has_irregular_spending": self._detect_irregular_spending(
                transaction_history
            ),
        }

    def _generate_ai_plan(
        self, profile: Dict, spending_patterns: Dict, monthly_income: Decimal
    ) -> Optional[Dict]:
        """AI 기반 계획 생성"""

        if not self.api_key or self.api_key == "your_huggingface_api_key_here":
            return None

        try:
            from huggingface_hub import InferenceClient

            client = InferenceClient(api_key=self.api_key)

            # 프롬프트 생성
            prompt = self._create_smart_plan_prompt(
                profile, spending_patterns, monthly_income
            )

            # AI 모델 호출 - 여러 방법 시도
            ai_text = None

            # 1) chat_completion 시도
            try:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000,
                    temperature=0.3,
                )
                if response and response.choices:
                    ai_text = response.choices[0].message.content
            except Exception as e:
                logger.warning(f"chat_completion 실패: {e}")

                # 2) text_generation 폴백
                try:
                    ai_text = client.text_generation(
                        model=self.model_name,
                        prompt=prompt,
                        max_new_tokens=1000,
                        temperature=0.3,
                        return_full_text=False,
                    )
                except Exception as e2:
                    logger.warning(f"text_generation 실패: {e2}")

            if ai_text:
                return self._parse_ai_plan_response(ai_text, profile, monthly_income)

        except Exception as e:
            logger.error(f"AI 계획 생성 실패: {e}")

        return None

    def _create_smart_plan_prompt(
        self, profile: Dict, spending_patterns: Dict, monthly_income: Decimal
    ) -> str:
        """스마트 계획 생성 프롬프트"""

        age = profile.get("age", 25)
        location = profile.get("location", "seoul")
        occupation = profile.get("occupation", "freelancer")
        income_level = profile.get("income_level", "medium")
        is_youth = profile.get("is_youth", True)

        spending_info = ""
        if spending_patterns.get("total_monthly_spending", 0) > 0:
            spending_info = f"""
## 현재 지출 패턴
- 월 총 지출: {spending_patterns['total_monthly_spending']:,.0f}원
- 주요 지출 카테고리: {', '.join([f"{cat}({ratio:.1f}%)" for cat, ratio in list(spending_patterns['spending_ratios'].items())[:3]])}
- 불규칙 지출: {'있음' if spending_patterns.get('has_irregular_spending') else '없음'}
"""

        return f"""당신은 한국의 금융 전문가입니다. 사용자의 구체적인 상황을 분석하여 개인 맞춤형 자산 관리 계획을 생성하세요.

## 사용자 프로필
- **연령**: {age}세 ({'청년' if is_youth else '성인'})
- **직업**: {occupation}
- **지역**: {location}
- **월 소득**: {monthly_income:,.0f}원 ({income_level} 소득층)
- **생애주기**: {profile.get('life_stage', '청년기')}

{spending_info}

## 요청사항
위 정보를 바탕으로 다음을 포함한 맞춤형 계획을 생성하세요:

1. **저축 계획**: 소득 대비 적절한 저축률과 구체적 금액
2. **지출 최적화**: 현재 지출 패턴 분석 및 개선 방안
3. **청년 혜택**: 연령과 소득에 맞는 정부 지원 정책
4. **금융 상품**: 추천 상품과 가입 방법
5. **단계별 실행 계획**: 1개월, 3개월, 6개월 목표

**반드시 JSON 형식으로만 응답하세요:**

{{
  "savings_plan": {{
    "recommended_rate": 20.0,
    "monthly_amount": 500000,
    "breakdown": {{
      "emergency_fund": 300000,
      "investment": 200000
    }},
    "targets": {{
      "emergency_fund_6months": 1800000,
      "investment_1year": 2400000
    }}
  }},
  "expense_optimization": {{
    "current_spending": 2000000,
    "recommended_spending": 1800000,
    "savings_potential": 200000,
    "optimization_tips": [
      "구체적인 절약 방법 1",
      "구체적인 절약 방법 2"
    ]
  }},
  "youth_benefits": [
    {{
      "name": "청년도약계좌",
      "description": "정부 기여금과 우대금리 혜택",
      "monthly_contribution": 50000,
      "government_match": 30000,
      "eligibility": "만 19-34세",
      "application_link": "https://youthaccount.moef.go.kr"
    }}
  ],
  "financial_products": [
    {{
      "name": "추천 상품명",
      "type": "적금/대출/카드",
      "reason": "추천 이유",
      "monthly_amount": 100000,
      "benefits": ["혜택 1", "혜택 2"]
    }}
  ],
  "action_plan": {{
    "1_month": [
      "1개월 내 실행할 구체적 행동"
    ],
    "3_months": [
      "3개월 내 달성할 목표"
    ],
    "6_months": [
      "6개월 내 달성할 목표"
    ]
  }},
  "summary": "전체 계획의 핵심 요약"
}}

**중요**: 모든 수치는 사용자의 실제 소득({monthly_income:,.0f}원)에 맞는 현실적인 금액으로 설정하세요."""

    def _parse_ai_plan_response(
        self, ai_text: str, profile: Dict, monthly_income: Decimal
    ) -> Optional[Dict]:
        """AI 응답 파싱"""
        try:
            # JSON 추출
            import re

            json_match = re.search(r"\{.*\}", ai_text, re.DOTALL)
            if not json_match:
                return None

            json_str = json_match.group()
            plan_data = json.loads(json_str)

            # 데이터 검증 및 보정
            return self._validate_and_correct_plan(plan_data, profile, monthly_income)

        except Exception as e:
            logger.error(f"AI 응답 파싱 실패: {e}")
            return None

    def _validate_and_correct_plan(
        self, plan_data: Dict, profile: Dict, monthly_income: Decimal
    ) -> Dict:
        """계획 데이터 검증 및 보정"""

        # 기본 구조 보장
        validated_plan = {
            "savings_plan": plan_data.get("savings_plan", {}),
            "expense_optimization": plan_data.get("expense_optimization", {}),
            "youth_benefits": plan_data.get("youth_benefits", []),
            "financial_products": plan_data.get("financial_products", []),
            "action_plan": plan_data.get("action_plan", {}),
            "summary": plan_data.get("summary", ""),
            "generated_by": "ai",
        }

        # 저축 계획 검증
        savings_plan = validated_plan["savings_plan"]
        if not savings_plan.get("recommended_rate"):
            savings_plan["recommended_rate"] = self._calculate_optimal_savings_rate(
                profile
            )

        if not savings_plan.get("monthly_amount"):
            savings_plan["monthly_amount"] = float(monthly_income) * (
                savings_plan["recommended_rate"] / 100
            )

        # 청년 혜택 필터링
        if profile.get("is_youth"):
            validated_plan["youth_benefits"] = self._filter_youth_benefits(
                validated_plan["youth_benefits"], profile
            )

        return validated_plan

    def _generate_rule_based_plan(
        self, profile: Dict, spending_patterns: Dict, monthly_income: Decimal
    ) -> Dict:
        """규칙 기반 계획 생성"""

        income = float(monthly_income)
        age = profile.get("age", 25)
        is_youth = profile.get("is_youth", True)

        # 저축 계획
        savings_rate = self._calculate_optimal_savings_rate(profile)
        monthly_savings = income * (savings_rate / 100)

        savings_plan = {
            "recommended_rate": savings_rate,
            "monthly_amount": monthly_savings,
            "breakdown": {
                "emergency_fund": monthly_savings * 0.6,
                "investment": monthly_savings * 0.4,
            },
            "targets": {
                "emergency_fund_6months": monthly_savings * 0.6 * 6,
                "investment_1year": monthly_savings * 0.4 * 12,
            },
        }

        # 지출 최적화
        current_spending = spending_patterns.get("total_monthly_spending", income * 0.7)
        recommended_spending = income * 0.6  # 소득의 60%
        savings_potential = max(0, current_spending - recommended_spending)

        expense_optimization = {
            "current_spending": current_spending,
            "recommended_spending": recommended_spending,
            "savings_potential": savings_potential,
            "optimization_tips": self._generate_optimization_tips(
                profile, spending_patterns
            ),
        }

        # 청년 혜택
        youth_benefits = []
        if is_youth:
            youth_benefits = self._get_youth_benefits(profile, income)

        # 금융 상품 추천
        financial_products = self._recommend_financial_products(profile, income)

        # 실행 계획
        action_plan = self._create_action_plan(profile, income, savings_rate)

        return {
            "savings_plan": savings_plan,
            "expense_optimization": expense_optimization,
            "youth_benefits": youth_benefits,
            "financial_products": financial_products,
            "action_plan": action_plan,
            "summary": self._generate_plan_summary(profile, income, savings_rate),
            "generated_by": "rule_based",
        }

    def _generate_fallback_plan(self, monthly_income: Decimal) -> Dict:
        """최종 폴백 계획"""
        income = float(monthly_income)

        return {
            "savings_plan": {
                "recommended_rate": 20.0,
                "monthly_amount": income * 0.2,
                "breakdown": {
                    "emergency_fund": income * 0.12,
                    "investment": income * 0.08,
                },
                "targets": {
                    "emergency_fund_6months": income * 0.12 * 6,
                    "investment_1year": income * 0.08 * 12,
                },
            },
            "expense_optimization": {
                "current_spending": income * 0.7,
                "recommended_spending": income * 0.6,
                "savings_potential": income * 0.1,
                "optimization_tips": [
                    "고정비 절약: 통신비, 보험료 재검토",
                    "변동비 관리: 외식비, 쇼핑비 계획적 사용",
                    "할인 혜택 활용: 청년 할인, 지역 상품권 등",
                ],
            },
            "youth_benefits": [
                {
                    "name": "청년도약계좌",
                    "description": "정부 기여금과 우대금리로 목돈 마련",
                    "monthly_contribution": 50000,
                    "government_match": 30000,
                    "eligibility": "만 19-34세",
                    "application_link": "https://youthaccount.moef.go.kr",
                }
            ],
            "financial_products": [
                {
                    "name": "고금리 자유적금",
                    "type": "적금",
                    "reason": "비상자금 마련에 적합",
                    "monthly_amount": int(income * 0.1),
                    "benefits": ["높은 금리", "자유로운 입출금"],
                }
            ],
            "action_plan": {
                "1_month": ["비상자금 자동이체 설정", "월 예산 계획 수립"],
                "3_months": ["청년도약계좌 가입", "지출 패턴 분석 및 최적화"],
                "6_months": ["비상자금 3개월치 마련", "투자 상품 검토 및 가입"],
            },
            "summary": f"월 {income:,.0f}원 소득으로 안정적인 자산 관리를 위한 기본 계획입니다.",
            "generated_by": "fallback",
        }

    # 헬퍼 메서드들
    def _classify_income_level(self, monthly_income: Decimal) -> str:
        """소득 수준 분류"""
        income = float(monthly_income)
        if income < 2000000:
            return "low"
        elif income < 4000000:
            return "medium"
        elif income < 6000000:
            return "high"
        else:
            return "very_high"

    def _determine_life_stage(self, age: int) -> str:
        """생애주기 결정"""
        if age < 30:
            return "청년기"
        elif age < 40:
            return "성인 초기"
        elif age < 50:
            return "성인 중기"
        else:
            return "성인 후기"

    def _get_default_spending_patterns(self) -> Dict:
        """기본 지출 패턴"""
        return {
            "total_monthly_spending": 0,
            "category_spending": {},
            "spending_ratios": {},
            "top_categories": [],
            "has_irregular_spending": False,
        }

    def _detect_irregular_spending(self, transactions: List[Dict]) -> bool:
        """불규칙 지출 감지"""
        if len(transactions) < 10:
            return False

        amounts = [float(t.get("amount", 0)) for t in transactions]
        if not amounts:
            return False

        # 표준편차 계산으로 변동성 측정
        mean_amount = sum(amounts) / len(amounts)
        variance = sum((x - mean_amount) ** 2 for x in amounts) / len(amounts)
        std_dev = variance**0.5

        # 변동계수가 0.5 이상이면 불규칙 지출로 판단
        return (std_dev / mean_amount) > 0.5 if mean_amount > 0 else False

    def _calculate_optimal_savings_rate(self, profile: Dict) -> float:
        """최적 저축률 계산"""
        age = profile.get("age", 25)
        income_level = profile.get("income_level", "medium")

        base_rate = 20.0

        # 연령별 조정
        if age < 30:
            base_rate = 15.0  # 청년기는 낮은 저축률
        elif age > 40:
            base_rate = 25.0  # 중년기는 높은 저축률

        # 소득 수준별 조정
        if income_level == "low":
            base_rate *= 0.8  # 저소득층은 현실적 목표
        elif income_level == "high":
            base_rate *= 1.2  # 고소득층은 높은 목표

        return min(max(base_rate, 10.0), 40.0)  # 10-40% 범위

    def _filter_youth_benefits(self, benefits: List[Dict], profile: Dict) -> List[Dict]:
        """청년 혜택 필터링"""
        filtered = []
        for benefit in benefits:
            # 연령 조건 확인
            if "age" in benefit.get("eligibility", "").lower():
                if profile.get("age", 25) <= 34:
                    filtered.append(benefit)
            else:
                filtered.append(benefit)
        return filtered

    def _generate_optimization_tips(
        self, profile: Dict, spending_patterns: Dict
    ) -> List[str]:
        """최적화 팁 생성"""
        tips = []

        # 소득 수준별 팁
        if profile.get("income_level") == "low":
            tips.extend(
                [
                    "고정비 절약: 통신비, 보험료 재검토",
                    "할인 혜택 적극 활용: 청년 할인, 지역 상품권",
                    "가계부 작성으로 지출 패턴 파악",
                ]
            )
        else:
            tips.extend(
                [
                    "투자 상품 검토: ETF, 펀드 등 장기 투자",
                    "세제 혜택 활용: 연금저축, IRP 가입",
                    "신용관리: 카드 이용률 30% 이하 유지",
                ]
            )

        # 지출 패턴별 팁
        if spending_patterns.get("has_irregular_spending"):
            tips.append("불규칙 지출 관리: 월 예산 설정 및 준수")

        return tips[:3]  # 최대 3개

    def _get_youth_benefits(self, profile: Dict, income: float) -> List[Dict]:
        """청년 혜택 목록"""
        benefits = []

        if profile.get("age", 25) <= 34:
            benefits.append(
                {
                    "name": "청년도약계좌",
                    "description": "정부 기여금과 우대금리로 목돈 마련",
                    "monthly_contribution": min(700000, int(income * 0.2)),
                    "government_match": min(500000, int(income * 0.15)),
                    "eligibility": "만 19-34세",
                    "application_link": "https://youthaccount.moef.go.kr",
                }
            )

            if income < 3000000:
                benefits.append(
                    {
                        "name": "청년희망적금",
                        "description": "근로·사업소득 청년 비과세 및 저축장려금",
                        "monthly_contribution": 50000,
                        "government_match": 50000,
                        "eligibility": "만 19-34세, 소득요건",
                        "application_link": "https://www.fss.or.kr",
                    }
                )

        return benefits

    def _recommend_financial_products(self, profile: Dict, income: float) -> List[Dict]:
        """금융 상품 추천"""
        products = []

        # 소득 수준별 추천
        if profile.get("income_level") == "low":
            products.append(
                {
                    "name": "고금리 자유적금",
                    "type": "적금",
                    "reason": "비상자금 마련에 적합한 안전한 상품",
                    "monthly_amount": int(income * 0.1),
                    "benefits": ["높은 금리", "자유로운 입출금", "소액 가입 가능"],
                }
            )
        else:
            products.append(
                {
                    "name": "연금저축",
                    "type": "연금",
                    "reason": "세제 혜택과 장기 자산 형성",
                    "monthly_amount": int(income * 0.1),
                    "benefits": ["세액공제", "장기 수익", "은퇴 준비"],
                }
            )

        return products

    def _create_action_plan(
        self, profile: Dict, income: float, savings_rate: float
    ) -> Dict:
        """실행 계획 생성"""
        monthly_savings = int(income * (savings_rate / 100))

        return {
            "1_month": [
                f"비상자금 자동이체 설정 (월 {monthly_savings:,}원)",
                "월 예산 계획 수립 및 가계부 작성",
            ],
            "3_months": ["청년도약계좌 가입 및 정기 납입", "지출 패턴 분석 및 최적화"],
            "6_months": [
                f"비상자금 {int(monthly_savings * 3):,}원 마련",
                "투자 상품 검토 및 가입",
            ],
        }

    def _generate_plan_summary(
        self, profile: Dict, income: float, savings_rate: float
    ) -> str:
        """계획 요약 생성"""
        age = profile.get("age", 25)
        monthly_savings = int(income * (savings_rate / 100))

        return f"""
{age}세 {profile.get('occupation', '프리랜서')}를 위한 맞춤형 자산 관리 계획입니다.

📊 **핵심 지표**
- 월 소득: {income:,.0f}원
- 권장 저축률: {savings_rate:.0f}%
- 월 저축 목표: {monthly_savings:,}원

🎯 **주요 목표**
- 6개월 내 비상자금 마련
- 청년 혜택 최대 활용
- 장기 자산 형성 기반 구축

💡 **핵심 전략**
- 자동이체를 통한 저축 습관 형성
- 지출 최적화로 추가 자금 확보
- 정부 지원 정책 적극 활용
        """.strip()
