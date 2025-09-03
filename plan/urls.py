from django.urls import path
from . import views

app_name = 'plan'

urlpatterns = [
    path('', views.plan_home, name='plan_home'),
    path('income-prediction/', views.income_prediction, name='income_prediction'),
    path('create-plan/<int:prediction_id>/', views.create_financial_plan, name='create_financial_plan'),
    path('detail/<int:plan_id>/', views.plan_detail, name='plan_detail'),
    path('list/', views.plan_list, name='plan_list'),
]
