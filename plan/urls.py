from django.urls import path

from . import views

app_name = "plan"

urlpatterns = [
    path("", views.plan_home, name="plan_home"),
    path("quick-start/", views.quick_start, name="quick_start"),
    path("income-prediction/", views.income_prediction, name="income_prediction"),
    path(
        "create-plan/<int:prediction_id>/",
        views.create_financial_plan,
        name="create_financial_plan",
    ),
    path("detail/<int:plan_id>/", views.plan_detail, name="plan_detail"),
    path("list/", views.plan_list, name="plan_list"),
    path("analytics/<int:plan_id>/", views.plan_analytics, name="plan_analytics"),
    path("smart-plan/", views.smart_plan_generator, name="smart_plan_generator"),
    path("smart-plan/result/", views.smart_plan_result, name="smart_plan_result"),
    # API 엔드포인트
    path("api/predict-income/", views.api_predict_income, name="api_predict_income"),
    path("api/generate-plan/", views.api_generate_plan, name="api_generate_plan"),
    path(
        "api/personal-coaching/<int:plan_id>/",
        views.api_personal_coaching,
        name="api_personal_coaching",
    ),
    path("api/apply-kpi/<int:plan_id>/", views.api_apply_kpi, name="api_apply_kpi"),
    path("api/smart-plan/", views.api_smart_plan, name="api_smart_plan"),
]

