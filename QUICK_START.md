# Much 프로젝트 빠른 시작 가이드 🚀

## ⚡ **5분 만에 시작하기**

### 1. 환경 설정
```bash
# 가상환경 활성화
source venv/bin/activate

# 의존성 설치 (이미 설치되어 있음)
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
# 개발 서버 시작
python manage.py runserver

# 브라우저에서 접속
# http://localhost:8000/
```

### 3. Admin 접속
```bash
# 슈퍼유저 생성 (처음 한 번만)
python manage.py createsuperuser

# Admin 접속
# http://localhost:8000/admin/
```

---

## 📁 **프로젝트 구조**

```
much/
├── asset/           # 자산진단 앱 (담당자 1)
├── plan/            # AI플랜 앱 (담당자 2)  
├── reward/          # 성장리워드 앱 (담당자 3)
├── templates/       # HTML 템플릿
├── static/          # CSS, JS, 이미지
└── manage.py        # Django 관리
```

---

## 🎯 **각자 작업할 내용**

### **담당자 1: 자산진단**
- `templates/asset/question_form.html` - 진단 질문 폼
- `templates/asset/result.html` - 진단 결과 표시
- `templates/asset/history.html` - 진단 기록 목록

### **담당자 2: AI플랜**
- `templates/plan/income_input.html` - 소득 데이터 입력
- `templates/plan/plan_settings.html` - 플랜 설정
- `templates/plan/plan_result.html` - 플랜 결과

### **담당자 3: 성장리워드**
- `templates/reward/quiz_list.html` - 퀴즈 목록
- `templates/reward/take_quiz.html` - 퀴즈 풀이
- `templates/reward/dashboard.html` - 사용자 대시보드

---

## 🔧 **자주 사용하는 명령어**

```bash
# 서버 실행
python manage.py runserver

# 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 테스트
python manage.py test

# 정적 파일 수집
python manage.py collectstatic
```

---

## 📚 **더 자세한 가이드**

- **개발 환경 설정**: `DEVELOPMENT_GUIDE.md`
- **팀원별 작업 가이드**: `TEAM_WORK_GUIDE.md`
- **프로젝트 전체 설명**: `README.md`

---

**즐거운 코딩 되세요! 🎉**


