from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class AssetProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="asset_profile")
    credit_info = models.TextField(blank=True, help_text="마이데이터 요약(대출/카드/한도 등)")
    income_6m = models.DecimalField("6개월 총 수입", max_digits=14, decimal_places=2,
                                    validators=[MinValueValidator(0)])
    expense_6m = models.DecimalField("6개월 총 지출", max_digits=14, decimal_places=2,
                                     validators=[MinValueValidator(0)])
    credit_score = models.IntegerField("신용점수",
                                       validators=[MinValueValidator(0), MaxValueValidator(1000)])
    # 월별 데이터(최근 6개월)
    # 최근 6개월 월별 금액(만원 단위 정수 리스트) 예: [550, 600, 580, 620, 600, 650]
    income_monthly = models.JSONField(default=list, blank=True)
    expense_monthly = models.JSONField(default=list, blank=True)
    # 현실 자산/부채 속성
    housing_loan_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    auto_loan_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit_card_limit_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    savings_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    investment_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    delinquency_last12m = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AssetProfile for {self.user}" 

class Assessment(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    credit_info = models.TextField(help_text="신용정보 요약(대출/카드/한도 등 자유기입)")
    income_6m = models.DecimalField("6개월 총 수입", max_digits=14, decimal_places=2,
                                    validators=[MinValueValidator(0)])
    expense_6m = models.DecimalField("6개월 총 지출", max_digits=14, decimal_places=2,
                                     validators=[MinValueValidator(0)])
    credit_score = models.IntegerField("신용점수",
                                       validators=[MinValueValidator(0), MaxValueValidator(1000)])
    result = models.JSONField(null=True, blank=True)  # LLM 결과(JSON)
    grade = models.CharField(max_length=2, blank=True)  # 빠른 접근용(A/B/C/D 등)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Assessment#{self.pk} - {self.created_at:%Y-%m-%d}"
