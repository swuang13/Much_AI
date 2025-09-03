from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class AssetAssessment(models.Model):
    """자산 관리 역량 진단 모델"""
    
    ASSESSMENT_TYPES = [
        ('basic', '기본 진단'),
        ('advanced', '심화 진단'),
        ('comprehensive', '종합 진단'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='asset_assessments')
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES, default='basic')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 진단 결과 점수 (0-100)
    total_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    
    # 세부 영역별 점수
    financial_literacy_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    risk_management_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    investment_knowledge_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    debt_management_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    
    # 피드백 및 권장사항
    feedback = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.assessment_type} ({self.created_at.strftime('%Y-%m-%d')})"

class AssessmentQuestion(models.Model):
    """진단 질문 모델"""
    
    CATEGORIES = [
        ('financial_literacy', '금융 리터러시'),
        ('risk_management', '위험 관리'),
        ('investment', '투자 지식'),
        ('debt', '부채 관리'),
    ]
    
    question_text = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORIES)
    weight = models.IntegerField(default=1)  # 질문 가중치
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.question_text[:50]}..."

class AssessmentAnswer(models.Model):
    """진단 답변 모델"""
    
    assessment = models.ForeignKey(AssetAssessment, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE)
    answer_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1: 매우 그렇지 않음, 5: 매우 그렇다"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['assessment', 'question']
    
    def __str__(self):
        return f"{self.assessment.user.username} - {self.question.question_text[:30]}"
