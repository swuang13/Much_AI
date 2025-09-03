from django.contrib import admin
from .models import AssetAssessment, AssessmentQuestion, AssessmentAnswer

@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'category', 'weight', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['question_text']
    ordering = ['category', 'created_at']
    
    fieldsets = (
        ('질문 정보', {
            'fields': ('question_text', 'category', 'weight', 'is_active')
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']

@admin.register(AssetAssessment)
class AssetAssessmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'assessment_type', 'total_score', 'created_at', 'updated_at']
    list_filter = ['assessment_type', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    ordering = ['-created_at']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user', 'assessment_type')
        }),
        ('진단 결과', {
            'fields': (
                'total_score', 'financial_literacy_score', 'risk_management_score',
                'investment_knowledge_score', 'debt_management_score'
            )
        }),
        ('피드백', {
            'fields': ('feedback', 'recommendations')
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(AssessmentAnswer)
class AssessmentAnswerAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'question', 'answer_value', 'created_at']
    list_filter = ['answer_value', 'created_at']
    search_fields = ['assessment__user__username', 'question__question_text']
    ordering = ['-created_at']
    
    fieldsets = (
        ('답변 정보', {
            'fields': ('assessment', 'question', 'answer_value')
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('assessment__user', 'question')
