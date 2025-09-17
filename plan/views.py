import json
import logging
import os
import statistics
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

from .ai_services import DynamicPlanGenerator, FreelancerIncomePredictor
from .coaching import PersonalizedCoach, PolicyAdvisor
from .models import CreditScoreSnapshot, FinancialPlan, IncomePrediction, MonthlyPlan
from .mydata import MyDataClient
from .smart_plan_generator import SmartPlanGenerator


def _safe_decimal(value, default="0"):
    """사용자 입력을 안전하게 Decimal로 변환.

    - 쉼표, 공백, 통화기호, 퍼센트 기호 제거
    - 비어있거나 변환 오류 시 기본값 반환
    """
    from decimal import Decimal, InvalidOperation

    if value is None:
        value = default
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal(str(default))
    if not isinstance(value, str):
        return Decimal(str(default))

    cleaned = (
        value.replace(",", "")
        .replace("%", "")
        .replace("원", "")
        .replace("₩", "")
        .strip()
    )
    if cleaned == "":
        cleaned = str(default)
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal(str(default))


def plan_home(request):
    """플랜 생성 메인 페이지"""
    return render(request, "plan/plan_home.html")


@login_required
def quick_start(request):
    """사용자 입력 없이 사전 저장된 12개월 소득으로 확인→생성 흐름"""
    if request.method == "POST":
        # 확인 완료 → 예측 계산 후 플랜 생성 페이지로 이동
        prediction_id = request.POST.get("prediction_id")
        prediction = get_object_or_404(
            IncomePrediction, id=prediction_id, user=request.user
        )

        incomes = [
            prediction.monthly_income_1,
            prediction.monthly_income_2,
            prediction.monthly_income_3,
            prediction.monthly_income_4,
            prediction.monthly_income_5,
            prediction.monthly_income_6,
            prediction.monthly_income_7,
            prediction.monthly_income_8,
            prediction.monthly_income_9,
            prediction.monthly_income_10,
            prediction.monthly_income_11,
            prediction.monthly_income_12,
        ]

        ai_predictor = FreelancerIncomePredictor()
        result = ai_predictor.predict_income(incomes, prediction.income_type)

        prediction.predicted_monthly_income = result["predicted_monthly_income"]
        prediction.predicted_yearly_income = result["predicted_yearly_income"]
        prediction.confidence_level = result["confidence_level"]
        prediction.income_volatility = result["income_volatility"]
        prediction.seasonal_pattern = result.get("seasonal_pattern", "")
        prediction.save()

        return redirect("plan:create_financial_plan", prediction_id=prediction.id)

    # GET: 사전 저장된(or 기본 시드) 데이터를 넣은 예측 레코드 생성 후 확인 화면 표시
    default_incomes = [
        1000000,
        1100000,
        1200000,
        1300000,
        1400000,
        1000000,
        1100000,
        900000,
        1200000,
        1500000,
        1600000,
        1400000,
    ]
    income_type = "freelance"

    # 기존 데이터에 접근하지 않고 새 레코드를 생성하여 안전 확보
    prediction = IncomePrediction.objects.create(
        user=request.user,
        income_type=income_type,
        monthly_income_1=_safe_decimal(default_incomes[0]),
        monthly_income_2=_safe_decimal(default_incomes[1]),
        monthly_income_3=_safe_decimal(default_incomes[2]),
        monthly_income_4=_safe_decimal(default_incomes[3]),
        monthly_income_5=_safe_decimal(default_incomes[4]),
        monthly_income_6=_safe_decimal(default_incomes[5]),
        monthly_income_7=_safe_decimal(default_incomes[6]),
        monthly_income_8=_safe_decimal(default_incomes[7]),
        monthly_income_9=_safe_decimal(default_incomes[8]),
        monthly_income_10=_safe_decimal(default_incomes[9]),
        monthly_income_11=_safe_decimal(default_incomes[10]),
        monthly_income_12=_safe_decimal(default_incomes[11]),
    )

    context = {
        "prediction": prediction,
        "incomes": default_incomes,
        "income_type": income_type,
    }
    return render(request, "plan/confirm_incomes.html", context)


@login_required
def income_prediction(request):
    """소득 예측 입력 및 생성"""
    if request.method == "POST":
        income_type = request.POST.get("income_type")

        # 과거 소득 데이터 수집
        monthly_incomes = []
        for i in range(1, 13):
            income = request.POST.get(f"monthly_income_{i}", "0")
            monthly_incomes.append(_safe_decimal(income, "0"))

        # 기존 레코드에 잘못 저장된 값으로 인해 조회 단계에서 오류가 발생할 수 있어
        # 사용자 기존 예측을 일괄 삭제 후 새로 생성한다(조회 없이 DELETE는 안전함).
        IncomePrediction.objects.filter(user=request.user).delete()
        prediction = IncomePrediction.objects.create(
            user=request.user, income_type=income_type
        )

        # 과거 소득 데이터 저장
        prediction.monthly_income_1 = monthly_incomes[0]
        prediction.monthly_income_2 = monthly_incomes[1]
        prediction.monthly_income_3 = monthly_incomes[2]
        prediction.monthly_income_4 = monthly_incomes[3]
        prediction.monthly_income_5 = monthly_incomes[4]
        prediction.monthly_income_6 = monthly_incomes[5]
        prediction.monthly_income_7 = monthly_incomes[6]
        prediction.monthly_income_8 = monthly_incomes[7]
        prediction.monthly_income_9 = monthly_incomes[8]
        prediction.monthly_income_10 = monthly_incomes[9]
        prediction.monthly_income_11 = monthly_incomes[10]
        prediction.monthly_income_12 = monthly_incomes[11]

        # AI 소득 예측 수행 (새로운 AI 서비스 사용)
        ai_predictor = FreelancerIncomePredictor()
        prediction_result = ai_predictor.predict_income(monthly_incomes, income_type)

        prediction.predicted_monthly_income = prediction_result[
            "predicted_monthly_income"
        ]
        prediction.predicted_yearly_income = prediction_result[
            "predicted_yearly_income"
        ]
        prediction.confidence_level = prediction_result["confidence_level"]
        prediction.income_volatility = prediction_result["income_volatility"]
        prediction.seasonal_pattern = prediction_result["seasonal_pattern"]

        prediction.save()

        messages.success(request, "소득 예측이 완료되었습니다!")
        return redirect("plan:create_financial_plan", prediction_id=prediction.id)

    return render(request, "plan/income_prediction.html")


@login_required
def create_financial_plan(request, prediction_id):
    """자산 관리 플랜 생성"""
    prediction = get_object_or_404(
        IncomePrediction, id=prediction_id, user=request.user
    )

    if request.method == "POST":
        plan_type = request.POST.get("plan_type")
        target_savings_rate = _safe_decimal(
            request.POST.get("target_savings_rate", "20"), "20"
        )
        emergency_fund_target = _safe_decimal(
            request.POST.get("emergency_fund_target", "0"), "0"
        )
        current_credit_score = int(request.POST.get("current_credit_score", 0))

        # 플랜 생성
        plan = FinancialPlan.objects.create(
            user=request.user,
            income_prediction=prediction,
            plan_type=plan_type,
            target_savings_rate=target_savings_rate,
            emergency_fund_target=emergency_fund_target,
            current_credit_score=current_credit_score,
        )

        # AI 기반 동적 플랜 생성
        ai_predictor = FreelancerIncomePredictor()
        plan_generator = DynamicPlanGenerator(ai_predictor, mydata=MyDataClient())

        # 예측 결과 재구성
        prediction_result = {
            "predicted_monthly_income": prediction.predicted_monthly_income,
            "income_volatility": prediction.income_volatility,
            "risk_factors": [],  # 모델에서 추출 필요
            "growth_trend": "stable",  # 기본값
        }

        # 사용자 선호도
        user_preferences = {
            "plan_type": plan_type,
            "target_savings_rate": target_savings_rate,
        }

        # 동적 플랜 생성 (사용자 전달 → MyData 고정지출 반영)
        dynamic_plan = plan_generator.generate_adaptive_plan(
            prediction_result, user_preferences, user=request.user
        )

        # 플랜 상세 정보 생성
        generate_detailed_plan(plan, prediction, dynamic_plan)

        messages.success(request, "자산 관리 플랜이 생성되었습니다!")
        return redirect("plan:plan_detail", plan_id=plan.id)

    return render(
        request,
        "plan/create_financial_plan.html",
        {
            "prediction": prediction,
            # 비상금 권장 범위 (월 소득의 3~6개월)
            "recommended_emergency_low": prediction.predicted_monthly_income
            * Decimal("3"),
            "recommended_emergency_high": prediction.predicted_monthly_income
            * Decimal("6"),
            "recommended_emergency_text": f"{int(prediction.predicted_monthly_income) * 3}원 ~ {int(prediction.predicted_monthly_income) * 6}원",
        },
    )


@login_required
def plan_detail(request, plan_id):
    """플랜 상세 보기"""
    plan = get_object_or_404(FinancialPlan, id=plan_id, user=request.user)
    monthly_plans = plan.monthly_plans.all()

    # 신용등급 백분율 (0~100)
    def _clamp_percent(value, max_value=950):
        try:
            pct = float(value) / float(max_value) * 100.0
            if pct < 0:
                return 0
            if pct > 100:
                return 100
            return round(pct, 2)
        except Exception:
            return 0

    current_credit_percent = _clamp_percent(plan.current_credit_score)
    target_credit_percent = _clamp_percent(plan.target_credit_score)
    try:
        confidence_display = round(float(plan.income_prediction.confidence_level), 1)
    except Exception:
        confidence_display = 0.0
    try:
        volatility_display = round(float(plan.income_prediction.income_volatility), 1)
    except Exception:
        volatility_display = 0.0

    return render(
        request,
        "plan/plan_detail.html",
        {
            "plan": plan,
            "monthly_plans": monthly_plans,
            "current_credit_percent": current_credit_percent,
            "target_credit_percent": target_credit_percent,
            "income_type_display": plan.income_prediction.get_income_type_display(),
            "confidence_display": confidence_display,
            "volatility_display": volatility_display,
        },
    )


@login_required
def credit_insights(request):
    """신용점수 분석/시뮬레이션 화면 (간단 JSON 응답)"""
    # MyData 스냅샷/프로필 사용
    mydata = MyDataClient()
    snapshot = mydata.get_credit_snapshot(request.user)

    generator = DynamicPlanGenerator(FreelancerIncomePredictor(), mydata=mydata)
    analysis = generator.analyze_credit_factors(snapshot)
    simulation = generator.simulate_credit_improvement(snapshot, months=6)
    # 금융상품 추천: MyData 프로필 기본값 사용(파라미터가 있으면 오버라이드)
    profile = mydata.get_user_profile(request.user)
    age = int(request.GET.get("age", profile["age"]))
    region = request.GET.get("region", profile["region"])
    housing = request.GET.get("housing", profile["housing"])
    employment = request.GET.get("employment", profile["employment"])
    has_children = (
        request.GET.get("children", str(profile["has_children"]).lower()).lower()
        == "true"
    )
    monthly_income = prediction_amount_for_user(request.user)
    products = generator.recommend_products(
        age=age,
        monthly_income=monthly_income,
        credit_score=snapshot.score,
        region=region,
        housing=housing,
        employment=employment,
        has_children=has_children,
    )

    resp = {
        "snapshot": {
            "score": snapshot.score,
            "utilization_rate": float(snapshot.utilization_rate),
            "on_time_payment_ratio": float(snapshot.on_time_payment_ratio),
            "credit_age_months": snapshot.credit_age_months,
            "hard_inquiries_12m": snapshot.hard_inquiries_12m,
            "credit_mix_score": snapshot.credit_mix_score,
        },
        "analysis": analysis,
        "simulation": simulation,
        "products": products,
        "profile": {
            "age": age,
            "region": region,
            "housing": housing,
            "employment": employment,
            "has_children": has_children,
        },
    }
    return JsonResponse(resp)


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["GET"])
def api_personal_coaching(request, plan_id):
    """API: Llama 3.1 8B 기반 개인 맞춤형 저축/신용 코칭"""
    try:
        logger.info(f"개인화 코칭 요청 시작 - 플랜 ID: {plan_id}")

        # 플랜 정보 가져오기
        plan = get_object_or_404(FinancialPlan, id=plan_id)
        logger.info(
            f"플랜 정보 로드 완료 - 사용자: {plan.user}, 소득: {plan.income_prediction.predicted_monthly_income}"
        )

        # 사용자 정보 가져오기
        user = plan.user

        # 개인화된 코칭 생성
        from .coaching import PersonalizedCoach

        coach = PersonalizedCoach()
        logger.info("PersonalizedCoach 인스턴스 생성 완료")

        advice = coach.generate_personalized_advice(
            user=user, plan=plan, income_prediction=plan.income_prediction
        )

        if advice:
            logger.info(
                f"코칭 생성 성공 - 조언 항목 수: {len(advice.get('savings_plan', []))}"
            )
            # CORS 헤더 추가
            response = JsonResponse({"success": True, "advice": advice})
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response
        else:
            logger.error("코칭 생성 실패 - 응답 없음")
            # 코칭 생성 실패 시 오류 응답
            response = JsonResponse(
                {
                    "success": False,
                    "error": "코칭 생성 실패",
                    "advice": None,
                }
            )
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    except Exception as e:
        logger.error(f"개인화 코칭 생성 실패: {str(e)}", exc_info=True)

        # 폴백 응답
        fallback_advice = {
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
                {"title": "신용카드 이용률 관리", "detail": "한도 대비 20% 이하 유지"},
                {
                    "title": "정기적 신용정보 확인",
                    "detail": "나이스/올크레딧에서 무료 조회",
                },
            ],
            "priority_actions": [
                {"title": "예산 설정", "detail": "매월 고정/변동 지출 계획 수립"},
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

        response = JsonResponse({"success": True, "advice": fallback_advice})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response


def prediction_amount_for_user(user):
    """사용자 최근 예측 월소득(없으면 기본 250만원)"""
    latest = IncomePrediction.objects.filter(user=user).order_by("-created_at").first()
    return (
        latest.predicted_monthly_income
        if latest and latest.predicted_monthly_income
        else Decimal("2500000")
    )


@csrf_exempt
@login_required
def api_apply_kpi(request, plan_id):
    """간단한 엔드포인트: 권장 KPI를 플랜에 적용합니다 (테스트용)"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    plan = get_object_or_404(FinancialPlan, id=plan_id, user=request.user)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "invalid json"}, status=400)

    target_savings = data.get("target_savings_rate")
    target_util = data.get("target_utilization_rate")

    try:
        if target_savings is not None:
            plan.target_savings_rate = Decimal(str(target_savings))
        plan.save()
        return JsonResponse({"success": True, "message": "KPI 적용 완료"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def plan_list(request):
    """사용자의 플랜 목록"""
    plans = FinancialPlan.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "plan/plan_list.html", {"plans": plans})


def generate_detailed_plan(plan, prediction, dynamic_plan=None):
    """상세 플랜 생성 (AI 기반 동적 플랜 활용)"""

    # 월별 계획 생성 (향후 12개월)
    current_year = timezone.now().year
    current_month = timezone.now().month
    first_month_snapshot = None  # 요약 카드용(첫 달 기준)

    # 동적 플랜이 있으면 사용, 없으면 기본 비율 사용
    if dynamic_plan and "monthly_plans" in dynamic_plan:
        monthly_plans_data = dynamic_plan["monthly_plans"]
        ratios = dynamic_plan.get("ratios", {})
    else:
        # 기본 비율 설정
        ratios = {
            "housing": 0.3,
            "food": 0.15,
            "transport": 0.1,
            "healthcare": 0.05,
            "entertainment": 0.1,
            "other": 0.1,
        }
        monthly_plans_data = None

    for i in range(12):
        target_month = current_month + i
        target_year = current_year

        if target_month > 12:
            target_month -= 12
            target_year += 1

        # 동적 플랜 데이터가 있으면 사용
        if monthly_plans_data and i < len(monthly_plans_data):
            plan_data = monthly_plans_data[i]
            expected_income = plan_data["expected_income"]
            housing_expense = plan_data["housing"]
            food_expense = plan_data["food"]
            transport_expense = plan_data["transport"]
            healthcare_expense = plan_data["healthcare"]
            entertainment_expense = plan_data["entertainment"]
            other_expenses = plan_data["other"]
            savings_amount = plan_data["savings"]
            investment_amount = plan_data["investment"]
        else:
            # 기본 계산
            expected_income = prediction.predicted_monthly_income
            housing_expense = expected_income * Decimal(str(ratios["housing"]))
            food_expense = expected_income * Decimal(str(ratios["food"]))
            transport_expense = expected_income * Decimal(str(ratios["transport"]))
            healthcare_expense = expected_income * Decimal(str(ratios["healthcare"]))
            entertainment_expense = expected_income * Decimal(
                str(ratios["entertainment"])
            )
            other_expenses = expected_income * Decimal(str(ratios["other"]))

            # 저축 및 투자 계획
            savings_amount = expected_income * (plan.target_savings_rate / 100)
            investment_amount = expected_income * Decimal("0.1")  # 투자 10%

        # 첫 달 스냅샷 저장(요약 카드용)
        if first_month_snapshot is None:
            total_expenses = (
                housing_expense
                + food_expense
                + transport_expense
                + healthcare_expense
                + entertainment_expense
                + other_expenses
            )
            first_month_snapshot = {
                "savings": savings_amount,
                "investment": investment_amount,
                "expenses": total_expenses,
            }

        # 신용 관리 (고정 성격)
        credit_payment = expected_income * Decimal("0.05")  # 신용카드 결제 5%
        loan_payment = expected_income * Decimal("0.05")  # 대출 상환 5%

        MonthlyPlan.objects.create(
            financial_plan=plan,
            year=target_year,
            month=target_month,
            expected_income=expected_income,
            housing_expense=housing_expense,  # MyData 고정값을 이미 반영
            food_expense=food_expense,
            transportation_expense=transport_expense,
            healthcare_expense=healthcare_expense,
            entertainment_expense=entertainment_expense,
            other_expenses=other_expenses,
            savings_amount=savings_amount,
            investment_amount=investment_amount,
            credit_card_payment=credit_payment,
            loan_payment=loan_payment,
            notes=f"{target_year}년 {target_month}월 AI 기반 계획",
        )

    # 플랜 설명 및 위험도 평가 생성
    plan.plan_description = generate_plan_description(plan, prediction)
    plan.risk_assessment = generate_risk_assessment(plan, prediction)

    # 신용등급 개선 계획
    plan.target_credit_score = min(plan.current_credit_score + 50, 950)
    plan.credit_improvement_plan = generate_credit_improvement_plan(plan)

    # 요약 카드 값 채우기(첫 달 기준)
    if first_month_snapshot:
        plan.monthly_savings = first_month_snapshot["savings"]
        plan.monthly_investment = first_month_snapshot["investment"]
        plan.monthly_expenses = first_month_snapshot["expenses"]

    plan.save()


def generate_plan_description(plan, prediction):
    """플랜 설명 생성"""
    description = f"""
    {plan.get_plan_type_display()} 자산 관리 플랜입니다.
    
    예상 월 소득: {prediction.predicted_monthly_income:,.0f}원
    목표 저축률: {plan.target_savings_rate}%
    월 저축 목표: {plan.monthly_savings:,.0f}원
    비상금 목표: {plan.emergency_fund_target:,.0f}원
    
    이 플랜은 {prediction.get_income_type_display()}(프리랜서) 및 청년층 특성을 고려하여 
    고정비를 낮추고(주거비 40만원 기준), 비상금과 투자 비중을 균형 있게 배분해 
    소득 변동성에 견고한 구조를 지향합니다.
    """
    return description.strip()


def generate_risk_assessment(plan, prediction):
    """위험도 평가 생성"""
    risk_factors = []

    if prediction.income_volatility > prediction.predicted_monthly_income * Decimal(
        "0.3"
    ):
        risk_factors.append("소득 변동성이 높음")

    if plan.target_savings_rate > 50:
        risk_factors.append("저축률이 높아 지출 여유가 부족할 수 있음")

    if plan.current_credit_score < 600:
        risk_factors.append("신용등급이 낮아 금융 상품 이용에 제약이 있을 수 있음")

    if not risk_factors:
        risk_level = "낮음"
        assessment = "현재 설정된 플랜은 안정적입니다."
    elif len(risk_factors) == 1:
        risk_level = "보통"
        assessment = f"주의가 필요한 요소: {risk_factors[0]}"
    else:
        risk_level = "높음"
        assessment = f"주의가 필요한 요소들: {', '.join(risk_factors)}"

    return f"위험도: {risk_level}\n\n{assessment}"


def generate_credit_improvement_plan(plan):
    """신용등급 개선 계획 생성"""
    improvements = []

    if plan.current_credit_score < 600:
        improvements.extend(
            [
                "신용카드 사용량을 소득의 30% 이하로 제한",
                "모든 신용카드 대금을 만기일 전에 결제",
                "대출 상환을 우선적으로 진행",
            ]
        )
    elif plan.current_credit_score < 700:
        improvements.extend(
            [
                "신용카드 사용량을 소득의 40% 이하로 제한",
                "정기적인 신용카드 사용으로 신용 이력 쌓기",
                "소액 대출로 신용 이력 다양화",
            ]
        )
    else:
        improvements.extend(
            [
                "현재 신용등급을 유지",
                "신용카드 혜택을 적극 활용",
                "정기적인 신용정보 확인",
            ]
        )

    return "\n".join(improvements)


@login_required
@csrf_exempt
def api_predict_income(request):
    """API: 실시간 소득 예측"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        data = json.loads(request.body)
        monthly_incomes = [
            Decimal(str(income)) for income in data.get("monthly_incomes", [])
        ]
        income_type = data.get("income_type", "freelance")

        if len(monthly_incomes) != 12:
            return JsonResponse(
                {"error": "12개월 소득 데이터가 필요합니다"}, status=400
            )

        # AI 예측 수행
        ai_predictor = FreelancerIncomePredictor()
        prediction_result = ai_predictor.predict_income(monthly_incomes, income_type)

        return JsonResponse(
            {
                "success": True,
                "prediction": {
                    "predicted_monthly_income": float(
                        prediction_result["predicted_monthly_income"]
                    ),
                    "predicted_yearly_income": float(
                        prediction_result["predicted_yearly_income"]
                    ),
                    "confidence_level": float(prediction_result["confidence_level"]),
                    "income_volatility": float(prediction_result["income_volatility"]),
                    "seasonal_pattern": prediction_result["seasonal_pattern"],
                    "risk_factors": prediction_result.get("risk_factors", []),
                    "growth_trend": prediction_result.get("growth_trend", "stable"),
                    "recommendations": prediction_result.get("recommendations", []),
                    "prediction_method": prediction_result.get(
                        "prediction_method", "unknown"
                    ),
                },
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@csrf_exempt
def api_generate_plan(request):
    """API: 동적 플랜 생성"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        data = json.loads(request.body)

        # 예측 결과
        prediction_result = {
            "predicted_monthly_income": Decimal(str(data["predicted_monthly_income"])),
            "income_volatility": Decimal(str(data.get("income_volatility", 0))),
            "risk_factors": data.get("risk_factors", []),
            "growth_trend": data.get("growth_trend", "stable"),
        }

        # 사용자 선호도
        user_preferences = {
            "plan_type": data.get("plan_type", "moderate"),
            "target_savings_rate": data.get("target_savings_rate", 20),
        }

        # 동적 플랜 생성
        ai_predictor = FreelancerIncomePredictor()
        plan_generator = DynamicPlanGenerator(ai_predictor)
        dynamic_plan = plan_generator.generate_adaptive_plan(
            prediction_result, user_preferences
        )

        # 응답 데이터 변환
        response_data = {
            "success": True,
            "plan": {
                "plan_type": dynamic_plan["plan_type"],
                "ratios": dynamic_plan["ratios"],
                "monthly_plans": [
                    {
                        "month": plan["month"],
                        "expected_income": float(plan["expected_income"]),
                        "savings": float(plan["savings"]),
                        "investment": float(plan["investment"]),
                        "housing": float(plan["housing"]),
                        "food": float(plan["food"]),
                        "transport": float(plan["transport"]),
                        "healthcare": float(plan["healthcare"]),
                        "entertainment": float(plan["entertainment"]),
                        "other": float(plan["other"]),
                    }
                    for plan in dynamic_plan["monthly_plans"]
                ],
                "risk_assessment": dynamic_plan["risk_assessment"],
                "adaptation_strategy": dynamic_plan["adaptation_strategy"],
            },
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@csrf_exempt
def api_seed_and_generate(request):
    """API: (임시) 현재 사용자에 대해 12개월 소득을 DB에 저장하고 맞춤형 플랜 생성

    Request (JSON):
    {
      "monthly_incomes": [12개 숫자],
      "income_type": "freelance|business|employee|mixed",
      "plan_type": "conservative|moderate|aggressive" (optional),
      "target_savings_rate": 20 (optional),
      "emergency_fund_target": 0 (optional),
      "current_credit_score": 700 (optional)
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        payload = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(payload)

        # 입력 데이터 준비 (없으면 합리적인 기본값 생성)
        raw_incomes = data.get("monthly_incomes")
        if not raw_incomes or len(raw_incomes) != 12:
            # 기본 시드(하향): 100만~160만원 사이 완만한 변동
            raw_incomes = [
                1000000,
                1100000,
                1200000,
                1300000,
                1400000,
                1000000,
                1100000,
                900000,
                1200000,
                1500000,
                1600000,
                1400000,
            ]
        monthly_incomes = [_safe_decimal(v, "0") for v in raw_incomes]

        income_type = data.get("income_type", "freelance")
        plan_type = data.get("plan_type", "moderate")
        target_savings_rate = _safe_decimal(data.get("target_savings_rate", "20"), "20")
        emergency_fund_target = _safe_decimal(
            data.get("emergency_fund_target", "0"), "0"
        )
        current_credit_score = int(data.get("current_credit_score", 700))

        # 1) 기존 손상 데이터 무시하고 안전 업데이트 (fetch 없이 UPDATE만 수행)
        IncomePrediction.objects.filter(user=request.user).update(
            monthly_income_1=0,
            monthly_income_2=0,
            monthly_income_3=0,
            monthly_income_4=0,
            monthly_income_5=0,
            monthly_income_6=0,
            monthly_income_7=0,
            monthly_income_8=0,
            monthly_income_9=0,
            monthly_income_10=0,
            monthly_income_11=0,
            monthly_income_12=0,
            predicted_monthly_income=0,
            predicted_yearly_income=0,
            confidence_level=0,
            income_volatility=0,
            seasonal_pattern="",
        )

        # 2) 예측 레코드 확보 (없으면 생성)
        prediction, _ = IncomePrediction.objects.get_or_create(
            user=request.user, defaults={"income_type": income_type}
        )
        prediction.income_type = income_type
        # 12개월 데이터 저장
        (prediction.__setattr__("monthly_income_1", monthly_incomes[0]))
        prediction.monthly_income_2 = monthly_incomes[1]
        prediction.monthly_income_3 = monthly_incomes[2]
        prediction.monthly_income_4 = monthly_incomes[3]
        prediction.monthly_income_5 = monthly_incomes[4]
        prediction.monthly_income_6 = monthly_incomes[5]
        prediction.monthly_income_7 = monthly_incomes[6]
        prediction.monthly_income_8 = monthly_incomes[7]
        prediction.monthly_income_9 = monthly_incomes[8]
        prediction.monthly_income_10 = monthly_incomes[9]
        prediction.monthly_income_11 = monthly_incomes[10]
        prediction.monthly_income_12 = monthly_incomes[11]

        # 3) AI/폴백 예측 실행
        ai_predictor = FreelancerIncomePredictor()
        result = ai_predictor.predict_income(monthly_incomes, income_type)
        prediction.predicted_monthly_income = result["predicted_monthly_income"]
        prediction.predicted_yearly_income = result["predicted_yearly_income"]
        prediction.confidence_level = result["confidence_level"]
        prediction.income_volatility = result["income_volatility"]
        prediction.seasonal_pattern = result.get("seasonal_pattern", "")
        prediction.save()

        # 4) 플랜 생성 + 월별 상세 생성
        plan = FinancialPlan.objects.create(
            user=request.user,
            income_prediction=prediction,
            plan_type=plan_type,
            target_savings_rate=target_savings_rate,
            emergency_fund_target=emergency_fund_target,
            current_credit_score=current_credit_score,
        )

        plan_generator = DynamicPlanGenerator(ai_predictor)
        dynamic_plan = plan_generator.generate_adaptive_plan(
            prediction_result={
                "predicted_monthly_income": prediction.predicted_monthly_income,
                "income_volatility": prediction.income_volatility,
                "risk_factors": result.get("risk_factors", []),
                "growth_trend": result.get("growth_trend", "stable"),
            },
            user_preferences={
                "plan_type": plan_type,
                "target_savings_rate": target_savings_rate,
            },
        )

        generate_detailed_plan(plan, prediction, dynamic_plan)

        return JsonResponse(
            {
                "success": True,
                "prediction_id": prediction.id,
                "plan_id": plan.id,
                "redirect_detail_url": f"/plan/detail/{plan.id}/",
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def plan_analytics(request, plan_id):
    """플랜 분석 및 인사이트"""
    plan = get_object_or_404(FinancialPlan, id=plan_id, user=request.user)
    monthly_plans = plan.monthly_plans.all()

    # 분석 데이터 생성
    analytics = {
        "total_expected_income": sum(mp.expected_income for mp in monthly_plans),
        "total_savings": sum(mp.savings_amount for mp in monthly_plans),
        "total_investment": sum(mp.investment_amount for mp in monthly_plans),
        "average_monthly_income": (
            sum(mp.expected_income for mp in monthly_plans) / len(monthly_plans)
            if monthly_plans
            else 0
        ),
        "savings_rate": (
            (
                sum(mp.savings_amount for mp in monthly_plans)
                / sum(mp.expected_income for mp in monthly_plans)
                * 100
            )
            if monthly_plans
            else 0
        ),
        "income_trend": "stable",  # 추후 계산 로직 추가
        "recommendations": [],
    }

    return render(
        request,
        "plan/plan_analytics.html",
        {"plan": plan, "analytics": analytics, "monthly_plans": monthly_plans},
    )


@login_required
def smart_plan_generator(request):
    """AI 기반 스마트 계획 생성"""
    if request.method == "POST":
        try:
            # 마이데이터 연동 여부 확인
            use_mydata = request.POST.get("use_mydata") == "on"

            if use_mydata:
                # 마이데이터에서 자동으로 데이터 가져오기
                smart_generator = SmartPlanGenerator()
                smart_plan = smart_generator.generate_smart_plan_from_mydata(
                    request.user
                )

                # 마이데이터 정보로 사용자 입력 구성
                mydata_info = smart_plan.get("mydata_info", {})
                user_input = {
                    "monthly_income": mydata_info.get("monthly_income", 3000000),
                    "age": 27,  # 마이데이터 기본값
                    "location": "seoul",
                    "occupation": "freelancer",
                    "data_source": "mydata",
                }
            else:
                # 사용자 직접 입력
                monthly_income = _safe_decimal(request.POST.get("monthly_income", "0"))
                age = int(request.POST.get("age", 25))
                location = request.POST.get("location", "seoul")
                occupation = request.POST.get("occupation", "freelancer")

                # 거래내역 데이터 (선택사항)
                transaction_data = request.POST.get("transaction_data", "")
                transaction_history = []
                if transaction_data:
                    try:
                        transaction_history = json.loads(transaction_data)
                    except json.JSONDecodeError:
                        transaction_history = []

                # 사용자 프로필 구성
                user_profile = {
                    "age": age,
                    "location": location,
                    "occupation": occupation,
                }

                # 스마트 계획 생성
                smart_generator = SmartPlanGenerator()
                smart_plan = smart_generator.generate_smart_plan(
                    user=request.user,
                    monthly_income=monthly_income,
                    transaction_history=transaction_history,
                    user_profile=user_profile,
                )

                # 사용자 입력 정보 구성
                user_input = {
                    "monthly_income": float(monthly_income),
                    "age": age,
                    "location": location,
                    "occupation": occupation,
                    "data_source": "manual",
                }

            # 세션에 저장 (결과 페이지에서 사용)
            request.session["smart_plan"] = smart_plan
            request.session["user_input"] = user_input

            messages.success(request, "AI가 맞춤형 자산 관리 계획을 생성했습니다!")
            return redirect("plan:smart_plan_result")

        except Exception as e:
            logger.error(f"스마트 계획 생성 실패: {e}")
            messages.error(
                request, "계획 생성 중 오류가 발생했습니다. 다시 시도해주세요."
            )

    return render(request, "plan/smart_plan_generator.html")


@login_required
def smart_plan_result(request):
    """스마트 계획 결과 페이지"""
    smart_plan = request.session.get("smart_plan")
    user_input = request.session.get("user_input")

    if not smart_plan or not user_input:
        messages.error(request, "계획 데이터를 찾을 수 없습니다. 다시 생성해주세요.")
        return redirect("plan:smart_plan_generator")

    return render(
        request,
        "plan/smart_plan_result.html",
        {
            "smart_plan": smart_plan,
            "user_input": user_input,
        },
    )


@login_required
@csrf_exempt
def api_smart_plan(request):
    """API: 스마트 계획 생성"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        data = json.loads(request.body)

        # 마이데이터 연동 여부 확인
        use_mydata = data.get("use_mydata", False)

        if use_mydata:
            # 마이데이터에서 자동으로 데이터 가져오기
            smart_generator = SmartPlanGenerator()
            smart_plan = smart_generator.generate_smart_plan_from_mydata(request.user)

            # 마이데이터 정보로 사용자 입력 구성
            mydata_info = smart_plan.get("mydata_info", {})
            user_input = {
                "monthly_income": mydata_info.get("monthly_income", 3000000),
                "age": 27,
                "location": "seoul",
                "occupation": "freelancer",
                "data_source": "mydata",
            }
        else:
            # 필수 데이터 검증
            monthly_income = _safe_decimal(data.get("monthly_income", "0"))
            if monthly_income <= 0:
                return JsonResponse(
                    {"error": "유효한 월 소득을 입력해주세요"}, status=400
                )

            # 사용자 프로필
            user_profile = {
                "age": data.get("age", 25),
                "location": data.get("location", "seoul"),
                "occupation": data.get("occupation", "freelancer"),
            }

            # 거래내역 (선택사항)
            transaction_history = data.get("transaction_history", [])

            # 스마트 계획 생성
            smart_generator = SmartPlanGenerator()
            smart_plan = smart_generator.generate_smart_plan(
                user=request.user,
                monthly_income=monthly_income,
                transaction_history=transaction_history,
                user_profile=user_profile,
            )

            # 사용자 입력 정보 구성
            user_input = {
                "monthly_income": float(monthly_income),
                "age": user_profile["age"],
                "location": user_profile["location"],
                "occupation": user_profile["occupation"],
                "data_source": "manual",
            }

        return JsonResponse(
            {
                "success": True,
                "smart_plan": smart_plan,
                "user_input": user_input,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 JSON 형식"}, status=400)
    except Exception as e:
        logger.error(f"API 스마트 계획 생성 실패: {e}")
        return JsonResponse({"error": str(e)}, status=500)
