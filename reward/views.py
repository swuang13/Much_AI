from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
import json
from datetime import date, timedelta

from .models import (
    UserProfile, PointHistory, LevelUpHistory, Quiz, QuizQuestion, 
    QuizOption, QuizAttempt, FinancialBenefit, UserBenefit, 
    Achievement, UserAchievement, QuizAnswer
)

def reward_home(request):
    """리워드 시스템 메인 페이지"""
    return render(request, 'reward/reward_home.html')

@login_required
def profile_dashboard(request):
    """사용자 프로필 대시보드"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # 최근 활동 기록
    recent_points = PointHistory.objects.filter(user_profile=profile).order_by('-created_at')[:10]
    recent_achievements = UserAchievement.objects.filter(user_profile=profile).order_by('-earned_at')[:5]
    recent_level_ups = LevelUpHistory.objects.filter(user_profile=profile).order_by('-created_at')[:5]
    
    # 사용 가능한 혜택
    available_benefits = FinancialBenefit.objects.filter(
        is_active=True,
        required_level__lte=profile.current_level,
        required_points__lte=profile.total_points
    )
    
    # 업적 진행 상황
    achievements = Achievement.objects.filter(is_active=True)
    user_achievements = UserAchievement.objects.filter(user_profile=profile)
    achievement_progress = []
    
    for achievement in achievements:
        if user_achievements.filter(achievement=achievement).exists():
            progress = 100
            status = "달성"
        else:
            # 진행률 계산 (간단한 예시)
            if achievement.achievement_type == 'quiz':
                current_value = profile.quizzes_completed
            elif achievement.achievement_type == 'assessment':
                current_value = profile.assessments_completed
            elif achievement.achievement_type == 'plan':
                current_value = profile.plans_created
            elif achievement.achievement_type == 'streak':
                current_value = profile.streak_days
            elif achievement.achievement_type == 'level':
                current_value = profile.current_level
            else:
                current_value = 0
            
            progress = min(int((current_value / achievement.requirement_value) * 100), 100)
            status = "진행중" if progress < 100 else "달성"
        
        achievement_progress.append({
            'achievement': achievement,
            'progress': progress,
            'status': status,
            'current_value': current_value if 'current_value' in locals() else 0
        })
    
    context = {
        'profile': profile,
        'recent_points': recent_points,
        'recent_achievements': recent_achievements,
        'recent_level_ups': recent_level_ups,
        'available_benefits': available_benefits,
        'achievement_progress': achievement_progress,
    }
    
    return render(request, 'reward/profile_dashboard.html', context)

@login_required
def quiz_list(request):
    """퀴즈 목록"""
    quizzes = Quiz.objects.filter(is_active=True).order_by('difficulty', 'category')
    
    # 사용자가 완료한 퀴즈
    completed_quizzes = QuizAttempt.objects.filter(user_profile__user=request.user)
    completed_quiz_ids = [attempt.quiz.id for attempt in completed_quizzes]
    
    context = {
        'quizzes': quizzes,
        'completed_quiz_ids': completed_quiz_ids,
    }
    
    return render(request, 'reward/quiz_list.html', context)

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # 이미 응시했는지 확인
    existing = QuizAttempt.objects.filter(user_profile=profile, quiz=quiz) \
                                  .order_by('-completed_at').first()

    # ★ 테스트 우회: 관리자이거나 ?retry=1 이면 통과
    allow_retry = request.user.is_staff or request.GET.get('retry') == '1'

    if existing and not allow_retry:
        messages.warning(request, '이미 응시한 퀴즈입니다. 다시 풀 수 없습니다.')
        return redirect('reward:quiz_result', attempt_id=existing.id)

    if request.method == 'POST':
        attempt = QuizAttempt.objects.create(user_profile=profile, quiz=quiz, score=0, max_score=0)
        score = 0
        max_score = 0

        for question in quiz.questions.prefetch_related('options'):
            max_score += question.points

            selected_letter = request.POST.get(f'question_{question.id}')
            selected_option = question.options.filter(order=selected_letter).first() if selected_letter else None
            is_correct = bool(selected_option and selected_option.is_correct)

            if is_correct:
                score += question.points

            QuizAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_order=selected_letter,
                selected_option=selected_option,
                is_correct=is_correct,
                points_awarded=question.points if is_correct else 0,
            )

        attempt.score = score
        attempt.max_score = max_score
        attempt.save()

        if score > 0 and max_score > 0:
            points_earned = int((score / max_score) * quiz.points_reward)
            profile.add_points(points_earned, f"퀴즈: {quiz.title}")
        profile.quizzes_completed += 1
        profile.save()
        check_achievements(profile)

        messages.success(request, f'퀴즈 완료! {score}/{max_score}점')
        return redirect('reward:quiz_result', attempt_id=attempt.id)

    return render(request, 'reward/take_quiz.html', {'quiz': quiz, 'questions': quiz.questions.all()})


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz', 'user_profile__user')
        .prefetch_related('answers__question__options', 'answers__selected_option'),
        id=attempt_id, user_profile__user=request.user
    )
    return render(request, 'reward/quiz_result.html', {
        'attempt': attempt, 'quiz': attempt.quiz, 'answers': attempt.answers.all()
    })


@login_required
def benefits_list(request):
    """금융 혜택 목록"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # 모든 혜택
    all_benefits = FinancialBenefit.objects.filter(is_active=True).order_by('required_level', 'required_points')
    
    # 사용자가 이용 중인 혜택
    user_benefits = UserBenefit.objects.filter(user_profile=profile, is_active=True)
    
    context = {
        'profile': profile,
        'all_benefits': all_benefits,
        'user_benefits': user_benefits,
    }
    
    return render(request, 'reward/benefits_list.html', context)

@login_required
def activate_benefit(request, benefit_id):
    """혜택 활성화"""
    if request.method == 'POST':
        benefit = get_object_or_404(FinancialBenefit, id=benefit_id, is_active=True)
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # 조건 확인
        if profile.current_level < benefit.required_level:
            messages.error(request, f'레벨 {benefit.required_level} 이상이 필요합니다.')
            return redirect('reward:benefits_list')
        
        if profile.total_points < benefit.required_points:
            messages.error(request, f'포인트가 부족합니다. 필요: {benefit.required_points}점')
            return redirect('reward:benefits_list')
        
        # 이미 활성화된 혜택인지 확인
        if UserBenefit.objects.filter(user_profile=profile, financial_benefit=benefit, is_active=True).exists():
            messages.warning(request, '이미 활성화된 혜택입니다.')
            return redirect('reward:benefits_list')
        
        # 혜택 활성화
        user_benefit = UserBenefit.objects.create(
            user_profile=profile,
            financial_benefit=benefit,
            points_spent=benefit.required_points
        )
        
        # 포인트 차감
        profile.total_points -= benefit.required_points
        profile.save()
        
        # 포인트 사용 기록
        PointHistory.objects.create(
            user_profile=profile,
            points=-benefit.required_points,
            point_type='spend',
            reason=f"혜택 활성화: {benefit.title}"
        )
        
        messages.success(request, f'{benefit.title} 혜택이 활성화되었습니다!')
        return redirect('reward:benefits_list')
    
    return redirect('reward:benefits_list')

@login_required
def achievements_list(request):
    """업적 목록"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # 모든 업적
    achievements = Achievement.objects.filter(is_active=True).order_by('achievement_type', 'requirement_value')
    
    # 사용자가 달성한 업적
    user_achievements = UserAchievement.objects.filter(user_profile=profile)
    earned_achievement_ids = [ua.achievement.id for ua in user_achievements]
    
    context = {
        'profile': profile,
        'achievements': achievements,
        'earned_achievement_ids': earned_achievement_ids,
    }
    
    return render(request, 'reward/achievements_list.html', context)

@login_required
def leaderboard(request):
    """리더보드 + 지난 7일 변화량 뱃지"""
    level_leaders  = UserProfile.objects.order_by('-current_level', '-experience_points')[:20]
    point_leaders  = UserProfile.objects.order_by('-total_points')[:20]
    streak_leaders = UserProfile.objects.order_by('-streak_days')[:20]

    since = timezone.now() - timedelta(days=7)

    ph = PointHistory.objects.filter(created_at__gte=since)
    points_delta = {r['user_profile']: r['delta'] or 0
                    for r in ph.values('user_profile').annotate(delta=Sum('points'))}

    lh = LevelUpHistory.objects.filter(created_at__gte=since)
    levels_delta = {r['user_profile']: r['delta']
                    for r in lh.values('user_profile').annotate(delta=Count('id'))}

    act = (ph.annotate(day=TruncDate('created_at'))
             .values('user_profile', 'day').distinct()
             .values('user_profile').annotate(cnt=Count('day')))
    active_days_7d = {r['user_profile']: r['cnt'] for r in act}

    def attach(board):
        return [{
            'profile': p,
            'delta_points': points_delta.get(p.id, 0),
            'delta_levels': levels_delta.get(p.id, 0),
            'active_days_7d': active_days_7d.get(p.id, 0),
        } for p in board]

    context = {
        'since_date': since.date(),

        'level_board': attach(level_leaders),
        'point_board': attach(point_leaders),
        'streak_board': attach(streak_leaders),

        'level_leaders': level_leaders,
        'point_leaders': point_leaders,
        'streak_leaders': streak_leaders,
    }
    return render(request, 'reward/leaderboard.html', context)


def check_achievements(profile):
    """업적 달성 체크"""
    achievements = Achievement.objects.filter(is_active=True)
    
    for achievement in achievements:
        # 이미 달성한 업적은 스킵
        if UserAchievement.objects.filter(user_profile=profile, achievement=achievement).exists():
            continue
        
        # 달성 조건 확인
        if achievement.achievement_type == 'quiz':
            current_value = profile.quizzes_completed
        elif achievement.achievement_type == 'assessment':
            current_value = profile.assessments_completed
        elif achievement.achievement_type == 'plan':
            current_value = profile.plans_created
        elif achievement.achievement_type == 'streak':
            current_value = profile.streak_days
        elif achievement.achievement_type == 'level':
            current_value = profile.current_level
        else:
            continue
        
        # 업적 달성 확인
        if current_value >= achievement.requirement_value:
            UserAchievement.objects.create(
                user_profile=profile,
                achievement=achievement
            )
            
            # 포인트 지급
            profile.add_points(achievement.points_reward, f"업적 달성: {achievement.title}")
            
            # 메시지 표시 (실제로는 AJAX나 세션을 통해 처리)
            print(f"업적 달성: {achievement.title}")

@login_required
def update_streak(request):
    """연속 활동일 업데이트 (일일 로그인 등)"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    today = date.today()
    
    if profile.last_activity_date:
        days_diff = (today - profile.last_activity_date).days
        
        if days_diff == 1:
            # 연속 활동
            profile.streak_days += 1
        elif days_diff > 1:
            # 연속 활동 끊김
            profile.streak_days = 1
        # days_diff == 0이면 같은 날이므로 변경 없음
    else:
        # 첫 활동
        profile.streak_days = 1
    
    profile.last_activity_date = today
    profile.save()
    
    # 연속 활동 보상
    if profile.streak_days in [7, 30, 100]:
        bonus_points = profile.streak_days * 10
        profile.add_points(bonus_points, f"연속 활동 {profile.streak_days}일 달성!")
    
    # 업적 체크
    check_achievements(profile)
    
    return JsonResponse({'status': 'success', 'streak_days': profile.streak_days})
