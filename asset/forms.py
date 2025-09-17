from django import forms

class AssessmentInputForm(forms.Form):
    credit_info = forms.CharField(
        label="추가 자유 기입 정보",
        widget=forms.Textarea(attrs={
            "rows":4,
            "placeholder":"예) 최근 지출 패턴 변화, 목표(비상금·내집마련 등), 기타 참고사항"
        })
    )
