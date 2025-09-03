from django.contrib import admin
from .models import IncomePrediction, FinancialPlan, MonthlyPlan

@admin.register(IncomePrediction)
class IncomePredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'income_type', 'predicted_monthly_income', 'confidence_level', 'created_at']
    list_filter = ['income_type', 'created_at']
    search_fields = ['user__username', 'user__email']
    ordering = ['-created_at']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user', 'income_type')
        }),
        ('과거 소득 데이터 (최근 12개월)', {
            'fields': (
                'monthly_income_1', 'monthly_income_2', 'monthly_income_3', 'monthly_income_4',
                'monthly_income_5', 'monthly_income_6', 'monthly_income_7', 'monthly_income_8',
                'monthly_income_9', 'monthly_income_10', 'monthly_income_11', 'monthly_income_12'
            ),
            'classes': ('collapse',)
        }),
        ('예측 결과', {
            'fields': ('predicted_monthly_income', 'predicted_yearly_income', 'confidence_level')
        }),
        ('분석 결과', {
            'fields': ('income_volatility', 'seasonal_pattern')
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(FinancialPlan)
class FinancialPlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan_type', 'target_savings_rate', 'current_credit_score', 'created_at']
    list_filter = ['plan_type', 'created_at']
    search_fields = ['user__username', 'user__email']
    ordering = ['-created_at']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user', 'income_prediction', 'plan_type')
        }),
        ('플랜 목표', {
            'fields': ('target_savings_rate', 'emergency_fund_target', 'investment_target')
        }),
        ('월별 계획', {
            'fields': ('monthly_savings', 'monthly_investment', 'monthly_expenses')
        }),
        ('신용 관리', {
            'fields': ('current_credit_score', 'target_credit_score', 'credit_improvement_plan')
        }),
        ('플랜 설명', {
            'fields': ('plan_description', 'risk_assessment')
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'income_prediction')

@admin.register(MonthlyPlan)
class MonthlyPlanAdmin(admin.ModelAdmin):
    list_display = ['financial_plan', 'year', 'month', 'expected_income', 'total_expenses', 'disposable_income']
    list_filter = ['year', 'month']
    search_fields = ['financial_plan__user__username']
    ordering = ['-year', '-month']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('financial_plan', 'year', 'month')
        }),
        ('소득 및 지출', {
            'fields': ('expected_income', 'housing_expense', 'food_expense', 'transportation_expense')
        }),
        ('추가 지출', {
            'fields': ('healthcare_expense', 'entertainment_expense', 'other_expenses')
        }),
        ('저축 및 투자', {
            'fields': ('savings_amount', 'investment_amount')
        }),
        ('신용 관리', {
            'fields': ('credit_card_payment', 'loan_payment')
        }),
        ('메모', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ['total_expenses', 'disposable_income']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('financial_plan__user')
