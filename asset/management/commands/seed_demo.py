from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from asset.models import AssetProfile


class Command(BaseCommand):
    help = "Seed or fix demo user/profile with realistic monthly data"

    def handle(self, *args, **options):
        username = "demo_user"
        password = "demo_pass_1234"
        user, created = User.objects.get_or_create(username=username, defaults={"email": "demo@example.com"})
        if created:
            user.set_password(password)
            user.save()

        profile, _ = AssetProfile.objects.get_or_create(user=user)
        profile.credit_info = "주담대 3.2억 잔액 / 자동차할부 1800만 / 카드한도 2000만 / 비상금 600만"
        profile.income_monthly = [550, 600, 580, 620, 600, 650]
        profile.expense_monthly = [360, 390, 370, 410, 380, 420]
        profile.income_6m = sum(profile.income_monthly) * 10000
        profile.expense_6m = sum(profile.expense_monthly) * 10000
        profile.credit_score = 720
        profile.housing_loan_balance = 320000000
        profile.auto_loan_balance = 18000000
        profile.credit_card_limit_total = 20000000
        profile.savings_balance = 6000000
        profile.investment_balance = 15000000
        profile.delinquency_last12m = False
        profile.save()

        self.stdout.write(self.style.SUCCESS("Demo user/profile seeded and fixed."))





