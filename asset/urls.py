from django.urls import path
from . import views

app_name = 'asset'

urlpatterns = [
    path('', views.home, name='home'),
    path('list/', views.assessment_list, name='assessment_list'),
    path('start/', views.start_assessment, name='start_assessment'),
    path('take/<int:assessment_id>/', views.take_assessment, name='take_assessment'),
    path('result/<int:assessment_id>/', views.assessment_result, name='assessment_result'),
]


