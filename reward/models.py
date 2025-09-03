from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class UserProfile(models.Model):
    """사용자 프로필 및 포인트 관리"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reward_profile')
    total_points = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    experience_points = models.IntegerField(default=0)
    experience_to_next_level = models.IntegerField(default=100)
    
    # 성장 지표
    quizzes_completed = models.IntegerField(default=0)
    assessments_completed = models.IntegerField(default=0)
    plans_created = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)  # 연속 활동 일수
    last_activity_date = models.DateField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Level {self.current_level}"
    
    def add_points(self, points, reason="활동"):
        """포인트 추가"""
        self.total_points += points
        self.experience_points += points
        
        # 레벨업 체크
        while self.experience_points >= self.experience_to_next_level:
            self.level_up()
        
        self.save()
        
        # 포인트 획득 기록
        PointHistory.objects.create(
            user_profile=self,
            points=points,
            reason=reason
        )
    
    def level_up(self):
        """레벨업"""
        self.experience_points -= self.experience_to_next_level
        self.current_level += 1
        self.experience_to_next_level = int(self.experience_to_next_level * 1.2)  # 20% 증가
        
        # 레벨업 보상
        level_reward = self.current_level * 100
        self.total_points += level_reward
        
        # 레벨업 기록
        LevelUpHistory.objects.create(
            user_profile=self,
            new_level=self.current_level,
            reward_points=level_reward
        )

class PointHistory(models.Model):
    """포인트 획득/사용 기록"""
    
    POINT_TYPES = [
        ('earn', '획득'),
        ('spend', '사용'),
        ('bonus', '보너스'),
        ('penalty', '차감'),
    ]
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='point_history')
    points = models.IntegerField()
    point_type = models.CharField(max_length=10, choices=POINT_TYPES, default='earn')
    reason = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.points}점 ({self.reason})"

class LevelUpHistory(models.Model):
    """레벨업 기록"""
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='level_up_history')
    new_level = models.IntegerField()
    reward_points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - Level {self.new_level} 달성!"

class Quiz(models.Model):
    """금융 리터러시 퀴즈"""
    
    DIFFICULTY_LEVELS = [
        ('easy', '쉬움'),
        ('medium', '보통'),
        ('hard', '어려움'),
    ]
    
    CATEGORIES = [
        ('basic', '기초 금융'),
        ('investment', '투자'),
        ('credit', '신용'),
        ('insurance', '보험'),
        ('tax', '세금'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORIES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS)
    points_reward = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()})"

class QuizQuestion(models.Model):
    """퀴즈 질문"""
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    explanation = models.TextField(blank=True)  # 정답 설명
    points = models.IntegerField(default=5)
    order = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"

class QuizOption(models.Model):
    """퀴즈 선택지"""
    
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    order = models.CharField(max_length=1)  # A, B, C, D
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question.question_text[:30]} - {self.option_text}"

class QuizAttempt(models.Model):
    """퀴즈 시도 기록"""
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.quiz.title} ({self.score}/{self.max_score})"

class FinancialBenefit(models.Model):
    """금융사 제휴 혜택"""
    
    BENEFIT_TYPES = [
        ('loan_rate', '대출 금리 인하'),
        ('card_benefit', '카드 추가 혜택'),
        ('savings_rate', '예금 금리 인상'),
        ('investment_fee', '투자 수수료 할인'),
        ('insurance_discount', '보험료 할인'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    benefit_type = models.CharField(max_length=20, choices=BENEFIT_TYPES)
    partner_bank = models.CharField(max_length=100)
    required_level = models.IntegerField(default=1)
    required_points = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.partner_bank}"

class UserBenefit(models.Model):
    """사용자 혜택 이용 기록"""
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='benefits')
    financial_benefit = models.ForeignKey(FinancialBenefit, on_delete=models.CASCADE, related_name='user_benefits')
    points_spent = models.IntegerField()
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-activated_at']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.financial_benefit.title}"

class Achievement(models.Model):
    """업적 시스템"""
    
    ACHIEVEMENT_TYPES = [
        ('quiz', '퀴즈'),
        ('assessment', '진단'),
        ('plan', '플랜'),
        ('streak', '연속 활동'),
        ('level', '레벨'),
    ]
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    icon = models.CharField(max_length=50, blank=True)  # 아이콘 클래스명
    points_reward = models.IntegerField(default=50)
    requirement_value = models.IntegerField(default=1)  # 달성 조건 값
    is_hidden = models.BooleanField(default=False)  # 숨겨진 업적
    
    def __str__(self):
        return self.title

class UserAchievement(models.Model):
    """사용자 업적 달성 기록"""
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='user_achievements')
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user_profile', 'achievement']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.achievement.title}"
