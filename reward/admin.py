from django.contrib import admin
from .models import (
    UserProfile, PointHistory, LevelUpHistory, Quiz, QuizQuestion, 
    QuizOption, QuizAttempt, FinancialBenefit, UserBenefit, 
    Achievement, UserAchievement
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_level', 'total_points', 'quizzes_completed', 'assessments_completed', 'streak_days']
    list_filter = ['current_level', 'created_at']
    search_fields = ['user__username', 'user__email']
    ordering = ['-current_level', '-total_points']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user',)
        }),
        ('포인트 및 레벨', {
            'fields': ('total_points', 'current_level', 'experience_points', 'experience_to_next_level')
        }),
        ('활동 통계', {
            'fields': ('quizzes_completed', 'assessments_completed', 'plans_created', 'streak_days')
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at', 'last_activity_date'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'points_reward', 'is_active', 'created_at']
    list_filter = ['category', 'difficulty', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['category', 'difficulty', 'created_at']
    
    fieldsets = (
        ('퀴즈 정보', {
            'fields': ('title', 'description', 'category', 'difficulty', 'points_reward', 'is_active')
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']

@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'question_text', 'points', 'order']
    list_filter = ['quiz', 'points']
    search_fields = ['question_text', 'quiz__title']
    ordering = ['quiz', 'order']
    
    fieldsets = (
        ('질문 정보', {
            'fields': ('quiz', 'question_text', 'explanation', 'points', 'order')
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = []

@admin.register(QuizOption)
class QuizOptionAdmin(admin.ModelAdmin):
    list_display = ['question', 'option_text', 'is_correct', 'order']
    list_filter = ['is_correct', 'order']
    search_fields = ['option_text', 'question__question_text']
    ordering = ['question', 'order']
    
    fieldsets = (
        ('선택지 정보', {
            'fields': ('question', 'option_text', 'is_correct', 'order')
        }),
    )

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'quiz', 'score', 'max_score', 'completed_at']
    list_filter = ['completed_at']
    search_fields = ['user_profile__user__username', 'quiz__title']
    ordering = ['-completed_at']
    
    fieldsets = (
        ('시도 정보', {
            'fields': ('user_profile', 'quiz', 'score', 'max_score')
        }),
        ('메타데이터', {
            'fields': ('completed_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['completed_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user', 'quiz')

@admin.register(FinancialBenefit)
class FinancialBenefitAdmin(admin.ModelAdmin):
    list_display = ['title', 'benefit_type', 'partner_bank', 'required_level', 'required_points', 'is_active']
    list_filter = ['benefit_type', 'required_level', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'partner_bank']
    ordering = ['benefit_type', 'required_level', 'required_points']
    
    fieldsets = (
        ('혜택 정보', {
            'fields': ('title', 'description', 'benefit_type', 'partner_bank')
        }),
        ('조건', {
            'fields': ('required_level', 'required_points', 'is_active')
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']

@admin.register(UserBenefit)
class UserBenefitAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'financial_benefit', 'points_spent', 'is_active', 'activated_at']
    list_filter = ['is_active', 'activated_at']
    search_fields = ['user_profile__user__username', 'financial_benefit__title']
    ordering = ['-activated_at']
    
    fieldsets = (
        ('사용자 혜택', {
            'fields': ('user_profile', 'financial_benefit', 'points_spent', 'is_active')
        }),
        ('활성화 정보', {
            'fields': ('activated_at', 'expires_at')
        }),
    )
    
    readonly_fields = ['activated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user', 'financial_benefit')

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['title', 'achievement_type', 'requirement_value', 'points_reward', 'is_hidden']
    list_filter = ['achievement_type', 'is_hidden']
    search_fields = ['title', 'description']
    ordering = ['achievement_type', 'requirement_value']
    
    fieldsets = (
        ('업적 정보', {
            'fields': ('title', 'description', 'achievement_type', 'icon')
        }),
        ('달성 조건', {
            'fields': ('requirement_value', 'points_reward')
        }),
        ('설정', {
            'fields': ('is_hidden',)
        }),
    )

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'achievement', 'earned_at']
    list_filter = ['earned_at']
    search_fields = ['user_profile__user__username', 'achievement__title']
    ordering = ['-earned_at']
    
    fieldsets = (
        ('업적 달성', {
            'fields': ('user_profile', 'achievement')
        }),
        ('메타데이터', {
            'fields': ('earned_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['earned_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user', 'achievement')

@admin.register(PointHistory)
class PointHistoryAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'points', 'point_type', 'reason', 'created_at']
    list_filter = ['point_type', 'created_at']
    search_fields = ['user_profile__user__username', 'reason']
    ordering = ['-created_at']
    
    fieldsets = (
        ('포인트 기록', {
            'fields': ('user_profile', 'points', 'point_type', 'reason')
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user')

@admin.register(LevelUpHistory)
class LevelUpHistoryAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'new_level', 'reward_points', 'created_at']
    list_filter = ['new_level', 'created_at']
    search_fields = ['user_profile__user__username']
    ordering = ['-created_at']
    
    fieldsets = (
        ('레벨업 정보', {
            'fields': ('user_profile', 'new_level', 'reward_points')
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user')
