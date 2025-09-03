from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .models import AssetAssessment, AssessmentQuestion, AssessmentAnswer

def home(request):
    """메인 페이지 - 자산 관리 역량 진단 소개"""
    return render(request, 'asset/home.html')

@login_required
def assessment_list(request):
    """사용자의 진단 기록 목록"""
    assessments = AssetAssessment.objects.filter(user=request.user)
    return render(request, 'asset/assessment_list.html', {
        'assessments': assessments
    })

@login_required
def start_assessment(request):
    """새로운 진단 시작"""
    if request.method == 'POST':
        assessment_type = request.POST.get('assessment_type', 'basic')
        
        # 기존 진행 중인 진단이 있다면 완료 처리
        existing_assessment = AssetAssessment.objects.filter(
            user=request.user,
            total_score=0
        ).first()
        
        if existing_assessment:
            existing_assessment.delete()
        
        # 새 진단 생성
        assessment = AssetAssessment.objects.create(
            user=request.user,
            assessment_type=assessment_type
        )
        
        return redirect('asset:take_assessment', assessment_id=assessment.id)
    
    return render(request, 'asset/start_assessment.html')

@login_required
def take_assessment(request, assessment_id):
    """진단 진행"""
    assessment = get_object_or_404(AssetAssessment, id=assessment_id, user=request.user)
    
    if request.method == 'POST':
        # 답변 저장
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = int(key.split('_')[1])
                question = get_object_or_404(AssessmentQuestion, id=question_id)
                
                AssessmentAnswer.objects.update_or_create(
                    assessment=assessment,
                    question=question,
                    defaults={'answer_value': int(value)}
                )
        
        # 진단 완료 처리
        calculate_scores(assessment)
        return redirect('asset:assessment_result', assessment_id=assessment.id)
    
    # 진단 질문 가져오기
    questions = AssessmentQuestion.objects.filter(is_active=True).order_by('category', 'id')
    
    return render(request, 'asset/take_assessment.html', {
        'assessment': assessment,
        'questions': questions
    })

@login_required
def assessment_result(request, assessment_id):
    """진단 결과 표시"""
    assessment = get_object_or_404(AssetAssessment, id=assessment_id, user=request.user)
    
    if assessment.total_score == 0:
        messages.error(request, '진단이 완료되지 않았습니다.')
        return redirect('asset:take_assessment', assessment_id=assessment.id)
    
    return render(request, 'asset/assessment_result.html', {
        'assessment': assessment
    })

def calculate_scores(assessment):
    """진단 점수 계산"""
    answers = assessment.answers.all()
    
    if not answers.exists():
        return
    
    # 카테고리별 점수 계산
    category_scores = {}
    total_weight = 0
    
    for answer in answers:
        category = answer.question.category
        weight = answer.question.weight
        
        if category not in category_scores:
            category_scores[category] = {'total': 0, 'weight': 0}
        
        category_scores[category]['total'] += answer.answer_value * weight
        category_scores[category]['weight'] += weight
        total_weight += weight
    
    # 점수 계산 및 저장
    for category, data in category_scores.items():
        if data['weight'] > 0:
            score = int((data['total'] / data['weight']) * 20)  # 5점 만점을 100점으로 변환
            
            if category == 'financial_literacy':
                assessment.financial_literacy_score = score
            elif category == 'risk_management':
                assessment.risk_management_score = score
            elif category == 'investment':
                assessment.investment_knowledge_score = score
            elif category == 'debt':
                assessment.debt_management_score = score
    
    # 전체 점수 계산
    if total_weight > 0:
        total_score = sum(
            answer.answer_value * answer.question.weight 
            for answer in answers
        )
        assessment.total_score = int((total_score / total_weight) * 20)
    
    # 피드백 및 권장사항 생성
    assessment.feedback = generate_feedback(assessment)
    assessment.recommendations = generate_recommendations(assessment)
    
    assessment.save()

def generate_feedback(assessment):
    """피드백 생성"""
    feedback = []
    
    if assessment.financial_literacy_score < 60:
        feedback.append("금융 리터러시 향상이 필요합니다.")
    elif assessment.financial_literacy_score >= 80:
        feedback.append("금융 리터러시가 우수합니다!")
    
    if assessment.risk_management_score < 60:
        feedback.append("위험 관리 능력을 향상시켜야 합니다.")
    elif assessment.risk_management_score >= 80:
        feedback.append("위험 관리 능력이 뛰어납니다!")
    
    if assessment.investment_knowledge_score < 60:
        feedback.append("투자 지식을 쌓아야 합니다.")
    elif assessment.investment_knowledge_score >= 80:
        feedback.append("투자 지식이 풍부합니다!")
    
    if assessment.debt_management_score < 60:
        feedback.append("부채 관리에 주의가 필요합니다.")
    elif assessment.debt_management_score >= 80:
        feedback.append("부채 관리가 체계적입니다!")
    
    return " ".join(feedback) if feedback else "전반적으로 균형잡힌 자산 관리 능력을 보여줍니다."

def generate_recommendations(assessment):
    """권장사항 생성"""
    recommendations = []
    
    if assessment.financial_literacy_score < 60:
        recommendations.append("금융 관련 서적 읽기, 온라인 강의 수강")
    
    if assessment.risk_management_score < 60:
        recommendations.append("보험 상품 검토, 비상금 확보")
    
    if assessment.investment_knowledge_score < 60:
        recommendations.append("투자 기초 교육, 소액 투자 시작")
    
    if assessment.debt_management_score < 60:
        recommendations.append("부채 현황 점검, 상환 계획 수립")
    
    return " | ".join(recommendations) if recommendations else "현재 수준을 유지하면서 지속적인 학습을 권장합니다."
