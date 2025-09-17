"""
AI 기반 소득 예측 및 코칭 서비스.
Llama 3.1 8B 모델을 활용한 프리랜서 소득 예측/동적 플랜/맞춤 코칭 제공.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.models import User
from huggingface_hub import InferenceClient

from .models import CreditScoreSnapshot
from .mydata import MyDataClient

logger = logging.getLogger(__name__)


class FreelancerIncomePredictor:
    """프리랜서 소득 예측 AI 서비스"""

    def __init__(self):
        self.api_key = settings.HF_API_KEY
        self.model_name = settings.AI_MODEL_NAME
        self.client = None

        # API 키가 유효한지 확인
        if self.api_key and self.api_key != "your_huggingface_api_key_here":
            try:
                self.client = InferenceClient(api_key=self.api_key)
                logger.info(f"AI 서비스 초기화 완료: {self.model_name}")
            except Exception as e:
                logger.error(f"AI 서비스 초기화 실패: {e}")
                self.client = None
        else:
            logger.warning(
                "유효한 Hugging Face API 키가 설정되지 않았습니다. 통계 기반 폴백을 사용합니다."
            )

    def predict_income(
        self, monthly_incomes: List[Decimal], income_type: str = "freelance"
    ) -> Dict:
        """
        AI 기반 소득 예측

        Args:
            monthly_incomes: 최근 12개월 소득 데이터
            income_type: 소득 유형 (freelance, business, employee, mixed)

        Returns:
            Dict: 예측 결과 (predicted_monthly, predicted_yearly, confidence, volatility, seasonal_analysis, risk_factors)
        """

        # 1. AI 모델을 통한 예측 시도
        ai_result = self._predict_with_llama(monthly_incomes, income_type)
        if ai_result:
            return ai_result

        # 2. AI 실패 시 통계 기반 폴백
        logger.warning("AI 예측 실패, 통계 기반 폴백 사용")
        return self._predict_with_statistics(monthly_incomes, income_type)

    def _predict_with_llama(
        self, monthly_incomes: List[Decimal], income_type: str
    ) -> Optional[Dict]:
        """Llama 3.1 8B 모델을 사용한 소득 예측"""

        if not self.client:
            return None

        # 소득 데이터 전처리
        try:
            incomes_list = [float(income) for income in monthly_incomes]
            valid_incomes = [income for income in incomes_list if income > 0]
        except Exception:
            return None

        if not valid_incomes:
            return None

        # 프롬프트 생성
        prompt = self._create_freelancer_prompt(incomes_list, income_type)

        # 1) chat_completion 시도 (가장 안정적)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )
            if response and response.choices:
                ai_text = response.choices[0].message.content
                parsed = self._parse_ai_response(ai_text, valid_incomes)
                if parsed:
                    parsed["prediction_method"] = "ai_chat_completion"
                    return parsed
        except Exception as e:
            logger.debug(f"chat_completion 실패, conversational 폴백 시도: {str(e)}")

        # 2) conversational 폴백 시도
        try:
            conv_input = {
                "past_user_inputs": [],
                "generated_responses": [],
                "text": prompt,
            }
            cv_resp = self.client.conversational(
                model=self.model_name,
                inputs=conv_input,
                parameters={"temperature": 0.3, "max_new_tokens": 500},
            )
            cv_text = (
                cv_resp.get("generated_text")
                if isinstance(cv_resp, dict)
                else str(cv_resp)
            )
            cv_parsed = self._parse_ai_response(cv_text or "", valid_incomes)
            if cv_parsed:
                cv_parsed["prediction_method"] = "ai_conversational"
                return cv_parsed
        except Exception as e:
            logger.debug(f"conversational 실패, text_generation 폴백 시도: {str(e)}")

        # 3) text_generation 폴백 시도
        try:
            tg_resp = self.client.text_generation(
                model=self.model_name,
                prompt=prompt,
                max_new_tokens=500,
                temperature=0.3,
                return_full_text=False,
            )
            tg_parsed = self._parse_ai_response(tg_resp, valid_incomes)
            if tg_parsed:
                tg_parsed["prediction_method"] = "ai_text_generation"
                return tg_parsed
        except Exception as e:
            logger.debug(f"text_generation 실패: {str(e)}")

        return None

    def _create_freelancer_prompt(
        self, monthly_incomes: List[float], income_type: str
    ) -> str:
        """프리랜서 특화 프롬프트 생성"""

        income_type_korean = {
            "freelance": "프리랜서",
            "business": "사업자",
            "employee": "급여소득자",
            "mixed": "혼합소득",
        }.get(income_type, "프리랜서")

        prompt = f"""당신은 프리랜서 및 자영업자를 위한 전문 금융 분석가입니다. 
다음은 {income_type_korean}의 최근 12개월 소득 데이터입니다:

월별 소득 (단위: 원):
{self._format_income_data(monthly_incomes)}

다음 정보를 JSON 형식으로 분석해주세요:

1. predicted_monthly_income: 다음 달 예상 소득 (원)
2. predicted_yearly_income: 연간 예상 소득 (원)
3. confidence: 예측 신뢰도 (0-100)
4. volatility: 소득 변동성 지수 (0-100)
5. seasonal_analysis: 계절성 패턴 분석 (한국어)
6. risk_factors: 위험 요소들 (배열)
7. growth_trend: 성장 트렌드 (positive/stable/negative)
8. recommendations: 개선 권장사항 (배열)

프리랜서의 특성을 고려하여:
- 프로젝트 기반 소득의 불규칙성
- 계절적 변동성
- 시장 수요 변화
- 개인 역량 발전
- 네트워킹 효과

를 종합적으로 분석해주세요.

응답은 반드시 유효한 JSON 형식으로만 해주세요:"""

        return prompt

    def _format_income_data(self, monthly_incomes: List[float]) -> str:
        """소득 데이터를 읽기 쉬운 형식으로 포맷팅"""
        months = [
            "1월",
            "2월",
            "3월",
            "4월",
            "5월",
            "6월",
            "7월",
            "8월",
            "9월",
            "10월",
            "11월",
            "12월",
        ]

        formatted = []
        for i, income in enumerate(monthly_incomes):
            month_name = months[i] if i < len(months) else f"{i+1}월"
            formatted.append(f"{month_name}: {income:,.0f}원")

        return "\n".join(formatted)

    def _parse_ai_response(
        self, response: str, valid_incomes: List[float]
    ) -> Optional[Dict]:
        """AI 응답을 파싱하여 예측 결과 추출"""

        try:
            # 응답 정리
            response = response.strip()

            # JSON 블록 추출
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()

            # JSON 객체 찾기
            if response.startswith("{"):
                end_brace = response.rfind("}")
                if end_brace != -1:
                    response = response[: end_brace + 1]

            # JSON 파싱 시도
            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                # JSON이 아닌 경우 텍스트에서 숫자 추출 시도
                return self._extract_from_text(response, valid_incomes)

            # 필수 필드 검증
            required_fields = [
                "predicted_monthly_income",
                "predicted_yearly_income",
                "confidence",
            ]
            if not all(field in data for field in required_fields):
                return self._extract_from_text(response, valid_incomes)

            # 데이터 검증 및 변환
            predicted_monthly = Decimal(str(data["predicted_monthly_income"]))
            predicted_yearly = Decimal(str(data["predicted_yearly_income"]))
            confidence = Decimal(str(data.get("confidence", 0)))
            volatility = Decimal(str(data.get("volatility", 0)))

            # 합리성 검증
            if predicted_monthly <= 0 or confidence < 0 or confidence > 100:
                return self._extract_from_text(response, valid_incomes)

            return {
                "predicted_monthly_income": predicted_monthly,
                "predicted_yearly_income": predicted_yearly,
                "confidence_level": confidence,
                "income_volatility": volatility,
                "seasonal_pattern": data.get(
                    "seasonal_analysis", "계절성 패턴 분석 없음"
                ),
                "risk_factors": data.get("risk_factors", []),
                "growth_trend": data.get("growth_trend", "stable"),
                "recommendations": data.get("recommendations", []),
            }

        except Exception as e:
            logger.error(f"AI 응답 파싱 실패: {e}")
            return self._extract_from_text(response, valid_incomes)

    def _extract_from_text(
        self, text: str, valid_incomes: List[float]
    ) -> Optional[Dict]:
        """텍스트에서 숫자 정보 추출"""
        import re

        try:
            # 숫자 추출
            numbers = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)
            if not numbers:
                return None

            # 평균 소득 계산
            avg_income = sum(valid_incomes) / len(valid_incomes)

            # 추출된 숫자 중 합리적인 범위의 것 선택
            reasonable_numbers = []
            for num_str in numbers:
                try:
                    num = float(num_str.replace(",", ""))
                    if 100000 <= num <= avg_income * 3:  # 합리적인 범위
                        reasonable_numbers.append(num)
                except ValueError:
                    continue

            if reasonable_numbers:
                predicted_monthly = Decimal(str(reasonable_numbers[0]))
                confidence = Decimal("75")  # 기본 신뢰도
            else:
                predicted_monthly = Decimal(str(avg_income))
                confidence = Decimal("60")

            return {
                "predicted_monthly_income": predicted_monthly,
                "predicted_yearly_income": predicted_monthly * 12,
                "confidence_level": confidence,
                "income_volatility": Decimal("15"),
                "seasonal_pattern": "AI 분석 결과",
                "risk_factors": ["AI 응답 파싱 제한"],
                "growth_trend": "stable",
                "recommendations": ["정확한 분석을 위해 더 많은 데이터가 필요합니다"],
            }
        except Exception as e:
            logger.error(f"텍스트 추출 실패: {e}")
            return None

    def _predict_with_statistics(
        self, monthly_incomes: List[Decimal], income_type: str
    ) -> Dict:
        """통계 기반 폴백 예측"""

        valid_incomes = [income for income in monthly_incomes if income > 0]

        if not valid_incomes:
            return {
                "predicted_monthly_income": Decimal(0),
                "predicted_yearly_income": Decimal(0),
                "confidence_level": Decimal(0),
                "income_volatility": Decimal(0),
                "seasonal_pattern": "데이터 부족",
                "risk_factors": ["소득 데이터 부족"],
                "growth_trend": "unknown",
                "recommendations": ["소득 데이터를 더 많이 수집해주세요"],
                "prediction_method": "statistical_fallback",
            }

        # 기본 통계 계산
        mean_income = sum(valid_incomes) / len(valid_incomes)

        # 변동성 계산 (표준편차를 평균 대비 백분율로 변환: 0~100)
        if len(valid_incomes) > 1:
            variance = sum((income - mean_income) ** 2 for income in valid_incomes) / (
                len(valid_incomes) - 1
            )
            stddev = variance.sqrt()
            volatility = (
                (stddev / mean_income * Decimal("100"))
                if mean_income > 0
                else Decimal("0")
            )
        else:
            volatility = Decimal("0")
        # 0~100 범위로 클램프 및 소수 2자리로 정규화
        if volatility < 0:
            volatility = Decimal("0")
        if volatility > 100:
            volatility = Decimal("100")
        volatility = volatility.quantize(Decimal("0.01"))

        # 계절성 분석
        seasonal_analysis = self._analyze_seasonality(monthly_incomes)

        # 성장 트렌드 분석
        growth_trend = self._analyze_growth_trend(valid_incomes)

        # 신뢰도 계산
        confidence = self._calculate_confidence(valid_incomes, volatility, mean_income)

        # 위험 요소 분석
        risk_factors = self._identify_risk_factors(
            valid_incomes, volatility, mean_income
        )

        # 권장사항 생성
        recommendations = self._generate_recommendations(
            valid_incomes, volatility, growth_trend
        )

        # 예측 소득 계산 (가중 평균 + 트렌드 고려)
        predicted_monthly = self._calculate_predicted_income(
            valid_incomes, growth_trend
        )

        return {
            "predicted_monthly_income": predicted_monthly,
            "predicted_yearly_income": predicted_monthly * 12,
            "confidence_level": confidence,
            "income_volatility": volatility,
            "seasonal_pattern": seasonal_analysis,
            "risk_factors": risk_factors,
            "growth_trend": growth_trend,
            "recommendations": recommendations,
            "prediction_method": "statistical_fallback",
        }

    def _analyze_seasonality(self, monthly_incomes: List[Decimal]) -> str:
        """계절성 패턴 분석"""
        monthly_averages = {}
        months = [
            "1월",
            "2월",
            "3월",
            "4월",
            "5월",
            "6월",
            "7월",
            "8월",
            "9월",
            "10월",
            "11월",
            "12월",
        ]

        for i, income in enumerate(monthly_incomes):
            if income > 0:
                month_name = months[i] if i < len(months) else f"{i+1}월"
                if month_name not in monthly_averages:
                    monthly_averages[month_name] = []
                monthly_averages[month_name].append(income)

        if not monthly_averages:
            return "계절성 패턴 분석 불가"

        analysis = "계절성 분석: "
        for month in sorted(monthly_averages.keys()):
            avg = sum(monthly_averages[month]) / len(monthly_averages[month])
            analysis += f"{month} 평균 {avg:,.0f}원, "

        return analysis.rstrip(", ")

    def _analyze_growth_trend(self, valid_incomes: List[Decimal]) -> str:
        """성장 트렌드 분석"""
        if len(valid_incomes) < 3:
            return "stable"

        # 최근 3개월 vs 이전 3개월 비교
        recent_avg = sum(valid_incomes[-3:]) / 3
        older_avg = (
            sum(valid_incomes[:-3]) / (len(valid_incomes) - 3)
            if len(valid_incomes) > 3
            else recent_avg
        )

        growth_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0

        if growth_rate > 0.1:  # 10% 이상 증가
            return "positive"
        elif growth_rate < -0.1:  # 10% 이상 감소
            return "negative"
        else:
            return "stable"

    def _calculate_confidence(
        self, valid_incomes: List[Decimal], volatility: Decimal, mean_income: Decimal
    ) -> Decimal:
        """신뢰도 계산"""
        # 모든 계산은 Decimal로 일관 처리
        from decimal import Decimal as D

        data_quality = D(str(min(len(valid_incomes) / 12, 1.0)))  # 0~1
        if mean_income > 0:
            vf = D("1") - (volatility / mean_income)
            # 하한 0, 상한 1
            volatility_factor = max(D("0"), min(D("1"), vf))
        else:
            volatility_factor = D("0")

        confidence = (data_quality * D("0.6") + volatility_factor * D("0.4")) * D("100")
        # 소수점 2자리까지 정규화
        return confidence.quantize(D("0.01"))

    def _identify_risk_factors(
        self, valid_incomes: List[Decimal], volatility: Decimal, mean_income: Decimal
    ) -> List[str]:
        """위험 요소 식별"""
        risk_factors = []

        if volatility > mean_income * Decimal("0.3"):
            risk_factors.append("높은 소득 변동성")

        if len(valid_incomes) < 6:
            risk_factors.append("부족한 소득 이력")

        if mean_income < Decimal("2000000"):  # 200만원 미만
            risk_factors.append("낮은 평균 소득")

        # 급격한 하락 패턴 체크
        if len(valid_incomes) >= 3:
            recent_trend = sum(valid_incomes[-3:]) / 3
            older_trend = (
                sum(valid_incomes[:-3]) / (len(valid_incomes) - 3)
                if len(valid_incomes) > 3
                else recent_trend
            )
            if recent_trend < older_trend * Decimal("0.8"):
                risk_factors.append("최근 소득 하락 추세")

        return risk_factors

    def _generate_recommendations(
        self, valid_incomes: List[Decimal], volatility: Decimal, growth_trend: str
    ) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []

        if volatility > sum(valid_incomes) / len(valid_incomes) * Decimal("0.3"):
            recommendations.append("소득 안정화를 위한 다각화 전략 수립")

        if growth_trend == "negative":
            recommendations.append("소득 증대를 위한 새로운 수익원 개발")

        if len(valid_incomes) < 6:
            recommendations.append("소득 데이터 지속적 기록으로 예측 정확도 향상")

        recommendations.extend(
            [
                "비상금 확보를 통한 소득 변동성 대비",
                "정기적인 자산 관리 플랜 검토 및 조정",
            ]
        )

        return recommendations

    def _calculate_predicted_income(
        self, valid_incomes: List[Decimal], growth_trend: str
    ) -> Decimal:
        """예측 소득 계산"""
        if len(valid_incomes) >= 3:
            # 최근 3개월에 더 높은 가중치
            recent_weight = Decimal("0.6")
            older_weight = Decimal("0.4")

            recent_avg = sum(valid_incomes[-3:]) / 3
            older_avg = (
                sum(valid_incomes[:-3]) / (len(valid_incomes) - 3)
                if len(valid_incomes) > 3
                else recent_avg
            )

            base_prediction = recent_avg * recent_weight + older_avg * older_weight

            # 성장 트렌드 반영
            if growth_trend == "positive":
                return base_prediction * Decimal("1.05")  # 5% 증가
            elif growth_trend == "negative":
                return base_prediction * Decimal("0.95")  # 5% 감소
            else:
                return base_prediction
        else:
            return sum(valid_incomes) / len(valid_incomes)


class DynamicPlanGenerator:
    """동적 자산관리 플랜 생성기"""

    def __init__(
        self,
        income_predictor: FreelancerIncomePredictor,
        mydata: MyDataClient | None = None,
    ):
        self.income_predictor = income_predictor
        self.mydata = mydata or MyDataClient()

    def generate_adaptive_plan(
        self,
        prediction_result: Dict,
        user_preferences: Dict,
        user: Optional[User] = None,
    ) -> Dict:
        """예측 결과를 바탕으로 한 동적 플랜 생성"""

        predicted_income = prediction_result["predicted_monthly_income"]
        volatility = prediction_result["income_volatility"]
        risk_factors = prediction_result["risk_factors"]
        growth_trend = prediction_result["growth_trend"]

        # 위험도 기반 플랜 유형 결정
        plan_type = self._determine_plan_type(
            volatility, risk_factors, user_preferences
        )

        # 동적 비율 계산
        ratios = self._calculate_dynamic_ratios(volatility, growth_trend, plan_type)

        # 월별 계획 생성
        # 고정 지출 (마이데이터 가정) 적용
        if user is not None and self.mydata:
            fixed_expenses = self.mydata.get_fixed_expenses(user)
        else:
            fixed_expenses = self._fetch_fixed_expenses()

        monthly_plans = self._generate_monthly_plans(
            predicted_income, ratios, growth_trend, fixed_expenses
        )

        return {
            "plan_type": plan_type,
            "ratios": ratios,
            "monthly_plans": monthly_plans,
            "risk_assessment": self._assess_plan_risk(volatility, risk_factors),
            "adaptation_strategy": self._create_adaptation_strategy(
                growth_trend, risk_factors
            ),
        }

    def _determine_plan_type(
        self, volatility: Decimal, risk_factors: List[str], user_preferences: Dict
    ) -> str:
        """위험도 기반 플랜 유형 결정"""
        risk_score = len(risk_factors)

        if volatility > Decimal("30") or risk_score >= 3:
            return "conservative"  # 보수형
        elif volatility > Decimal("15") or risk_score >= 2:
            return "moderate"  # 균형형
        else:
            return "aggressive"  # 공격형

    def _calculate_dynamic_ratios(
        self, volatility: Decimal, growth_trend: str, plan_type: str
    ) -> Dict:
        """동적 비율 계산"""
        base_ratios = {
            "conservative": {
                "savings": Decimal("0.25"),
                "investment": Decimal("0.15"),
                "housing": Decimal("0.25"),
                "food": Decimal("0.15"),
                "transport": Decimal("0.08"),
                "healthcare": Decimal("0.05"),
                "entertainment": Decimal("0.05"),
                "other": Decimal("0.02"),
            },
            "moderate": {
                "savings": Decimal("0.20"),
                "investment": Decimal("0.20"),
                "housing": Decimal("0.30"),
                "food": Decimal("0.15"),
                "transport": Decimal("0.10"),
                "healthcare": Decimal("0.05"),
                "entertainment": Decimal("0.10"),
                "other": Decimal("0.05"),
            },
            "aggressive": {
                "savings": Decimal("0.15"),
                "investment": Decimal("0.25"),
                "housing": Decimal("0.30"),
                "food": Decimal("0.15"),
                "transport": Decimal("0.10"),
                "healthcare": Decimal("0.05"),
                "entertainment": Decimal("0.10"),
                "other": Decimal("0.05"),
            },
        }

        ratios = base_ratios[plan_type].copy()

        # 변동성에 따른 조정
        if volatility > Decimal("30"):
            ratios["savings"] += Decimal("0.05")  # 저축률 증가
            ratios["investment"] -= Decimal("0.05")  # 투자 비율 감소

        # 성장 트렌드에 따른 조정
        if growth_trend == "positive":
            ratios["investment"] += Decimal("0.05")  # 투자 비율 증가
        elif growth_trend == "negative":
            ratios["savings"] += Decimal("0.05")  # 저축률 증가

        # 프리랜서/청년 특성 반영: 고정비 절감(주거)과 비상금/투자 균형 강화
        # 청년(<=34) & 프리랜서일 가능성이 높다고 가정하여 기본 주거비 가중치를 낮추고
        # 저축 2~5%p 상향, 투자는 변동성에 따라 0~3%p 조정
        # 실제 적용은 MyData의 employment/age를 직접 사용할 수도 있으나, 간접 기본 강화
        try:
            # 청년/프리랜서 가정: 주거 가중치 소폭 하향
            ratios["housing"] = max(
                Decimal("0.20"), ratios["housing"] - Decimal("0.05")
            )
            # 저축 상향
            ratios["savings"] += Decimal("0.02")
            # 변동성 높으면 투자 소폭 낮춤, 낮으면 소폭 올림
            if volatility > Decimal("25"):
                ratios["investment"] = max(
                    Decimal("0.10"), ratios["investment"] - Decimal("0.03")
                )
            else:
                ratios["investment"] = ratios["investment"] + Decimal("0.02")
        except Exception:
            pass

        # 총합을 1.0으로 재정규화(과/미할당 방지)
        keys = [
            "savings",
            "investment",
            "housing",
            "food",
            "transport",
            "healthcare",
            "entertainment",
            "other",
        ]
        total = sum(ratios[k] for k in keys)
        if total != 0:
            for k in keys:
                ratios[k] = (ratios[k] / total).quantize(Decimal("0.0001"))

        return ratios

    def _generate_monthly_plans(
        self,
        predicted_income: Decimal,
        ratios: Dict,
        growth_trend: str,
        fixed_expenses: Dict,
    ) -> List[Dict]:
        """월별 계획 생성"""
        monthly_plans = []

        for month in range(1, 13):
            # 계절성 고려한 소득 조정
            seasonal_factor = self._get_seasonal_factor(month)
            monthly_income = predicted_income * seasonal_factor

            # 성장 트렌드 반영
            if growth_trend == "positive":
                monthly_income *= Decimal("1.01") ** month  # 월 1% 증가
            elif growth_trend == "negative":
                monthly_income *= Decimal("0.99") ** month  # 월 1% 감소

            # 고정 지출 합계 (주거/통신/공과금 등을 합산)
            fixed_total = sum(Decimal(str(v)) for v in fixed_expenses.values())

            # 저축/투자 우선 반영
            savings_amt = monthly_income * ratios["savings"]
            invest_amt = monthly_income * ratios["investment"]

            # 남는 예산: 소득 - (저축+투자) - 고정지출(주거/통신/공과금)
            housing_fixed = Decimal(str(fixed_expenses.get("housing", 0)))
            telecom_fixed = Decimal(str(fixed_expenses.get("telecom", 0)))
            utilities_fixed = Decimal(str(fixed_expenses.get("utilities", 0)))
            remaining = (
                monthly_income
                - savings_amt
                - invest_amt
                - housing_fixed
                - telecom_fixed
                - utilities_fixed
            )
            if remaining < 0:
                remaining = Decimal("0")

            # 변동 지출 비중대로 나누기
            var_keys = ["food", "transport", "healthcare", "entertainment", "other"]
            weight_sum = sum(Decimal(str(ratios[k])) for k in var_keys)
            if weight_sum > 0:
                food = remaining * Decimal(str(ratios["food"])) / weight_sum
                transport = remaining * Decimal(str(ratios["transport"])) / weight_sum
                healthcare = remaining * Decimal(str(ratios["healthcare"])) / weight_sum
                entertain = (
                    remaining * Decimal(str(ratios["entertainment"])) / weight_sum
                )
                other = remaining * Decimal(str(ratios["other"])) / weight_sum
            else:
                food = transport = healthcare = entertain = other = Decimal("0")

            plan = {
                "month": month,
                "expected_income": monthly_income,
                "savings": savings_amt,
                "investment": invest_amt,
                "housing": housing_fixed or monthly_income * ratios["housing"],
                "food": food,
                "transport": transport,
                "healthcare": healthcare,
                "entertainment": entertain,
                "other": other,
                "fixed_expenses_total": fixed_total,
                "telecom": telecom_fixed,
                "utilities": utilities_fixed,
            }

            monthly_plans.append(plan)

        return monthly_plans

    def _fetch_fixed_expenses(self) -> Dict:
        """마이데이터 고정지출 기본값(스텁)"""
        # DynamicPlanGenerator는 사용자 객체를 모름 → 기본값 유지
        return {"housing": 800000, "telecom": 70000, "utilities": 120000}

    def _get_seasonal_factor(self, month: int) -> Decimal:
        """계절성 팩터 계산"""
        # 프리랜서 특성상 연말/연초에 프로젝트가 많은 경향
        seasonal_factors = {
            1: 1.1,  # 1월: 신년 프로젝트
            2: 0.9,  # 2월: 설날 연휴
            3: 1.0,  # 3월: 정상
            4: 1.0,  # 4월: 정상
            5: 1.0,  # 5월: 정상
            6: 0.95,  # 6월: 하반기 준비
            7: 1.0,  # 7월: 정상
            8: 0.9,  # 8월: 여름휴가
            9: 1.05,  # 9월: 하반기 시작
            10: 1.1,  # 10월: 연말 프로젝트 시작
            11: 1.1,  # 11월: 연말 프로젝트
            12: 1.2,  # 12월: 연말 마무리
        }

        return Decimal(str(seasonal_factors.get(month, 1.0)))

    def _assess_plan_risk(self, volatility: Decimal, risk_factors: List[str]) -> Dict:
        """플랜 위험도 평가"""
        risk_score = len(risk_factors)

        if volatility > Decimal("30") or risk_score >= 3:
            risk_level = "높음"
        elif volatility > Decimal("15") or risk_score >= 2:
            risk_level = "보통"
        else:
            risk_level = "낮음"

        return {
            "level": risk_level,
            "factors": risk_factors,
            "mitigation_strategies": self._get_mitigation_strategies(risk_factors),
        }

    def _get_mitigation_strategies(self, risk_factors: List[str]) -> List[str]:
        """위험 완화 전략"""
        strategies = []

        for factor in risk_factors:
            if "변동성" in factor:
                strategies.append("다양한 수익원 개발로 소득 안정화")
            elif "이력" in factor:
                strategies.append("소득 데이터 지속적 기록 및 관리")
            elif "소득" in factor:
                strategies.append("스킬 업그레이드 및 새로운 시장 진출")
            elif "하락" in factor:
                strategies.append("비상금 확보 및 지출 최적화")

        return strategies

    def _create_adaptation_strategy(
        self, growth_trend: str, risk_factors: List[str]
    ) -> Dict:
        """적응 전략 생성"""
        strategy = {
            "review_frequency": "monthly",
            "adjustment_triggers": [],
            "action_plans": [],
        }

        if growth_trend == "positive":
            strategy["adjustment_triggers"].append("소득 증가 시 투자 비율 확대")
            strategy["action_plans"].append("성장 기회 확대를 위한 추가 투자 검토")
        elif growth_trend == "negative":
            strategy["adjustment_triggers"].append("소득 감소 시 지출 최적화")
            strategy["action_plans"].append("비상금 확보 및 필수 지출 우선순위 설정")

        if len(risk_factors) > 2:
            strategy["review_frequency"] = "weekly"
            strategy["adjustment_triggers"].append("높은 변동성 감지 시 플랜 재검토")

        return strategy

    # --- 신용 점수 분석 & 시뮬레이션 ---
    def analyze_credit_factors(self, snapshot: CreditScoreSnapshot) -> Dict:
        """신용점수 영향 요인 분석 (간단 가중치 모델)

        - 가용한 데이터: 이용률, 연체율(시간 내 결제 비율), 신용연령, 최근 12개월 조회, 크레딧 믹스
        - 점수 기여도(가중치):
            이용률 35%, 결제성실 30%, 신용연령 15%, 조회건수 10%, 믹스 10%
        """
        from decimal import Decimal as D

        utilization = snapshot.utilization_rate  # 0~100 낮을수록 좋음
        ontime = snapshot.on_time_payment_ratio  # 0~100 높을수록 좋음
        age = snapshot.credit_age_months
        inquiries = snapshot.hard_inquiries_12m
        mix = snapshot.credit_mix_score  # 0~100 높을수록 좋음

        # 0~100 스케일의 서브 스코어로 정규화
        utilization_score = max(D("0"), D("100") - utilization)  # 0 이용률=100점
        payment_score = ontime  # 이미 0~100
        age_score = D(min(100, age / 12 * 10))  # 10년(120개월) 이상이면 만점 가정
        inquiries_score = max(D("0"), D("100") - D(inquiries) * D("20"))  # 1건당 -20점
        mix_score = mix

        # 가중 합산 → 0~100
        total = (
            utilization_score * D("0.35")
            + payment_score * D("0.30")
            + age_score * D("0.15")
            + inquiries_score * D("0.10")
            + mix_score * D("0.10")
        ).quantize(D("0.01"))

        # 권장 액션
        actions: List[str] = []
        if utilization > 30:
            actions.append("카드 사용액을 한도 대비 30% 이하로 유지")
        if ontime < 98:
            actions.append("모든 대금 자동이체 설정으로 연체 방지")
        if age < 36:
            actions.append("오래된 계좌 유지로 신용연령 축적")
        if inquiries > 1:
            actions.append("12개월 내 신용조회/신규대출 최소화")
        if mix < 50:
            actions.append(
                "신용카드/할부/소액대출 등 포트폴리오 균형 개선(무리한 개설 금지)"
            )

        return {
            "factor_score": float(total),
            "recommendations": actions,
            "breakdown": {
                "utilization_score": float(utilization_score),
                "payment_score": float(payment_score),
                "age_score": float(age_score),
                "inquiries_score": float(inquiries_score),
                "mix_score": float(mix_score),
            },
        }

    def simulate_credit_improvement(
        self, snapshot: CreditScoreSnapshot, months: int = 6
    ) -> Dict:
        """신용점수 개선 시뮬레이션 (간단 선형 개선 가정)

        - 매월 이용률 2%p 감소, 연체 없음 가정(ontime +0.2%p, 100 상한),
          3개월마다 inquiries 영향 10점 회복, 크레딧 믹스 소폭(+1p) 개선 가정
        - 결과: 예상 점수 변화량 및 목표 달성 가능성
        """
        from decimal import Decimal as D

        sim = CreditScoreSnapshot(
            user=snapshot.user,
            score=snapshot.score,
            utilization_rate=snapshot.utilization_rate,
            on_time_payment_ratio=snapshot.on_time_payment_ratio,
            credit_age_months=snapshot.credit_age_months,
            hard_inquiries_12m=snapshot.hard_inquiries_12m,
            credit_mix_score=snapshot.credit_mix_score,
        )

        history = []
        for m in range(1, months + 1):
            sim.credit_age_months += 1
            sim.utilization_rate = max(D("0"), sim.utilization_rate - D("2"))
            sim.on_time_payment_ratio = min(
                D("100"), sim.on_time_payment_ratio + D("0.2")
            )
            if m % 3 == 0 and sim.hard_inquiries_12m > 0:
                sim.hard_inquiries_12m -= 1
            sim.credit_mix_score = min(100, sim.credit_mix_score + 1)

            analysis = self.analyze_credit_factors(sim)
            # 100점 스케일을 950점 만점으로 매핑 (간단 비례)
            mapped_score = int(analysis["factor_score"] / 100 * 950)
            history.append({"month": m, "estimated_score": mapped_score})

        return {
            "months": months,
            "trajectory": history,
            "estimated_improvement": (
                history[-1]["estimated_score"] - snapshot.score if history else 0
            ),
        }

    # --- 금융상품 추천 (연령/소득/신용) ---
    def recommend_products(
        self,
        age: int,
        monthly_income: Decimal,
        credit_score: int,
        region: str = "",
        housing: str = "rent",  # rent | owner | family
        employment: str = "employee",  # employee | freelancer | student
        has_children: bool = False,
    ) -> List[Dict]:
        """연령, 소득, 신용, 주거/고용/지역 요인을 반영한 규칙 기반 추천.

        - 청년(만 19~34): 청년 전월세대출/청년희망적금/청년도약계좌 등
        - 소득 구간: < 250만원, 250~400, >400에 따라 예/적금/ETF/연금/신용카드 혜택 차등
        - 신용점수: 700+ 고신용, 600~699 중신용, 미만 저신용으로 카드/대출 권고 조정
        """
        recs: List[Dict] = []
        youth = age >= 19 and age <= 34
        income = float(monthly_income)

        def add(name, category, why, cautions=None, eligibility=None, link=None):
            recs.append(
                {
                    "name": name,
                    "category": category,
                    "why": why,
                    "cautions": cautions or "",
                    "eligibility": eligibility or "",
                    "link": link or "",
                }
            )

        if youth:
            add(
                "청년 전월세 보증금 대출",
                "대출",
                "보증금/월세 자금 저금리 지원",
                eligibility="만 19~34세, 무주택, 소득요건",
                link="https://www.gov.kr/",
            )
            add(
                "청년희망적금/청년도약계좌",
                "적금",
                "정부 우대금리 및 소득공제 혜택",
                eligibility="연령·소득 요건 충족 시",
                link="https://www.fss.or.kr/",
            )
        elif age >= 35 and age <= 49:
            add("신용/주택 대환 프로그램", "대출", "금리인상기 부담 완화(요건 충족 시)")
            add("연금저축/IRP 증액", "연금", "세액공제 극대화(중장기)")
        else:
            add("퇴직연금/연금저축 리밸런싱", "연금", "은퇴 준비 및 세제 혜택 최적화")

        # 고용상태 특화
        if employment == "freelancer":
            add(
                "종합소득세 절세 패키지",
                "세제",
                "IRP/연금저축으로 종소세 절감",
                eligibility="사업/프리랜서 소득자",
            )
            add(
                "선지급 카드/현금흐름 보조",
                "카드",
                "매출 변동성 대비, 수수료 유의",
                cautions="이용률 30% 룰 준수",
            )
        elif employment == "student":
            add("청년/대학생 특화 체크카드", "카드", "교통/통신/편의점 할인 중심")

        # 주거상태 특화
        if housing == "rent":
            add(
                "버팀목 전세자금대출",
                "대출",
                "보증금/월세 부담 경감",
                eligibility="무주택, 소득/보증금 요건",
            )
            add("주택청약통장", "예치", "내집 마련 준비, 가점 축적")
        elif housing == "owner":
            add(
                "주담대 금리갈아타기",
                "대출",
                "고정/혼합으로 갈아타기 검토",
                cautions="중도상환수수료 확인",
            )

        # 지역 특화 (지자체 청년 통장 등)
        if region:
            add(
                f"{region} 청년/신혼부부 통장/대출",
                "지자체",
                "지역 우대금리 및 매칭지원",
                eligibility=f"{region} 거주·재직 요건",
            )

        if income < 2500000:
            add(
                "고금리 자유적금",
                "적금",
                "소액도 복리효과로 안전하게 비상금 구축",
                eligibility="소득제한 없음",
            )
            add("체크카드 생활혜택", "카드", "통신/대중교통/편의점 위주 실질 할인")
        elif income <= 4000000:
            add("인덱스 ETF 적립", "투자", "분산투자 기반의 중위험/중수익 전략")
            add(
                "연금저축/IRP",
                "연금",
                "연말정산 세액공제 및 중장기 자산형성",
                eligibility="근로/사업 소득자 권장",
            )
        else:
            add("종합자산관리 CMA", "예치", "유동성+수익성 균형, 여유자금 운용")
            add(
                "해외/섹터 ETF 포트폴리오", "투자", "분산을 유지하되 초과수익 기회 탐색"
            )

        if credit_score < 600:
            add(
                "보증부 중금리 대환",
                "대출",
                "기존 고금리 대출의 금리 부담 완화",
                cautions="신규 다중채무 자제",
            )
        elif credit_score < 700:
            add(
                "체크카드 → 신용카드 점진 전환",
                "카드",
                "이용률 30% 이하 원칙으로 신용도 개선",
            )
        else:
            add(
                "프리미엄 신용카드(실속형)", "카드", "이용률 관리 전제 하에 혜택 극대화"
            )

        if has_children:
            add("아이행복/가족 특화 카드", "카드", "보육/의료/교육비 할인")
            add("보장성 보험 점검", "보장", "가계 리스크 관리(과보장 주의)")

        return recs
