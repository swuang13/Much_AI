import os, json, re, requests, random
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import AssessmentInputForm
from .models import Assessment, AssetProfile
from .ai_client import hf_chat_json, hf_chat

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("LLAMA_MODEL", "llama3:8b")

SYSTEM_PROMPT = """
너는 한국 금융당국 기준을 준수하는 신용·자산 진단 AI다. 아래 지침을 엄격히 따른다.

[언어/표현]
- 어려운 용어 대신 쉬운 한국어 사용(예: 유동성→ 쉽게 찾을 수 있는 돈/비상금).
- 중복 문장 금지. 핵심만 간단명료하게.

[숫자/단위 규칙]
- JSON 숫자 필드는 숫자형으로 출력(문자열 금지). 요약 텍스트엔 쉼표와 단위를 정확히 쓴다.
- 금액 기본 단위는 원. 예: 2,330,000원. 1억 이상은 필요 시 "1.0억 원 (100,000,000원)" 같이 보조 표기.
- 비율은 %로 표기, 자산 비중 합은 100%가 되게.

[금융당국 기준 평가 룰]
- DTI: ≤40 우수(A) / 40~60 양호(B) / 60~70 주의(C) / >70 위험(D)
- 저축률: ≥30 매우 우수 / 20~30 우수 / 10~20 보통 / <10 주의
- 신용가중치: 900~1000 +20 / 800~899 +15 / 700~799 +10 / 600~699 +5 / <600 -10
- 부채 리스크: 담보<신용<카드/현금서비스, 연체는 -20점
- 자산 건전성: 예적금 비중 20%↑ 양호, 투자 집중 50%↑ 위험, 비상자금<월지출 6개월 주의
- 점수 공식(개략): 50 + DTI(≤25) + 저축률(≤20) + 신용가중치 + 자산건전성(≤15) - 리스크

[금지]
- 고금리 권유 금지(월 20%↑). 필요한 경우 위험 경고 문구 포함.
- 과도한 보장 표현 금지. 원칙/구조 중심으로.

[반드시 지켜야 할 출력 형식(JSON 스키마)]
{
  "grade": "A|B|C|D",
  "score_100": 0,
  "summary": "간결한 HTML( <p>, <ul>, <li>, <strong> )로 4~6문단 구성: <p><strong>상태 개요</strong>: …</p><p><strong>계산 근거</strong>: 저축률·DTI·월 여유자금 등 숫자 포함</p><p><strong>점수 부여 이유</strong>: 기준과 가중치 설명</p><p><strong>핵심 진단</strong>: 리스크·기회 요약</p><p><strong>권장 행동</strong>: 한 줄 제안</p>",
  "detailed_analysis": {
    "financial_health": "가계 상태를 쉬운 표현으로 2~3문장",
    "debt_structure": "빚 구조와 위험을 쉬운 표현으로 2~3문장",
    "asset_allocation": "자산 나눔(예적금=쉽게 찾을 수 있는 돈)을 2~3문장",
    "trend_analysis": "최근 6개월 수입·지출 추세를 2~3문장"
  },
  "metrics": {
    "savings_rate_pct": 0.0,
    "dti_pct": 0.0,
    "debt_to_asset_ratio": 0.0,
    "liquidity_ratio": 0.0,
    "monthly_surplus": 0
  },
  "risk_factors": [
    {
      "category": "고위험|중위험|저위험",
      "description": "쉬운 표현으로 위험 요소",
      "impact": "가계에 미칠 영향(간단)"
    }
  ],
  "alerts": ["금융당국 기준 위반사항 또는 주의사항 0~3개"],
  "recommendations": [
    {
      "priority": "높음|보통|낮음",
      "category": "부채관리|저축늘리기|투자기초|지출줄이기",
      "action": "월 납입액·기간·비중 등 구체 실행",
      "expected_benefit": "예상 효과(쉬운 표현)"
    }
  ],
  "next_steps": ["30일 내 실행 체크리스트 3개"]
}
"""

def _call_ollama(payload: dict) -> dict:
    """Ollama /api/chat 호출 + JSON 파싱 보강"""
    # 연결 지연과 응답 지연을 분리하여 제어 (connect=5s, read=180s)
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=None,  # 타임아웃 제거: 오래 걸려도 대기
    )
    r.raise_for_status()
    data = r.json()
    content = (data.get("message") or {}).get("content") or ""
    # 1차: JSON 그대로 시도
    try:
        return json.loads(content)
    except Exception:
        pass
    # 2차: 본문에서 { ... } JSON 블록만 추출 후 시도
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {content[:200]}")


def _ollama_is_up() -> bool:
    """Ollama 서버 헬스체크: /api/tags 호출로 가동 여부 확인"""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return resp.ok
    except Exception:
        return False


def _ollama_model_ready(model_name: str) -> bool:
    """모델이 로컬에 준비되어 있는지 /api/tags로 확인"""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json() or {}
        for item in data.get("models", []) or []:
            if (item.get("model") or "").lower() == model_name.lower():
                return True
        return False
    except Exception:
        return False

def _generate_virtual_asset_data():
    """가상 사용자를 위한 자산 데이터 생성"""
    # 월별 수입/지출 데이터 (만원 단위)
    base_income = random.randint(400, 800)  # 기본 수입
    base_expense = random.randint(250, 600)  # 기본 지출
    
    # 6개월간의 수입/지출 데이터 생성 (약간의 변동성 추가)
    income_monthly = []
    expense_monthly = []
    
    for i in range(6):
        # 수입: 기본값 ± 10% 변동
        income_var = random.uniform(0.9, 1.1)
        income = int(base_income * income_var)
        income_monthly.append(income)
        
        # 지출: 기본값 ± 15% 변동 (더 큰 변동성)
        expense_var = random.uniform(0.85, 1.15)
        expense = int(base_expense * expense_var)
        expense_monthly.append(expense)
    
    # 6개월 총합 계산
    income_6m = sum(income_monthly) * 10000  # 원 단위로 변환
    expense_6m = sum(expense_monthly) * 10000  # 원 단위로 변환
    
    # 신용점수 (수입/지출 비율에 따라 조정)
    savings_rate = (income_6m - expense_6m) / income_6m if income_6m > 0 else 0
    base_score = 500
    if savings_rate > 0.3:
        credit_score = random.randint(750, 850)
    elif savings_rate > 0.1:
        credit_score = random.randint(650, 750)
    elif savings_rate > 0:
        credit_score = random.randint(550, 650)
    else:
        credit_score = random.randint(400, 550)
    
    # 기타 자산 정보
    housing_loan = random.randint(0, 200000000)  # 주택담보대출 (0~2억)
    auto_loan = random.randint(0, 50000000)  # 자동차 할부 (0~5천만)
    credit_limit = random.randint(10000000, 50000000)  # 신용카드 한도 (1천만~5천만)
    savings = random.randint(10000000, 100000000)  # 예적금 (1천만~1억)
    investment = random.randint(0, 50000000)  # 투자 자산 (0~5천만)
    delinquency = random.randint(0, 2)  # 연체 횟수 (0~2회)
    
    # 신용정보 텍스트 생성
    credit_info_parts = []
    if housing_loan > 0:
        credit_info_parts.append(f"주택담보대출 {housing_loan//10000}만원")
    if auto_loan > 0:
        credit_info_parts.append(f"자동차할부 {auto_loan//10000}만원")
    if credit_limit > 0:
        credit_info_parts.append(f"신용카드 한도 {credit_limit//10000}만원")
    if savings > 0:
        credit_info_parts.append(f"예적금 {savings//10000}만원")
    if investment > 0:
        credit_info_parts.append(f"투자자산 {investment//10000}만원")
    
    credit_info = " / ".join(credit_info_parts) if credit_info_parts else "기본 신용정보"
    
    return {
        'credit_info': credit_info,
        'income_6m': income_6m,
        'expense_6m': expense_6m,
        'credit_score': credit_score,
        'housing_loan_balance': housing_loan,
        'auto_loan_balance': auto_loan,
        'credit_card_limit_total': credit_limit,
        'savings_balance': savings,
        'investment_balance': investment,
        'delinquency_last12m': delinquency,
        'income_monthly': income_monthly,
        'expense_monthly': expense_monthly,
    }


def _compute_metrics_from_profile(profile: AssetProfile) -> dict:
    """프로필 기반 핵심 지표 계산(서버 폴백용). 비율값은 퍼센트가 아닌 비율/배수는 그대로 유지.
    - savings_rate_pct, dti_pct: 퍼센트 값
    - debt_to_asset_ratio, liquidity_ratio: 배수
    - monthly_surplus: 원 단위
    """
    income_total = float(profile.income_6m or 0)
    expense_total = float(profile.expense_6m or 0)
    savings_balance = float(getattr(profile, "savings_balance", 0) or 0)
    investment_balance = float(getattr(profile, "investment_balance", 0) or 0)
    total_assets_liquid = savings_balance + investment_balance
    total_debts = float(getattr(profile, "housing_loan_balance", 0) or 0) + float(getattr(profile, "auto_loan_balance", 0) or 0)

    savings_rate_pct = ((income_total - expense_total) / income_total * 100.0) if income_total > 0 else 0.0
    dti_pct = (expense_total / income_total * 100.0) if income_total > 0 else 0.0
    debt_to_asset_ratio = (total_debts / total_assets_liquid) if total_assets_liquid > 0 else 0.0
    avg_monthly_expense = expense_total / 6.0 if expense_total > 0 else 0.0
    # 6개월치 지출 대비 예적금 보유액 비율(배수)
    liquidity_ratio = (savings_balance / (avg_monthly_expense * 6.0)) if avg_monthly_expense > 0 else 0.0
    monthly_surplus = int(((income_total - expense_total) / 6.0)) if income_total > 0 else 0

    return {
        "savings_rate_pct": round(savings_rate_pct, 2),
        "dti_pct": round(dti_pct, 2),
        "debt_to_asset_ratio": round(debt_to_asset_ratio, 2),
        "liquidity_ratio": round(liquidity_ratio, 2),
        "monthly_surplus": monthly_surplus,
    }


def _score_and_grade_from_metrics(metrics: dict, credit_score: int, delinquency_flag: bool) -> tuple[int, str]:
    """금융당국 기준(시스템 프롬프트 요약)에 맞춰 점수 산출."""
    score = 50
    dti = float(metrics.get("dti_pct", 0))
    if dti <= 40:
        score += 25
    elif dti <= 60:
        score += 15
    elif dti <= 70:
        score += 5
    # else: +0

    savings_rate = float(metrics.get("savings_rate_pct", 0))
    if savings_rate >= 30:
        score += 20
    elif savings_rate >= 20:
        score += 15
    elif savings_rate >= 10:
        score += 7

    if credit_score >= 900:
        score += 20
    elif credit_score >= 800:
        score += 15
    elif credit_score >= 700:
        score += 10
    elif credit_score >= 600:
        score += 5
    else:
        score -= 10

    # 유동성/자산건전성 보너스
    if float(metrics.get("debt_to_asset_ratio", 0)) < 1:
        score += 7
    elif float(metrics.get("debt_to_asset_ratio", 0)) < 2:
        score += 3
    if float(metrics.get("liquidity_ratio", 0)) >= 1:
        score += 5

    if delinquency_flag:
        score -= 20

    score = max(0, min(100, int(round(score))))
    grade = "A" if score >= 85 else ("B" if score >= 70 else ("C" if score >= 55 else "D"))
    return score, grade


def _fallback_assessment_from_profile(profile: AssetProfile) -> dict:
    """LLM 실패 시 표시 가능한 최소 완전 결과 생성."""
    metrics = _compute_metrics_from_profile(profile)
    score, grade = _score_and_grade_from_metrics(metrics, int(profile.credit_score or 0), bool(getattr(profile, "delinquency_last12m", False)))

    # 사고 체인이 드러나는 종합 요약
    income_6m = float(profile.income_6m or 0)
    expense_6m = float(profile.expense_6m or 0)
    credit_score = int(profile.credit_score or 0)
    
    # 상태 평가
    status_desc = "우수한" if score >= 80 else "양호한" if score >= 65 else "주의가 필요한"
    action_desc = "현재 상태 유지와 투자 다양화" if score >= 80 else "DTI 개선과 비상자금 확충" if score >= 65 else "지출 관리와 부채 정리"
    
    summary = f"""<p><strong>상태 개요</strong>: 최근 6개월 수입 {income_6m:,.0f}원, 지출 {expense_6m:,.0f}원으로 저축률 {metrics['savings_rate_pct']}%를 기록했습니다.</p>

<p><strong>계산 근거</strong>: DTI {metrics['dti_pct']}%, 신용점수 {credit_score}점, 월 여유자금 {metrics['monthly_surplus']:,}원을 종합 평가했습니다.</p>

<p><strong>핵심 진단</strong>: {grade}등급으로 {status_desc} 재무 상태입니다.</p>

<p><strong>권장 행동</strong>: {action_desc}를 우선하세요.</p>"""

    return {
        "grade": grade,
        "score_100": score,
        "summary": summary,
        "detailed_analysis": {
            "financial_health": f"6개월 수입 {income_6m:,.0f}원 대비 지출 {expense_6m:,.0f}원으로 저축률 {metrics['savings_rate_pct']}%를 달성했습니다. 월 여유자금 {metrics['monthly_surplus']:,}원으로 {'안정적' if metrics['monthly_surplus'] > 500000 else '보통' if metrics['monthly_surplus'] > 200000 else '부족한'} 수준입니다.",
            "debt_structure": f"신용점수 {credit_score}점 기준으로 {'우량' if credit_score >= 750 else '보통' if credit_score >= 650 else '관리 필요'} 신용 상태입니다. DTI {metrics['dti_pct']}%로 {'안전' if metrics['dti_pct'] <= 40 else '주의' if metrics['dti_pct'] <= 60 else '위험'} 구간에 해당합니다.",
            "asset_allocation": f"쉽게 찾을 수 있는 돈(예적금) 비중과 투자 자산의 균형을 평가했습니다. 비상자금 확보 비율은 {metrics['liquidity_ratio']:.1f}배로 {'충분' if metrics['liquidity_ratio'] >= 1.0 else '부족'} 수준입니다.",
            "trend_analysis": f"최근 6개월 수입·지출 패턴에서 {'안정적' if abs(max(profile.income_monthly or [0]) - min(profile.income_monthly or [0])) <= 100 else '변동성이 있는'} 추세를 보였습니다. 월평균 수입 {income_6m/6:,.0f}원, 지출 {expense_6m/6:,.0f}원 기준입니다.",
        },
        "metrics": metrics,
        "risk_factors": [
            {"category": "중위험", "description": "DTI가 중간 수준으로 상승 가능성 존재", "impact": "금리 상승기 가계 현금흐름 압박"}
        ],
        "alerts": [],
        "recommendations": [
            {
                "priority": "높음" if metrics['dti_pct'] > 60 else "보통",
                "category": "지출관리" if metrics['dti_pct'] > 60 else "저축늘리기",
                "action": f"월 지출을 {expense_6m/6:,.0f}원에서 {(expense_6m/6)*0.9:,.0f}원으로 10% 줄이고 자동이체 설정" if metrics['dti_pct'] > 60 else f"월 저축을 {metrics['monthly_surplus']:,}원에서 {metrics['monthly_surplus']+200000:,}원으로 늘려 목표 저축률 25% 달성",
                "expected_benefit": "DTI 5~10%p 개선" if metrics['dti_pct'] > 60 else "연간 240만원 추가 저축"
            },
            {
                "priority": "보통",
                "category": "투자기초",
                "action": f"비상자금 {(expense_6m/6)*3:,.0f}원(3개월치) 확보 후 월 {min(300000, metrics['monthly_surplus']//2):,}원씩 ETF 적립식 투자 시작",
                "expected_benefit": "장기 자산 증식과 인플레이션 대응"
            }
        ],
        "next_steps": [
            f"이번 달 예산 {expense_6m/6:,.0f}원 상한 설정하고 가계부 앱 설치",
            f"비상자금 {(expense_6m/6)*3:,.0f}원 목표로 적금 자동이체 신청",
            f"신용카드 이용률 30% 이하 유지 (현재 한도 기준 월 사용액 체크)"
        ],
    }


def _ensure_assessment_schema(llm_json: dict | str | None, profile: AssetProfile) -> dict:
    """LLM 결과를 점검하고 누락 시 서버 계산값으로 보완.
    - dict, str(JSON), None 모두 허용
    """
    base = _fallback_assessment_from_profile(profile)
    data: dict = {}
    if isinstance(llm_json, dict):
        data = llm_json
    elif isinstance(llm_json, str):
        try:
            data = json.loads(llm_json)
        except Exception:
            # 본문에서 JSON 블록만 추출 시도
            try:
                match = re.search(r"\{.*\}", llm_json, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
            except Exception:
                data = {}

    # 핵심 필드
    base["score_100"] = int(data.get("score_100", base["score_100"]))
    base["grade"] = (data.get("grade") or base["grade"])[:2]
    base["summary"] = data.get("summary") or base["summary"]

    # metrics 병합
    m = data.get("metrics") or {}
    metrics = base.get("metrics")
    for k in ("savings_rate_pct", "dti_pct", "debt_to_asset_ratio", "liquidity_ratio", "monthly_surplus"):
        if k in m and m[k] is not None:
            metrics[k] = m[k]
    base["metrics"] = metrics

    # 기타 섹션
    if data.get("detailed_analysis"):
        base["detailed_analysis"].update({k: v for k, v in data["detailed_analysis"].items() if v})
    if data.get("risk_factors"):
        base["risk_factors"] = data["risk_factors"]
    if data.get("recommendations"):
        base["recommendations"] = data["recommendations"]
    if data.get("next_steps"):
        base["next_steps"] = data["next_steps"]

    return base


def _derive_risk_profile(score_100: int | None, dti_pct: float | None, savings_rate_pct: float | None) -> str:
    """간단 리스크 성향 도출(보수/중립/공격)."""
    score = int(score_100 or 0)
    dti = float(dti_pct or 0)
    save = float(savings_rate_pct or 0)
    if score >= 80 and dti <= 40 and save >= 20:
        return "중립~공격"
    if score >= 65 and dti <= 60 and save >= 10:
        return "중립"
    return "보수적"


def _clean_chat_response(text: str) -> str:
    """간단 후처리: 중복 라인 제거, 공백 정리, 길이 제한."""
    if not text:
        return ""
    import re
    # 줄 단위 중복 제거(순서 유지)
    seen = set()
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    cleaned = "\n".join(lines)
    # 과도한 반복 어휘 축약(간단 규칙)
    cleaned = re.sub(r"(지분|정리|조정)[^\n]*\n(?:[^\n]*\n){0,1}\s*\1", r"\1", cleaned, flags=re.IGNORECASE)
    # 길이 제한
    return cleaned[:1800]


def _parse_korean_currency(text: str) -> int:
    """한글 금액 표현을 원 단위 정수로 단순 파싱(억원/천만/백만/만/원)."""
    import re
    t = text.replace(',', '')
    # 우선 억/만 단위
    m = re.search(r"(\d+(?:\.\d+)?)\s*(억)\s*(\d+)?\s*(만)?원?", t)
    if m:
        eok = float(m.group(1))
        man = float(m.group(3) or 0)
        return int((eok * 10000 + man) * 10000)
    # 단일 단위
    m = re.search(r"(\d+(?:\.\d+)?)\s*(억원|억|천만원|백만원|만원|원)", t)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        if unit in ("억원", "억"):
            return int(val * 10000 * 10000)
        if unit == "천만원":
            return int(val * 1000 * 10000)
        if unit == "백만원":
            return int(val * 100 * 10000)
        if unit == "만원":
            return int(val * 10000)
        if unit == "원":
            return int(val)
    # 숫자만
    m = re.search(r"(\d{6,})원?", t)
    if m:
        return int(m.group(1))
    return 0


def _intercept_high_interest_message(user_message: str) -> str | None:
    """월 이자 20% 이상 등 고금리 제안이 포함되면 모델 호출 전 경고 답변 반환."""
    import re
    t = user_message.replace('퍼센트', '%')
    # 월 금리 20% 이상 탐지
    rate = None
    for pat in [r"월\s*이자[^\d%]*([0-9]+(?:\.[0-9]+)?)%", r"([0-9]+(?:\.[0-9]+)?)%[^\n]{0,8}월"]:
        m = re.search(pat, t)
        if m:
            try:
                rate = float(m.group(1))
                break
            except Exception:
                pass
    if rate is None:
        return None
    if rate < 20.0:
        return None

    amount = _parse_korean_currency(t)
    monthly_interest = int(amount * (rate / 100.0)) if amount > 0 else None
    annual_rate = rate * 12.0
    lines = []
    lines.append("**고금리 대출 경고: 신청 비추천**")
    if amount > 0:
        lines.append(f"- **대출금액**: {amount:,}원")
    lines.append(f"- **제시 금리(월)**: {rate:.2f}% → **연 환산** {annual_rate:.0f}% 이상")
    if monthly_interest is not None:
        lines.append(f"- **월 이자만**: {monthly_interest:,}원 (원금 제외)")
    lines.append("- 이 수준은 과도한 고금리로, 신용 악화·연체 위험이 매우 큽니다.")
    lines.append("")
    lines.append("**권장 대안**")
    lines.append("1. 금융권 저금리 상담/대환(1금융권·정책서민금융) 먼저 검토")
    lines.append("2. 단기 현금 필요 시 금액 축소·기간 단축 + 상환계획 수립")
    lines.append("3. 카드 이용률 30% 이하·지출 상한 설정으로 유동성 개선")
    return "\n".join(lines)

def _build_user_content_from_profile(profile: AssetProfile, extra_info: str = "") -> str:
    """LLM에 전달할 사용자 데이터(JSON 문자열) - 프로필 기반"""
    d = {
        "income_6m_total": float(profile.income_6m),
        "expense_6m_total": float(profile.expense_6m),
        "credit_score": int(profile.credit_score),
        "credit_info": (extra_info or profile.credit_info or "").strip() or profile.credit_info,
        "note": "가능하면 위 값으로 저축률/DTI 계산해 metrics에 기입."
    }
    # 사용자 메시지도 JSON만 전달
    return json.dumps(d, ensure_ascii=False)

@require_http_methods(["GET"])
def home(request):
    form = AssessmentInputForm()
    latest = Assessment.objects.all()[:5]
    return render(request, "asset/home.html", {"form": form, "latest": latest})


@require_http_methods(["POST"]) 
def demo_login(request):
    """데모 유저를 생성하고 자동 로그인한다."""
    username = "demo_user"
    password = "demo_pass_1234"

    user, created = User.objects.get_or_create(username=username, defaults={"email": "demo@example.com"})
    if created:
        user.set_password(password)
        user.save()

    # 자산 프로필 기본값 생성/업데이트
    profile, created = AssetProfile.objects.get_or_create(
        user=user,
        defaults={
            "credit_info": "주담대 3.2억 잔액 / 자동차할부 1800만 / 카드한도 2000만 / 비상금 600만",
            # 총액(원)과 월별(만원)을 일관되게 맞춤
            "income_6m": 36000000,
            "expense_6m": 24000000,
            "credit_score": 720,
            # 최근 6개월(만원 단위 정수): 5개월전→이번달
            "income_monthly": [550, 600, 580, 620, 600, 650],
            "expense_monthly": [360, 390, 370, 410, 380, 420],
            "housing_loan_balance": 320000000,
            "auto_loan_balance": 18000000,
            "credit_card_limit_total": 20000000,
            "savings_balance": 6000000,
            "investment_balance": 15000000,
            "delinquency_last12m": False,
        },
    )

    # 기존 레코드가 이미 있었던 경우에도 스키마/단위를 교정한다
    try:
        income_monthly = [550, 600, 580, 620, 600, 650]
        expense_monthly = [360, 390, 370, 410, 380, 420]
        needs_update = False
        if getattr(profile, "income_monthly", None) in (None, []) or len(profile.income_monthly) != 6:
            profile.income_monthly = income_monthly
            needs_update = True
        if getattr(profile, "expense_monthly", None) in (None, []) or len(profile.expense_monthly) != 6:
            profile.expense_monthly = expense_monthly
            needs_update = True
        # 총액(원) 재계산: 만원 단위 합계 × 10,000
        income_6m_calc = sum(profile.income_monthly) * 10000
        expense_6m_calc = sum(profile.expense_monthly) * 10000
        if int(profile.income_6m or 0) != income_6m_calc:
            profile.income_6m = income_6m_calc
            needs_update = True
        if int(profile.expense_6m or 0) != expense_6m_calc:
            profile.expense_6m = expense_6m_calc
            needs_update = True
        if needs_update and not created:
            profile.save(update_fields=[
                "income_monthly", "expense_monthly", "income_6m", "expense_6m"
            ])
    except Exception:
        # 문제가 있어도 데모 로그인은 계속 진행
        pass

    user = authenticate(username=username, password=password)
    if user:
        login(request, user)
        messages.success(request, "데모 계정으로 로그인했습니다.")
    else:
        messages.error(request, "데모 로그인에 실패했습니다.")
    return redirect("asset:home")

@require_http_methods(["POST"])
def assess(request):
    form = AssessmentInputForm(request.POST)
    if not form.is_valid():
        messages.error(request, "입력값을 확인하세요.")
        return render(request, "asset/home.html", {"form": form, "latest": Assessment.objects.all()[:5]})

    # 로그인 사용자 프로필 기반으로 진단 (폼은 추가 메모만 받음)
    if not request.user.is_authenticated:
        messages.error(request, "로그인 후 이용하세요. 데모는 '데모 로그인'을 사용하세요.")
        return render(request, "asset/home.html", {"form": form, "latest": Assessment.objects.all()[:5]})

    try:
        profile = request.user.asset_profile
    except AssetProfile.DoesNotExist:
        messages.error(request, "자산 프로필이 없습니다. '데모 로그인' 또는 '마이데이터로 자산 진단'을 먼저 사용하세요.")
        return render(request, "asset/home.html", {"form": form, "latest": Assessment.objects.all()[:5]})

    # LLM 호출 (Hugging Face Inference API)
    user_content = _build_user_content_from_profile(
        profile, form.cleaned_data.get("credit_info", "")
    )
    # HF API 호출 시도 (안정성 강화)
    llm_json = None
    try:
        print(f"[DEBUG] HF API 호출 시작 - 프로필: {profile.pk}")
        llm_json = hf_chat_json(SYSTEM_PROMPT, user_content, max_tokens=1800, temperature=0.2, top_p=0.9)
        print(f"[DEBUG] HF API 성공 - 타입: {type(llm_json)}, 키: {list(llm_json.keys()) if isinstance(llm_json, dict) else 'None'}")
        
        # 필수 필드 검증
        if not isinstance(llm_json, dict) or not llm_json.get('score_100'):
            print(f"[DEBUG] LLM 응답 불완전, 폴백 적용")
            llm_json = None
            
    except Exception as e:
        print(f"[DEBUG] HF API 실패: {str(e)}")
        llm_json = None

    # 무조건 폴백으로 보완 (LLM 성공해도 누락 필드 채움)
    print(f"[DEBUG] 폴백 보정 시작")
    llm_json = _ensure_assessment_schema(llm_json, profile)
    print(f"[DEBUG] 최종 점수: {llm_json.get('score_100')}, 등급: {llm_json.get('grade')}")
    
    if llm_json.get('score_100', 0) == 0:
        print(f"[ERROR] 여전히 점수가 0 - 강제 폴백 적용")
        llm_json = _fallback_assessment_from_profile(profile)

    grade = (llm_json.get("grade") or "")[:2]

    # 저장
    obj = Assessment.objects.create(
        user=request.user,
        credit_info=(form.cleaned_data.get("credit_info") or profile.credit_info),
        income_6m=profile.income_6m,
        expense_6m=profile.expense_6m,
        credit_score=profile.credit_score,
        result=llm_json,
        grade=grade,
    )
    messages.success(request, "자산 진단이 완료되었습니다.")
    return redirect("asset:assessment_detail", pk=obj.pk)


@require_http_methods(["POST"]) 
def assess_mydata(request):
    """로그인 유저의 자산 프로필을 불러와 LLM으로 진단"""
    if not request.user.is_authenticated:
        messages.error(request, "먼저 로그인해주세요. 데모라면 '데모 로그인'을 사용하세요.")
        return redirect("asset:home")

    try:
        profile = request.user.asset_profile
    except AssetProfile.DoesNotExist:
        messages.error(request, "자산 프로필이 없습니다. 데모 로그인 버튼을 먼저 눌러 생성하세요.")
        return redirect("asset:home")

    user_payload = json.dumps({
        "income_6m_total": float(profile.income_6m),
        "expense_6m_total": float(profile.expense_6m),
        "income_monthly": profile.income_monthly,
        "expense_monthly": profile.expense_monthly,
        "credit_score": int(profile.credit_score),
        "credit_info": profile.credit_info,
        "assets": {
            "savings_balance": float(profile.savings_balance),
            "investment_balance": float(profile.investment_balance)
        },
        "debts": {
            "housing_loan_balance": float(profile.housing_loan_balance),
            "auto_loan_balance": float(profile.auto_loan_balance),
            "credit_card_limit_total": float(profile.credit_card_limit_total)
        },
        "flags": {"delinquency_last12m": bool(profile.delinquency_last12m)},
        "note": "월별 추세를 고려해 리스크와 기회 요인을 짚고, 실행 가능한 3~5개 조언을 제공."
    }, ensure_ascii=False)

    # HF API 호출 시도 (마이데이터, 안정성 강화)
    llm_json = None
    try:
        print(f"[DEBUG] 마이데이터 HF API 호출 시작 - 프로필: {profile.pk}")
        llm_json = hf_chat_json(SYSTEM_PROMPT, user_payload, max_tokens=1800, temperature=0.2, top_p=0.9)
        print(f"[DEBUG] 마이데이터 HF API 성공 - 타입: {type(llm_json)}, 키: {list(llm_json.keys()) if isinstance(llm_json, dict) else 'None'}")
        
        # 필수 필드 검증
        if not isinstance(llm_json, dict) or not llm_json.get('score_100'):
            print(f"[DEBUG] 마이데이터 LLM 응답 불완전, 폴백 적용")
            llm_json = None
            
    except Exception as e:
        print(f"[DEBUG] 마이데이터 HF API 실패: {str(e)}")
        llm_json = None

    # 무조건 폴백으로 보완 (LLM 성공해도 누락 필드 채움)
    print(f"[DEBUG] 마이데이터 폴백 보정 시작")
    llm_json = _ensure_assessment_schema(llm_json, profile)
    print(f"[DEBUG] 마이데이터 최종 점수: {llm_json.get('score_100')}, 등급: {llm_json.get('grade')}")
    
    if llm_json.get('score_100', 0) == 0:
        print(f"[ERROR] 마이데이터 여전히 점수가 0 - 강제 폴백 적용")
        llm_json = _fallback_assessment_from_profile(profile)

    grade = (llm_json.get("grade") or "")[:2]

    obj = Assessment.objects.create(
        user=request.user,
        credit_info=profile.credit_info,
        income_6m=profile.income_6m,
        expense_6m=profile.expense_6m,
        credit_score=profile.credit_score,
        result=llm_json,
        grade=grade,
    )
    messages.success(request, "마이데이터(가상) 기반 진단이 완료되었습니다.")
    return redirect("asset:assessment_detail", pk=obj.pk)

@require_http_methods(["GET"])
def assessment_list(request):
    qs = Assessment.objects.all()
    return render(request, "asset/assessment_list.html", {"items": qs})

@require_http_methods(["GET"])
def assessment_detail(request, pk: int):
    obj = get_object_or_404(Assessment, pk=pk)
    # 결과 스키마 보정(예전 기록도 가독성 있게 표시)
    try:
        profile = getattr(obj.user, "asset_profile", None)
    except Exception:
        profile = None
    try:
        src_result = obj.result if isinstance(obj.result, dict) else None
    except Exception:
        src_result = None
    if profile is not None:
        try:
            display_result = _ensure_assessment_schema(src_result, profile)
            # 템플릿에서 그대로 쓰도록 인메모리 결과를 대체 (DB 저장 아님)
            obj.result = display_result
        except Exception:
            pass

    # 파생 메트릭(서버측 계산)도 참고로 제공
    income = Decimal(obj.income_6m)
    expense = Decimal(obj.expense_6m)
    savings_rate = float(((income - expense) / income) * 100) if income > 0 else 0.0
    context = {
        "item": obj,
        "metrics_server": {
            "savings_rate_pct": round(savings_rate, 2),
            "dti_pct": round(float((expense / income) * 100), 2) if income > 0 else 0.0
        }
    }
    return render(request, "asset/assessment_detail.html", context)

def auth_page(request):
    """로그인/회원가입 페이지"""
    return render(request, "asset/auth.html")

def user_login(request):
    """사용자 로그인"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"환영합니다, {user.first_name or user.username}님!")
            return redirect("asset:home")
        else:
            messages.error(request, "아이디 또는 비밀번호가 올바르지 않습니다.")
    
    return redirect("asset:auth_page")

def user_register(request):
    """사용자 회원가입"""
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        first_name = request.POST.get("first_name")
        
        # 비밀번호 확인
        if password1 != password2:
            messages.error(request, "비밀번호가 일치하지 않습니다.")
            return redirect("asset:auth_page")
        
        # 사용자 생성
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    first_name=first_name
                )
                
                # 가상 자산 데이터 생성 및 저장
                asset_data = _generate_virtual_asset_data()
                AssetProfile.objects.create(
                    user=user,
                    **asset_data
                )
                
                # 자동 로그인
                login(request, user)
                messages.success(request, f"회원가입이 완료되었습니다! 마이데이터가 자동으로 연동되었습니다.")
                return redirect("asset:home")
                
        except Exception as e:
            messages.error(request, f"회원가입 중 오류가 발생했습니다: {str(e)}")
    
    return redirect("asset:auth_page")

def user_logout(request):
    """사용자 로그아웃"""
    logout(request)
    messages.info(request, "로그아웃되었습니다.")
    return redirect("asset:home")

@csrf_exempt
@require_http_methods(["POST"])
def chat_with_assessment(request, pk: int):
    """진단 결과 기반 챗봇 대화"""
    try:
        assessment = get_object_or_404(Assessment, pk=pk)
        
        # JSON 요청 파싱
        try:
            import json as json_module
            body = json_module.loads(request.body.decode('utf-8'))
        except (json_module.JSONDecodeError, UnicodeDecodeError) as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'})
            
        user_message = body.get('message', '').strip()
        assessment_data = body.get('assessment_data', {})
        
        if not user_message:
            return JsonResponse({'success': False, 'error': '메시지가 비어있습니다.'})
        
        # 챗봇용 컨텍스트 생성
        # 클라이언트에서 전달된 metrics가 있으면 활용
        metrics = assessment_data.get('metrics') or {}
        risk_profile = _derive_risk_profile(
            assessment_data.get('score') or assessment.result.get('score_100') if isinstance(assessment.result, dict) else 0,
            metrics.get('dti_pct') or assessment.result.get('metrics', {}).get('dti_pct') if isinstance(assessment.result, dict) else 0,
            metrics.get('savings_rate_pct') or assessment.result.get('metrics', {}).get('savings_rate_pct') if isinstance(assessment.result, dict) else 0,
        )

        chat_context = f"""
진단 요약:
- 등급: {assessment.grade} / 점수: {(assessment_data.get('score') or (assessment.result or {}).get('score_100') or 0)}
- 최근 6개월 수입 {assessment.income_6m:,}원 / 지출 {assessment.expense_6m:,}원
- 신용점수 {assessment.credit_score}점, 리스크 성향: {risk_profile}
- 핵심지표: 저축률 {(metrics.get('savings_rate_pct') or (assessment.result or {}).get('metrics', {}).get('savings_rate_pct') or 0)}%, DTI {(metrics.get('dti_pct') or (assessment.result or {}).get('metrics', {}).get('dti_pct') or 0)}%

대화 지침:
1) 질문 의도에 맞춰 3~6줄의 구체적인 실행 조언을 제공한다.
2) 숫자/비중/기간을 반드시 포함한다(예: 비상자금 300만원, 월 20만원 적립 15개월).
3) ETF/적금/대출/보험 등 실제 수단을 예시로 들되 특정 상품명 언급은 피한다.
4) 사용자 리스크 성향({risk_profile})에 맞춰 주식/채권/현금/대체 비중을 제시한다.
5) 중복 문구와 동어 반복을 금지하고, 동일 문장 구조의 나열을 피한다.
"""

        # 챗봇용 시스템 프롬프트(쉬운 한국어 + 단위 규칙 + 섹션)
        chat_system_prompt = """
너는 한국 개인재무/투자 자문가다. 아래 규칙을 엄격히 따른다.

[언어/표현]
- 쉬운 한국어를 사용하고 어려운 용어는 일상어로 바꿔 설명한다(예: 유동성→ 비상금/쉽게 찾을 수 있는 돈).
- 중복/장황한 문장은 금지. 3~6개의 짧은 문단으로 답변하고 각 문단 첫 줄은 굵게 요약한다.

[숫자/단위]
- 금액은 '원' 단위로 쉼표 포함 표기(예: 2,330,000원). 잘못된 '2333451 만원' 같은 표기는 금지.
- 1억 이상은 'X.X억 원'처럼 말하고, 필요 시 괄호로 원 금액을 함께 표기한다.
- 비중/수익률은 %로 표기하고, 자산 비중의 합은 100%가 되도록 제시한다.

[내용]
- 진단 데이터(점수, 저축률, DTI, 월 여유자금, 리스크 성향) 범위를 벗어난 가정은 하지 않는다.
- 포트폴리오: 주식/채권/현금/대체 비중(합 100%)과 리밸런싱 주기를 제안한다.
- 현금흐름: 월 납입액·기간·비상자금 목표를 수치로 제시한다.
- 부채/위험: DTI·금리·카드 이용률 등 실천 팁을 구체적으로 제시한다.
- 다음 30일 액션: 체크리스트 3~5개(간결 명령형)로 제시한다.

출력은 한국어 마크다운만 사용한다.
"""

        # 위험도 높은 문의 즉시 차단/대안 제시(월 이자 20% 이상 등)
        intercept = _intercept_high_interest_message(user_message)
        if intercept:
            return JsonResponse({'success': True, 'response': _clean_chat_response(intercept)})

        # 네트워크 AI 호출 (HF Inference)
        try:
            ai_response = hf_chat(
                chat_system_prompt + "\n\n" + chat_context,
                user_message,
                max_tokens=800,
                temperature=0.15,
                top_p=0.9,
            )
            ai_response = _clean_chat_response(ai_response or "") or "죄송합니다. 답변을 생성할 수 없습니다."
            return JsonResponse({'success': True, 'response': ai_response})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'AI 호출 오류: {str(e)}'})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'오류가 발생했습니다: {str(e)}'
        })
