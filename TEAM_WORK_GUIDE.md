# Much 팀원별 작업 가이드 👥

각 팀원이 담당 기능을 구현할 때 참고할 수 있는 상세 작업 가이드입니다.

## 🎯 **팀 구성 및 담당 기능**

### **담당자 1: 자산진단 (Asset App)**
- **담당 영역**: 자산 관리 역량 진단 시스템
- **주요 기능**: 진단 질문, 점수 계산, 피드백 생성
- **작업 우선순위**: 1순위

### **담당자 2: AI플랜 (Plan App)**
- **담당 영역**: AI 기반 자산 관리 플랜 생성
- **주요 기능**: 소득 예측, 플랜 생성, 신용등급 관리
- **작업 우선순위**: 2순위

### **담당자 3: 성장리워드 (Reward App)**
- **담당 영역**: 게이미피케이션 및 리워드 시스템
- **주요 기능**: 퀴즈, 포인트, 업적, 혜택
- **작업 우선순위**: 3순위

---

## 🔧 **담당자 1: 자산진단 (Asset App)**

### **구현해야 할 페이지들**

#### 1. 진단 질문 입력 폼 (`templates/asset/question_form.html`)
```html
<!-- 구현 예시 -->
<form method="post" class="diagnosis-form">
    <div class="question-section">
        <h4>금융 리터러시</h4>
        <div class="question">
            <p>1. 복리 효과에 대해 이해하고 있나요?</p>
            <div class="options">
                <label><input type="radio" name="q1" value="1"> 전혀 모름</label>
                <label><input type="radio" name="q1" value="2"> 조금 앎</label>
                <label><input type="radio" name="q1" value="3"> 보통</label>
                <label><input type="radio" name="q1" value="4"> 잘 앎</label>
                <label><input type="radio" name="q1" value="5"> 매우 잘 앎</label>
            </div>
        </div>
    </div>
    <!-- 추가 질문들... -->
</form>
```

#### 2. 진단 결과 표시 (`templates/asset/result.html`)
```html
<!-- 구현 예시 -->
<div class="result-summary">
    <div class="total-score">
        <h2>종합 점수: <span class="score">{{ total_score }}</span></h2>
    </div>
    
    <div class="category-scores">
        <div class="category">
            <h4>금융 리터러시</h4>
            <div class="progress">
                <div class="progress-bar" style="width: {{ financial_score }}%"></div>
            </div>
            <span>{{ financial_score }}점</span>
        </div>
        <!-- 추가 카테고리들... -->
    </div>
</div>
```

#### 3. 진단 기록 목록 (`templates/asset/history.html`)
```html
<!-- 구현 예시 -->
<div class="history-list">
    {% for assessment in assessments %}
    <div class="history-item">
        <div class="date">{{ assessment.created_at|date:"Y-m-d" }}</div>
        <div class="score">{{ assessment.total_score }}점</div>
        <div class="type">{{ assessment.get_assessment_type_display }}</div>
        <a href="{% url 'asset:result' assessment.id %}" class="btn btn-sm btn-primary">결과보기</a>
    </div>
    {% endfor %}
</div>
```

### **필요한 모델 수정사항**
```python
# asset/models.py에 추가할 필드들
class AssessmentQuestion:
    # 기존 필드 + 추가 필드
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    explanation = models.TextField(blank=True)  # 정답 설명
    
class AssetAssessment:
    # 기존 필드 + 추가 필드
    completion_time = models.IntegerField(default=0)  # 완료 시간(분)
    user_feedback = models.TextField(blank=True)  # 사용자 피드백
```

### **점수 계산 알고리즘 예시**
```python
def calculate_category_score(answers, category):
    """카테고리별 점수 계산"""
    category_answers = [a for a in answers if a.question.category == category]
    if not category_answers:
        return 0
    
    total_weight = sum(a.question.weight for a in category_answers)
    weighted_sum = sum(a.answer_value * a.question.weight for a in category_answers)
    
    return int((weighted_sum / total_weight) * 20)  # 5점 만점을 100점으로 변환
```

---

## 🧠 **담당자 2: AI플랜 (Plan App)**

### **구현해야 할 페이지들**

#### 1. 소득 데이터 입력 (`templates/plan/income_input.html`)
```html
<!-- 구현 예시 -->
<form method="post" class="income-form">
    <div class="income-type-selection">
        <h4>소득 유형 선택</h4>
        <select name="income_type" required>
            <option value="freelance">프리랜서</option>
            <option value="business">사업자</option>
            <option value="employee">급여소득자</option>
            <option value="mixed">혼합소득</option>
        </select>
    </div>
    
    <div class="monthly-income-input">
        <h4>최근 12개월 소득 입력</h4>
        {% for month in months %}
        <div class="month-input">
            <label>{{ month }}월 소득</label>
            <input type="number" name="monthly_income_{{ forloop.counter }}" 
                   placeholder="월 소득을 입력하세요" required>
        </div>
        {% endfor %}
    </div>
</form>
```

#### 2. 플랜 생성 설정 (`templates/plan/plan_settings.html`)
```html
<!-- 구현 예시 -->
<form method="post" class="plan-settings-form">
    <div class="plan-type-selection">
        <h4>플랜 유형 선택</h4>
        <div class="plan-options">
            <label><input type="radio" name="plan_type" value="conservative"> 보수형</label>
            <label><input type="radio" name="plan_type" value="moderate" checked> 균형형</label>
            <label><input type="radio" name="plan_type" value="aggressive"> 공격형</label>
        </div>
    </div>
    
    <div class="target-settings">
        <h4>목표 설정</h4>
        <div class="setting-item">
            <label>목표 저축률 (%)</label>
            <input type="number" name="target_savings_rate" value="20" min="5" max="80">
        </div>
        <div class="setting-item">
            <label>비상금 목표 (원)</label>
            <input type="number" name="emergency_fund_target" placeholder="예: 3000000">
        </div>
    </div>
</form>
```

#### 3. 플랜 결과 표시 (`templates/plan/plan_result.html`)
```html
<!-- 구현 예시 -->
<div class="plan-summary">
    <div class="income-prediction">
        <h3>AI 소득 예측 결과</h3>
        <div class="prediction-details">
            <p>예상 월 소득: <strong>{{ predicted_monthly_income|floatformat:0 }}원</strong></p>
            <p>예상 연 소득: <strong>{{ predicted_yearly_income|floatformat:0 }}원</strong></p>
            <p>신뢰도: <strong>{{ confidence_level|floatformat:1 }}%</strong></p>
        </div>
    </div>
    
    <div class="monthly-plan">
        <h3>월별 계획</h3>
        <div class="plan-chart">
            <!-- 차트 또는 테이블 형태로 표시 -->
        </div>
    </div>
</div>
```

### **AI 소득 예측 모델 개선 예시**
```python
def enhanced_income_prediction(monthly_incomes, income_type):
    """향상된 소득 예측 모델"""
    # 계절성 분석
    seasonal_factors = analyze_seasonality(monthly_incomes)
    
    # 트렌드 분석
    trend_factor = analyze_trend(monthly_incomes)
    
    # 변동성 분석
    volatility = calculate_volatility(monthly_incomes)
    
    # 소득 유형별 가중치 적용
    type_weights = get_income_type_weights(income_type)
    
    # 예측 계산
    base_prediction = calculate_base_prediction(monthly_incomes)
    adjusted_prediction = apply_factors(base_prediction, seasonal_factors, trend_factor, volatility, type_weights)
    
    return adjusted_prediction, calculate_confidence(monthly_incomes, volatility)
```

---

## 🎮 **담당자 3: 성장리워드 (Reward App)**

### **구현해야 할 페이지들**

#### 1. 퀴즈 목록 (`templates/reward/quiz_list.html`)
```html
<!-- 구현 예시 -->
<div class="quiz-categories">
    <div class="category-tabs">
        <button class="tab active" data-category="all">전체</button>
        <button class="tab" data-category="basic">기초 금융</button>
        <button class="tab" data-category="investment">투자</button>
        <button class="tab" data-category="credit">신용</button>
        <button class="tab" data-category="insurance">보험</button>
    </div>
    
    <div class="quiz-grid">
        {% for quiz in quizzes %}
        <div class="quiz-card" data-category="{{ quiz.category }}">
            <div class="quiz-header">
                <h4>{{ quiz.title }}</h4>
                <span class="difficulty {{ quiz.difficulty }}">{{ quiz.get_difficulty_display }}</span>
            </div>
            <p>{{ quiz.description }}</p>
            <div class="quiz-meta">
                <span class="points">+{{ quiz.points_reward }}점</span>
                <span class="questions">{{ quiz.questions.count }}문제</span>
            </div>
            <a href="{% url 'reward:take_quiz' quiz.id %}" class="btn btn-primary">시작하기</a>
        </div>
        {% endfor %}
    </div>
</div>
```

#### 2. 퀴즈 풀이 (`templates/reward/take_quiz.html`)
```html
<!-- 구현 예시 -->
<div class="quiz-container">
    <div class="quiz-progress">
        <div class="progress-bar">
            <div class="progress-fill" style="width: {{ progress }}%"></div>
        </div>
        <span class="progress-text">{{ current_question }}/{{ total_questions }}</span>
    </div>
    
    <div class="question-container">
        <h3 class="question-text">{{ question.question_text }}</h3>
        
        <div class="options">
            {% for option in question.options.all %}
            <label class="option-item">
                <input type="radio" name="answer" value="{{ option.order }}">
                <span class="option-text">{{ option.option_text }}</span>
            </label>
            {% endfor %}
        </div>
        
        <div class="question-navigation">
            <button type="button" class="btn btn-secondary" id="prev-btn">이전</button>
            <button type="button" class="btn btn-primary" id="next-btn">다음</button>
        </div>
    </div>
</div>
```

#### 3. 사용자 대시보드 (`templates/reward/dashboard.html`)
```html
<!-- 구현 예시 -->
<div class="user-dashboard">
    <div class="user-stats">
        <div class="stat-card">
            <div class="stat-icon">⭐</div>
            <div class="stat-value">{{ profile.total_points }}</div>
            <div class="stat-label">총 포인트</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-icon">📈</div>
            <div class="stat-value">{{ profile.current_level }}</div>
            <div class="stat-label">현재 레벨</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-icon">🔥</div>
            <div class="stat-value">{{ profile.streak_days }}</div>
            <div class="stat-label">연속 활동일</div>
        </div>
    </div>
    
    <div class="recent-achievements">
        <h4>최근 달성한 업적</h4>
        <div class="achievement-list">
            {% for achievement in recent_achievements %}
            <div class="achievement-item">
                <div class="achievement-icon">{{ achievement.achievement.icon }}</div>
                <div class="achievement-info">
                    <h5>{{ achievement.achievement.title }}</h5>
                    <p>{{ achievement.achievement.description }}</p>
                </div>
                <div class="achievement-date">{{ achievement.earned_at|date:"m/d" }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
```

### **게이미피케이션 시스템 예시**
```python
def calculate_level_rewards(user_profile):
    """레벨업 보상 계산"""
    level = user_profile.current_level
    base_points = level * 100
    
    # 특별 레벨 보상
    if level % 10 == 0:  # 10의 배수 레벨
        base_points *= 2
        special_reward = f"레벨 {level} 달성 특별 보상!"
    elif level % 5 == 0:  # 5의 배수 레벨
        base_points = int(base_points * 1.5)
        special_reward = f"레벨 {level} 달성 보너스!"
    else:
        special_reward = ""
    
    return base_points, special_reward

def check_achievements(user_profile):
    """업적 달성 체크"""
    achievements = Achievement.objects.filter(is_active=True)
    
    for achievement in achievements:
        if UserAchievement.objects.filter(
            user_profile=user_profile, 
            achievement=achievement
        ).exists():
            continue
            
        if is_achievement_completed(user_profile, achievement):
            # 업적 달성 처리
            UserAchievement.objects.create(
                user_profile=user_profile,
                achievement=achievement
            )
            
            # 포인트 지급
            user_profile.add_points(
                achievement.points_reward, 
                f"업적 달성: {achievement.title}"
            )
```

---

## 📋 **공통 작업 체크리스트**

### **모든 팀원이 확인해야 할 사항**
- [ ] 담당 앱의 `models.py` 모델 설계 완료
- [ ] 담당 앱의 `views.py` 뷰 로직 구현 완료
- [ ] 담당 앱의 `admin.py` 관리자 설정 완료
- [ ] 담당 앱의 `urls.py` URL 라우팅 설정 완료
- [ ] 담당 앱의 템플릿 파일들 완성
- [ ] 담당 앱의 정적 파일들 (CSS/JS) 완성
- [ ] 기본적인 테스트 코드 작성
- [ ] 에러 처리 및 사용자 피드백 구현

### **코드 품질 체크리스트**
- [ ] Python 코드 스타일 가이드 준수
- [ ] 함수 및 클래스에 적절한 docstring 작성
- [ ] 변수명이 명확하고 이해하기 쉬운가?
- [ ] 에러 처리가 적절하게 구현되었는가?
- [ ] 보안 취약점이 없는가? (SQL Injection, XSS 등)

### **사용자 경험 체크리스트**
- [ ] 페이지 로딩 속도가 적절한가?
- [ ] 모바일 반응형 디자인이 적용되었는가?
- [ ] 사용자 입력에 대한 적절한 피드백이 제공되는가?
- [ ] 에러 메시지가 명확하고 도움이 되는가?

---

## 🚀 **개발 완료 후 통합 작업**

### **1단계: 개별 테스트**
```bash
# 각자 담당 앱 테스트
python manage.py test asset
python manage.py test plan
python manage.py test reward
```

### **2단계: 통합 테스트**
```bash
# 전체 테스트 실행
python manage.py test

# 서버 실행 테스트
python manage.py runserver
```

### **3단계: 코드 리뷰**
- 팀원 간 코드 리뷰 진행
- 피드백 반영 및 수정
- 최종 코드 품질 검증

### **4단계: 배포 준비**
```bash
# 정적 파일 수집
python manage.py collectstatic

# 데이터베이스 마이그레이션 확인
python manage.py showmigrations

# 환경 변수 설정 확인
python manage.py check --deploy
```

---

## 📞 **팀 협업 규칙**

### **Git 브랜치 전략**
- `main`: 메인 브랜치 (안정 버전)
- `develop`: 개발 브랜치 (통합 테스트용)
- `feature/기능명`: 개별 기능 개발 브랜치
- `hotfix/버그명`: 긴급 버그 수정 브랜치

### **커밋 메시지 규칙**
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 코드 추가
chore: 빌드 프로세스 또는 보조 도구 변경
```

### **Pull Request 규칙**
- 기능 완성 후 PR 생성
- 코드 리뷰 후 머지
- 충돌 해결은 PR 작성자가 담당

---

**Happy Coding! 🚀**

각자 담당 기능을 완성하여 Much 프로젝트를 성공적으로 완성해봅시다!


