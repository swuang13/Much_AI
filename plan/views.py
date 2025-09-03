from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import statistics
from decimal import Decimal

from .models import IncomePrediction, FinancialPlan, MonthlyPlan

def plan_home(request):
    """플랜 생성 메인 페이지"""
    return render(request, 'plan/plan_home.html')

@login_required
def income_prediction(request):
    """소득 예측 입력 및 생성"""
    if request.method == 'POST':
        income_type = request.POST.get('income_type')
        
        # 과거 소득 데이터 수집
        monthly_incomes = []
        for i in range(1, 13):
            income = request.POST.get(f'monthly_income_{i}', 0)
            monthly_incomes.append(Decimal(income) if income else Decimal(0))
        
        # 기존 예측이 있다면 업데이트
        prediction, created = IncomePrediction.objects.get_or_create(
            user=request.user,
            defaults={'income_type': income_type}
        )
        
        if not created:
            prediction.income_type = income_type
        
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
        
        # AI 소득 예측 수행
        predicted_income, confidence, volatility, seasonal = predict_income(monthly_incomes)
        
        prediction.predicted_monthly_income = predicted_income
        prediction.predicted_yearly_income = predicted_income * 12
        prediction.confidence_level = confidence
        prediction.income_volatility = volatility
        prediction.seasonal_pattern = seasonal
        
        prediction.save()
        
        messages.success(request, '소득 예측이 완료되었습니다!')
        return redirect('plan:create_financial_plan', prediction_id=prediction.id)
    
    return render(request, 'plan/income_prediction.html')

@login_required
def create_financial_plan(request, prediction_id):
    """자산 관리 플랜 생성"""
    prediction = get_object_or_404(IncomePrediction, id=prediction_id, user=request.user)
    
    if request.method == 'POST':
        plan_type = request.POST.get('plan_type')
        target_savings_rate = Decimal(request.POST.get('target_savings_rate', 20))
        emergency_fund_target = Decimal(request.POST.get('emergency_fund_target', 0))
        current_credit_score = int(request.POST.get('current_credit_score', 0))
        
        # 플랜 생성
        plan = FinancialPlan.objects.create(
            user=request.user,
            income_prediction=prediction,
            plan_type=plan_type,
            target_savings_rate=target_savings_rate,
            emergency_fund_target=emergency_fund_target,
            current_credit_score=current_credit_score
        )
        
        # 플랜 상세 정보 생성
        generate_detailed_plan(plan, prediction)
        
        messages.success(request, '자산 관리 플랜이 생성되었습니다!')
        return redirect('plan:plan_detail', plan_id=plan.id)
    
    return render(request, 'plan/create_financial_plan.html', {
        'prediction': prediction
    })

@login_required
def plan_detail(request, plan_id):
    """플랜 상세 보기"""
    plan = get_object_or_404(FinancialPlan, id=plan_id, user=request.user)
    monthly_plans = plan.monthly_plans.all()
    
    return render(request, 'plan/plan_detail.html', {
        'plan': plan,
        'monthly_plans': monthly_plans
    })

@login_required
def plan_list(request):
    """사용자의 플랜 목록"""
    plans = FinancialPlan.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'plan/plan_list.html', {
        'plans': plans
    })

def predict_income(monthly_incomes):
    """AI 소득 예측 모델 (간단한 통계 기반)"""
    
    # 0이 아닌 소득만 필터링
    valid_incomes = [income for income in monthly_incomes if income > 0]
    
    if not valid_incomes:
        return Decimal(0), Decimal(0), Decimal(0), "데이터 부족"
    
    # 기본 통계 계산
    mean_income = sum(valid_incomes) / len(valid_incomes)
    
    # 변동성 계산 (표준편차)
    if len(valid_incomes) > 1:
        variance = sum((income - mean_income) ** 2 for income in valid_incomes) / (len(valid_incomes) - 1)
        volatility = variance.sqrt()
    else:
        volatility = Decimal(0)
    
    # 계절성 패턴 분석 (간단한 월별 평균)
    monthly_averages = {}
    for i, income in enumerate(monthly_incomes):
        if income > 0:
            month = (i + 1) % 12 or 12
            if month not in monthly_averages:
                monthly_averages[month] = []
            monthly_averages[month].append(income)
    
    seasonal_pattern = "계절성 패턴: "
    if monthly_averages:
        for month in sorted(monthly_averages.keys()):
            avg = sum(monthly_averages[month]) / len(monthly_averages[month])
            seasonal_pattern += f"{month}월 평균 {avg:,.0f}원, "
        seasonal_pattern = seasonal_pattern.rstrip(", ")
    else:
        seasonal_pattern = "계절성 패턴 없음"
    
    # 신뢰도 계산 (데이터 양과 변동성 기반)
    data_quality = min(len(valid_incomes) / 12, 1.0)  # 데이터 완성도
    volatility_factor = max(0, 1 - (volatility / mean_income)) if mean_income > 0 else 0
    confidence = (data_quality * 0.6 + volatility_factor * 0.4) * 100
    
    # 예측 소득 (가중 평균 + 트렌드 고려)
    if len(valid_incomes) >= 3:
        # 최근 3개월에 더 높은 가중치
        recent_weight = 0.6
        older_weight = 0.4
        
        recent_avg = sum(valid_incomes[-3:]) / 3
        older_avg = sum(valid_incomes[:-3]) / (len(valid_incomes) - 3) if len(valid_incomes) > 3 else recent_avg
        
        predicted = recent_avg * recent_weight + older_avg * older_weight
    else:
        predicted = mean_income
    
    return predicted, Decimal(str(confidence)), volatility, seasonal_pattern

def generate_detailed_plan(plan, prediction):
    """상세 플랜 생성"""
    
    # 월별 계획 생성 (향후 12개월)
    current_year = timezone.now().year
    current_month = timezone.now().month
    
    for i in range(12):
        target_month = current_month + i
        target_year = current_year
        
        if target_month > 12:
            target_month -= 12
            target_year += 1
        
        # 예상 소득 (계절성 고려)
        expected_income = prediction.predicted_monthly_income
        
        # 월별 지출 계획 (소득 대비 비율)
        housing_ratio = Decimal('0.3')  # 주거비 30%
        food_ratio = Decimal('0.15')    # 식비 15%
        transport_ratio = Decimal('0.1') # 교통비 10%
        healthcare_ratio = Decimal('0.05') # 의료비 5%
        entertainment_ratio = Decimal('0.1') # 여가비 10%
        other_ratio = Decimal('0.1')    # 기타 10%
        
        # 저축 및 투자 계획
        savings_amount = expected_income * (plan.target_savings_rate / 100)
        investment_amount = expected_income * Decimal('0.1')  # 투자 10%
        
        # 신용 관리
        credit_payment = expected_income * Decimal('0.05')  # 신용카드 결제 5%
        loan_payment = expected_income * Decimal('0.05')   # 대출 상환 5%
        
        MonthlyPlan.objects.create(
            financial_plan=plan,
            year=target_year,
            month=target_month,
            expected_income=expected_income,
            housing_expense=expected_income * housing_ratio,
            food_expense=expected_income * food_ratio,
            transportation_expense=expected_income * transport_ratio,
            healthcare_expense=expected_income * healthcare_ratio,
            entertainment_expense=expected_income * entertainment_ratio,
            other_expenses=expected_income * other_ratio,
            savings_amount=savings_amount,
            investment_amount=investment_amount,
            credit_card_payment=credit_payment,
            loan_payment=loan_payment,
            notes=f"{target_year}년 {target_month}월 계획"
        )
    
    # 플랜 설명 및 위험도 평가 생성
    plan.plan_description = generate_plan_description(plan, prediction)
    plan.risk_assessment = generate_risk_assessment(plan, prediction)
    
    # 신용등급 개선 계획
    plan.target_credit_score = min(plan.current_credit_score + 50, 950)
    plan.credit_improvement_plan = generate_credit_improvement_plan(plan)
    
    plan.save()

def generate_plan_description(plan, prediction):
    """플랜 설명 생성"""
    description = f"""
    {plan.get_plan_type_display()} 자산 관리 플랜입니다.
    
    예상 월 소득: {prediction.predicted_monthly_income:,.0f}원
    목표 저축률: {plan.target_savings_rate}%
    월 저축 목표: {plan.monthly_savings:,.0f}원
    비상금 목표: {plan.emergency_fund_target:,.0f}원
    
    이 플랜은 {prediction.get_income_type_display()} 소득 특성을 고려하여 
    안정적이고 지속 가능한 자산 관리를 목표로 합니다.
    """
    return description.strip()

def generate_risk_assessment(plan, prediction):
    """위험도 평가 생성"""
    risk_factors = []
    
    if prediction.income_volatility > prediction.predicted_monthly_income * Decimal('0.3'):
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
        improvements.extend([
            "신용카드 사용량을 소득의 30% 이하로 제한",
            "모든 신용카드 대금을 만기일 전에 결제",
            "대출 상환을 우선적으로 진행"
        ])
    elif plan.current_credit_score < 700:
        improvements.extend([
            "신용카드 사용량을 소득의 40% 이하로 제한",
            "정기적인 신용카드 사용으로 신용 이력 쌓기",
            "소액 대출로 신용 이력 다양화"
        ])
    else:
        improvements.extend([
            "현재 신용등급을 유지",
            "신용카드 혜택을 적극 활용",
            "정기적인 신용정보 확인"
        ])
    
    return "\n".join(improvements)
