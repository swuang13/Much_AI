from django.urls import path
from . import views

app_name = "asset"

urlpatterns = [
    path("", views.home, name="home"),
    path("assess/", views.assess, name="assess"),  # POST 처리
    path("demo-login/", views.demo_login, name="demo_login"),  # POST
    path("assess-mydata/", views.assess_mydata, name="assess_mydata"),  # POST
    path("assessments/", views.assessment_list, name="assessment_list"),
    path("assessments/<int:pk>/", views.assessment_detail, name="assessment_detail"),
    path("auth/", views.auth_page, name="auth_page"),
    path("login/", views.user_login, name="login"),
    path("register/", views.user_register, name="register"),
    path("logout/", views.user_logout, name="logout"),
    path("chat/<int:pk>/", views.chat_with_assessment, name="chat"),
]
