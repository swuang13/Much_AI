from django.urls import path
from . import views

app_name = 'reward'

urlpatterns = [
    path('', views.reward_home, name='reward_home'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('quiz-result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    path('benefits/', views.benefits_list, name='benefits_list'),
    path('activate-benefit/<int:benefit_id>/', views.activate_benefit, name='activate_benefit'),
    path('achievements/', views.achievements_list, name='achievements_list'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('update-streak/', views.update_streak, name='update_streak'),
]


