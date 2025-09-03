from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class IncomePrediction(models.Model):
    """소득 예측 모델"""
    
    INCOME_TYPES = [
        ('freelance', '프리랜서'),
        ('business', '사업자'),
        ('employee', '급여소득자'),
        ('mixed', '혼합소득'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='income_predictions')
    income_type = models.CharField(max_length=20, choices=INCOME_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 과거 소득 데이터 (최근 12개월)
    monthly_income_1 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_2 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_3 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_4 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_5 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_6 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_7 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_8 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_9 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_10 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_11 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_income_12 = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 예측된 소득
    predicted_monthly_income = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    predicted_yearly_income = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    confidence_level = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0-100%
    
    # 변동성 지표
    income_volatility = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 표준편차
    seasonal_pattern = models.TextField(blank=True)  # 계절성 패턴
    
    def __str__(self):
        return f"{self.user.username} - {self.get_income_type_display()} 소득예측"

class FinancialPlan(models.Model):
    """자산 관리 플랜 모델"""
    
    PLAN_TYPES = [
        ('conservative', '보수형'),
        ('moderate', '균형형'),
        ('aggressive', '공격형'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_plans')
    income_prediction = models.ForeignKey(IncomePrediction, on_delete=models.CASCADE, related_name='plans')
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 플랜 목표
    target_savings_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20)  # 월 소득 대비 저축률
    emergency_fund_target = models.DecimalField(max_digits=12, decimal_places=0, default=0)  # 비상금 목표
    investment_target = models.DecimalField(max_digits=12, decimal_places=0, default=0)  # 투자 목표
    
    # 월별 계획
    monthly_savings = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_investment = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    monthly_expenses = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 신용등급 관련
    current_credit_score = models.IntegerField(default=0)
    target_credit_score = models.IntegerField(default=0)
    credit_improvement_plan = models.TextField(blank=True)
    
    # 플랜 설명
    plan_description = models.TextField(blank=True)
    risk_assessment = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_plan_type_display()} 플랜"

class MonthlyPlan(models.Model):
    """월별 세부 계획"""
    
    financial_plan = models.ForeignKey(FinancialPlan, on_delete=models.CASCADE, related_name='monthly_plans')
    year = models.IntegerField()
    month = models.IntegerField()
    
    # 예상 소득
    expected_income = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 지출 계획
    housing_expense = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    food_expense = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    transportation_expense = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    healthcare_expense = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    entertainment_expense = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    other_expenses = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 저축 및 투자
    savings_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    investment_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 신용 관리
    credit_card_payment = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    loan_payment = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 메모
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['financial_plan', 'year', 'month']
        ordering = ['year', 'month']
    
    def __str__(self):
        return f"{self.financial_plan.user.username} - {self.year}년 {self.month}월 계획"
    
    @property
    def total_expenses(self):
        """총 지출 계산"""
        return (self.housing_expense + self.food_expense + self.transportation_expense + 
                self.healthcare_expense + self.entertainment_expense + self.other_expenses)
    
    @property
    def disposable_income(self):
        """가처분 소득 계산"""
        return self.expected_income - self.total_expenses - self.credit_card_payment - self.loan_payment
