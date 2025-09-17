from decimal import Decimal
from typing import Dict, List

from django.contrib.auth.models import User

from .models import CreditScoreSnapshot


class MyDataClient:
    """MyData 스텁 클라이언트

    - 사용자가 계좌/카드/적금/프로필/신용을 모두 연동했다고 가정
    - 실제 연동 대신 합리적 더미 데이터를 반환
    """

    def get_user_profile(self, user: User) -> Dict:
        """사용자 프로필(연령/지역/주거/고용/자녀여부)

        실제 환경에서는 외부 MyData 프로필을 조회.
        """
        return {
            "age": 27,
            "region": "서울",
            "housing": "rent",  # rent | owner | family
            "employment": "freelancer",  # employee | freelancer | student
            "has_children": False,
        }

    def get_fixed_expenses(self, user: User) -> Dict:
        """고정지출(주거/통신/공과금 등)

        실제 환경에서는 최근 3개월 평균을 산출.
        """
        return {
            "housing": 400000,
            "telecom": 70000,
            "utilities": 120000,
        }

    def get_credit_snapshot(self, user: User) -> CreditScoreSnapshot:
        """신용 스냅샷 조회(없으면 생성)"""
        snapshot, _ = CreditScoreSnapshot.objects.get_or_create(
            user=user,
            defaults={
                "score": 650,
                "utilization_rate": 45,
                "on_time_payment_ratio": 97,
                "credit_age_months": 24,
                "hard_inquiries_12m": 2,
                "credit_mix_score": 40,
            },
        )
        return snapshot

    def get_monthly_income(self, user: User) -> Decimal:
        """월 소득 조회

        실제 환경에서는 계좌 입금 내역을 분석하여 월 소득을 계산.
        프리랜서의 경우 프로젝트별 수입을 합산.
        """
        # 사용자별로 다른 소득 패턴 시뮬레이션
        user_id_hash = hash(user.id) % 4

        income_patterns = {
            0: Decimal("2500000"),  # 250만원 - 저소득 프리랜서
            1: Decimal("3500000"),  # 350만원 - 중소득 프리랜서
            2: Decimal("4500000"),  # 450만원 - 중상소득 프리랜서
            3: Decimal("6000000"),  # 600만원 - 고소득 프리랜서
        }

        return income_patterns.get(user_id_hash, Decimal("3000000"))

    def get_transaction_history(self, user: User, months: int = 3) -> List[Dict]:
        """거래내역 조회

        실제 환경에서는 은행/카드사 API를 통해 최근 거래내역을 가져옴.
        """
        # 사용자별로 다른 지출 패턴 시뮬레이션
        user_id_hash = hash(user.id) % 3

        # 기본 지출 패턴
        base_patterns = {
            0: {  # 절약형
                "food": 400000,
                "transport": 150000,
                "housing": 500000,
                "healthcare": 80000,
                "entertainment": 200000,
                "shopping": 300000,
                "education": 100000,
                "other": 150000,
            },
            1: {  # 일반형
                "food": 600000,
                "transport": 200000,
                "housing": 600000,
                "healthcare": 120000,
                "entertainment": 350000,
                "shopping": 500000,
                "education": 150000,
                "other": 200000,
            },
            2: {  # 소비형
                "food": 800000,
                "transport": 250000,
                "housing": 700000,
                "healthcare": 150000,
                "entertainment": 500000,
                "shopping": 800000,
                "education": 200000,
                "other": 300000,
            },
        }

        pattern = base_patterns.get(user_id_hash, base_patterns[1])
        transactions = []

        # 최근 3개월 거래내역 생성
        import random
        from datetime import datetime, timedelta

        for month_offset in range(months):
            month_date = datetime.now() - timedelta(days=30 * month_offset)

            for category, base_amount in pattern.items():
                # 월별 변동성 추가 (±20%)
                variation = random.uniform(0.8, 1.2)
                amount = int(base_amount * variation)

                # 월별 5-10건의 거래 생성
                num_transactions = random.randint(5, 10)
                for _ in range(num_transactions):
                    transaction_amount = amount // num_transactions
                    if transaction_amount > 0:
                        transactions.append(
                            {
                                "date": (
                                    month_date - timedelta(days=random.randint(0, 30))
                                ).strftime("%Y-%m-%d"),
                                "category": category,
                                "amount": transaction_amount,
                                "description": f"{category} 지출",
                                "account": f"계좌{random.randint(1, 3)}",
                            }
                        )

        # 날짜순 정렬
        transactions.sort(key=lambda x: x["date"], reverse=True)
        return transactions

    def get_income_history(self, user: User, months: int = 12) -> List[Decimal]:
        """최근 12개월 소득 이력 조회

        실제 환경에서는 계좌 입금 내역을 분석하여 월별 소득을 계산.
        """
        base_income = self.get_monthly_income(user)

        # 프리랜서 특성상 변동성이 있는 소득 패턴 시뮬레이션
        import random

        monthly_incomes = []
        for month in range(months):
            # 계절성과 변동성 반영
            seasonal_factor = self._get_seasonal_factor(month)
            volatility_factor = random.uniform(0.7, 1.3)  # ±30% 변동

            monthly_income = base_income * Decimal(
                str(seasonal_factor * volatility_factor)
            )
            monthly_incomes.append(monthly_income)

        return monthly_incomes

    def _get_seasonal_factor(self, month_offset: int) -> float:
        """계절성 팩터 계산 (프리랜서 특성 반영)"""
        # 현재 월에서 역산
        current_month = (12 - month_offset) % 12

        # 프리랜서 특성상 연말/연초에 프로젝트가 많은 경향
        seasonal_factors = {
            0: 1.1,  # 1월: 신년 프로젝트
            1: 0.9,  # 2월: 설날 연휴
            2: 1.0,  # 3월: 정상
            3: 1.0,  # 4월: 정상
            4: 1.0,  # 5월: 정상
            5: 0.95,  # 6월: 하반기 준비
            6: 1.0,  # 7월: 정상
            7: 0.9,  # 8월: 여름휴가
            8: 1.05,  # 9월: 하반기 시작
            9: 1.1,  # 10월: 연말 프로젝트 시작
            10: 1.1,  # 11월: 연말 프로젝트
            11: 1.2,  # 12월: 연말 마무리
        }

        return seasonal_factors.get(current_month, 1.0)

    def get_account_summary(self, user: User) -> Dict:
        """계좌 요약 정보 조회"""
        return {
            "total_balance": Decimal("2500000"),  # 총 잔액
            "checking_balance": Decimal("800000"),  # 당좌 계좌
            "savings_balance": Decimal("1200000"),  # 적금 계좌
            "investment_balance": Decimal("500000"),  # 투자 계좌
            "monthly_income_avg": self.get_monthly_income(user),
            "monthly_expense_avg": Decimal("1800000"),  # 월 평균 지출
        }

    def get_loan_info(self, user: User) -> List[Dict]:
        """대출 정보 조회"""
        return [
            {
                "type": "신용대출",
                "balance": Decimal("5000000"),
                "interest_rate": 6.5,
                "monthly_payment": Decimal("150000"),
                "remaining_months": 36,
            },
            {
                "type": "자동차할부",
                "balance": Decimal("8000000"),
                "interest_rate": 4.2,
                "monthly_payment": Decimal("200000"),
                "remaining_months": 48,
            },
        ]

    def get_credit_card_info(self, user: User) -> List[Dict]:
        """신용카드 정보 조회"""
        return [
            {
                "card_name": "프리미엄 카드",
                "limit": Decimal("3000000"),
                "used_amount": Decimal("900000"),
                "utilization_rate": 30.0,
                "due_date": "2024-10-15",
            },
            {
                "card_name": "일반 카드",
                "limit": Decimal("2000000"),
                "used_amount": Decimal("600000"),
                "utilization_rate": 30.0,
                "due_date": "2024-10-20",
            },
        ]
