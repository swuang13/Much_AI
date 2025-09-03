// Much 메인 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 페이지 로드 시 애니메이션
    animateOnLoad();
    
    // 퀴즈 옵션 선택 기능
    initQuizOptions();
    
    // 폼 유효성 검사
    initFormValidation();
    
    // 진행률 바 애니메이션
    initProgressBars();
    
    // 카드 호버 효과
    initCardHoverEffects();
});

// 페이지 로드 애니메이션
function animateOnLoad() {
    const elements = document.querySelectorAll('.card, .dashboard-card, .stat-card');
    elements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            element.style.transition = 'all 0.6s ease-out';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// 퀴즈 옵션 선택 기능
function initQuizOptions() {
    const quizOptions = document.querySelectorAll('.quiz-option');
    
    quizOptions.forEach(option => {
        option.addEventListener('click', function() {
            // 같은 질문의 다른 옵션 선택 해제
            const questionId = this.closest('.quiz-question').dataset.questionId;
            const sameQuestionOptions = document.querySelectorAll(`[data-question-id="${questionId}"] .quiz-option`);
            sameQuestionOptions.forEach(opt => opt.classList.remove('selected'));
            
            // 현재 옵션 선택
            this.classList.add('selected');
            
            // 라디오 버튼 자동 선택
            const radioInput = this.querySelector('input[type="radio"]');
            if (radioInput) {
                radioInput.checked = true;
            }
        });
    });
}

// 폼 유효성 검사
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                showFormErrors(this);
            }
        });
    });
}

// 폼 유효성 검사 함수
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// 폼 오류 표시
function showFormErrors(form) {
    const errorDiv = form.querySelector('.form-errors') || createErrorDiv(form);
    errorDiv.innerHTML = '<div class="alert alert-danger">필수 항목을 모두 입력해주세요.</div>';
    errorDiv.style.display = 'block';
}

// 오류 메시지 div 생성
function createErrorDiv(form) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-errors mb-3';
    form.insertBefore(errorDiv, form.firstChild);
    return errorDiv;
}

// 진행률 바 애니메이션
function initProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const progressBar = entry.target;
                const targetWidth = progressBar.getAttribute('aria-valuenow') + '%';
                
                progressBar.style.width = '0%';
                setTimeout(() => {
                    progressBar.style.transition = 'width 1s ease-in-out';
                    progressBar.style.width = targetWidth;
                }, 200);
                
                observer.unobserve(progressBar);
            }
        });
    });
    
    progressBars.forEach(bar => observer.observe(bar));
}

// 카드 호버 효과
function initCardHoverEffects() {
    const cards = document.querySelectorAll('.card, .dashboard-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
        });
    });
}

// 점수 애니메이션
function animateScore(element, targetScore, duration = 1000) {
    let startScore = 0;
    const increment = targetScore / (duration / 16); // 60fps
    
    function updateScore() {
        startScore += increment;
        if (startScore < targetScore) {
            element.textContent = Math.floor(startScore);
            requestAnimationFrame(updateScore);
        } else {
            element.textContent = targetScore;
        }
    }
    
    updateScore();
}

// 토스트 메시지 표시
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">알림</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    
    toastContainer.appendChild(toast);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// 토스트 컨테이너 생성
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// AJAX 요청 헬퍼 함수
function ajaxRequest(url, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(method, url);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        
        if (data && method === 'POST') {
            xhr.setRequestHeader('Content-Type', 'application/json');
        }
        
        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    resolve(response);
                } catch (e) {
                    resolve(xhr.responseText);
                }
            } else {
                reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
            }
        };
        
        xhr.onerror = function() {
            reject(new Error('Network error'));
        };
        
        if (data && method === 'POST') {
            xhr.send(JSON.stringify(data));
        } else {
            xhr.send();
        }
    });
}

// 로딩 스피너 표시/숨김
function showLoading(element) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    element.appendChild(spinner);
    element.disabled = true;
}

function hideLoading(element) {
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
    element.disabled = false;
}

// 숫자 포맷팅 (천 단위 콤마)
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// 날짜 포맷팅
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// URL 파라미터 가져오기
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// 로컬 스토리지 헬퍼
const Storage = {
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Storage set error:', e);
        }
    },
    
    get: function(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage get error:', e);
            return defaultValue;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('Storage remove error:', e);
        }
    }
};

// 전역 함수로 노출
window.FinancialAcademy = {
    showToast,
    ajaxRequest,
    showLoading,
    hideLoading,
    formatNumber,
    formatDate,
    getUrlParameter,
    Storage,
    animateScore
};
