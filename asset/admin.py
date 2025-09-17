# asset/admin.py
from django.contrib import admin
from .models import Assessment

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "grade", "credit_score", "income_6m", "expense_6m")
    list_filter = ("grade", "created_at")
    search_fields = ("credit_info",)
    readonly_fields = ("created_at",)
