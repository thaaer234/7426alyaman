/**
 * Panato Employee Sidebar JavaScript
 * Handles sidebar interactions, zakat calculations, and responsive behavior
 */

class PanatoEmployeeSidebar {
    constructor() {
        this.sidebar = document.getElementById('employeeSidebar');
        this.overlay = document.querySelector('.sidebar-overlay');
        this.mobileToggle = document.querySelector('.mobile-toggle');
        this.navLinks = document.querySelectorAll('.nav-link');
        this.currentSection = 'personal-info';
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupResponsiveBehavior();
        this.loadUserPreferences();
        this.initializeZakatCalculator();
    }
    
    setupEventListeners() {
        // Navigation links
        this.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.dataset.section;
                if (section) {
                    this.navigateToSection(section);
                }
            });
        });
        
        // Mobile toggle
        if (this.mobileToggle) {
            this.mobileToggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }
        
        // Overlay click
        if (this.overlay) {
            this.overlay.addEventListener('click', () => {
                this.closeSidebar();
            });
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSidebar();
                this.closeZakatCalculator();
            }
        });
        
        // Window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }
    
    setupResponsiveBehavior() {
        this.checkMobileView();
    }
    
    checkMobileView() {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            this.sidebar?.classList.add('mobile-view');
        } else {
            this.sidebar?.classList.remove('mobile-view', 'active');
            this.overlay?.classList.remove('active');
        }
    }
    
    handleResize() {
        this.checkMobileView();
    }
    
    navigateToSection(section) {
        // Remove active class from all links
        this.navLinks.forEach(link => {
            link.classList.remove('active');
        });
        
        // Add active class to current link
        const activeLink = document.querySelector(`[data-section="${section}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
        
        // Update current section
        this.currentSection = section;
        
        // Trigger section change event
        this.onSectionChange(section);
        
        // Close sidebar on mobile after navigation
        if (window.innerWidth <= 768) {
            this.closeSidebar();
        }
    }
    
    onSectionChange(section) {
        // Emit custom event for main content to listen to
        const event = new CustomEvent('sidebarSectionChange', {
            detail: { section }
        });
        document.dispatchEvent(event);
        
        // Update URL hash for deep linking
        window.location.hash = section;
        
        // Analytics tracking
        this.trackNavigation(section);
    }
    
    trackNavigation(section) {
        // Track navigation for analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'sidebar_navigation', {
                'section': section,
                'user_id': this.getCurrentUserId()
            });
        }
    }
    
    getCurrentUserId() {
        // Get current user ID from DOM or global variable
        const userElement = document.querySelector('[data-user-id]');
        return userElement ? userElement.dataset.userId : null;
    }
    
    toggleSidebar() {
        if (this.sidebar?.classList.contains('active')) {
            this.closeSidebar();
        } else {
            this.openSidebar();
        }
    }
    
    openSidebar() {
        this.sidebar?.classList.add('active');
        this.overlay?.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    closeSidebar() {
        this.sidebar?.classList.remove('active');
        this.overlay?.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    loadUserPreferences() {
        // Load user preferences from localStorage
        const preferences = localStorage.getItem('panato_sidebar_preferences');
        if (preferences) {
            try {
                const prefs = JSON.parse(preferences);
                if (prefs.lastSection) {
                    this.navigateToSection(prefs.lastSection);
                }
            } catch (e) {
                console.warn('Failed to load sidebar preferences:', e);
            }
        }
        
        // Load from URL hash
        const hash = window.location.hash.substring(1);
        if (hash) {
            this.navigateToSection(hash);
        }
    }
    
    saveUserPreferences() {
        const preferences = {
            lastSection: this.currentSection,
            timestamp: Date.now()
        };
        localStorage.setItem('panato_sidebar_preferences', JSON.stringify(preferences));
    }
    
    // Zakat Calculator Methods
    initializeZakatCalculator() {
        const monthlyIncomeInput = document.getElementById('monthlyIncome');
        const annualIncomeInput = document.getElementById('annualIncome');
        
        if (monthlyIncomeInput && annualIncomeInput) {
            // Auto-calculate annual income
            monthlyIncomeInput.addEventListener('input', () => {
                const monthly = parseFloat(monthlyIncomeInput.value) || 0;
                annualIncomeInput.value = (monthly * 12).toFixed(2);
            });
            
            // Initialize with current values
            const monthly = parseFloat(monthlyIncomeInput.value) || 0;
            annualIncomeInput.value = (monthly * 12).toFixed(2);
        }
    }
    
    calculateZakat() {
        const monthlyIncome = parseFloat(document.getElementById('monthlyIncome')?.value) || 0;
        const annualIncome = monthlyIncome * 12;
        const nisab = parseFloat(document.getElementById('nisabAmount')?.value) || 85000;
        const zakatRate = parseFloat(document.getElementById('zakatRate')?.value) || 2.5;
        
        let annualZakat = 0;
        let monthlyZakat = 0;
        
        if (annualIncome >= nisab) {
            annualZakat = (annualIncome * zakatRate) / 100;
            monthlyZakat = annualZakat / 12;
        }
        
        // Update display
        const annualZakatElement = document.getElementById('annualZakat');
        const monthlyZakatElement = document.getElementById('monthlyZakat');
        
        if (annualZakatElement) {
            annualZakatElement.textContent = this.formatCurrency(annualZakat);
        }
        
        if (monthlyZakatElement) {
            monthlyZakatElement.textContent = this.formatCurrency(monthlyZakat);
        }
        
        // Show success message
        this.showZakatMessage(annualIncome >= nisab, annualZakat);
        
        return { annualZakat, monthlyZakat, isEligible: annualIncome >= nisab };
    }
    
    showZakatMessage(isEligible, amount) {
        const existingMessage = document.querySelector('.zakat-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const message = document.createElement('div');
        message.className = `alert ${isEligible ? 'alert-success' : 'alert-info'} zakat-message`;
        message.style.marginTop = '16px';
        
        if (isEligible) {
            message.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <strong>مبروك!</strong> راتبك يستوجب الزكاة.
                <br>المبلغ السنوي: ${this.formatCurrency(amount)}
            `;
        } else {
            message.innerHTML = `
                <i class="fas fa-info-circle"></i>
                راتبك الحالي أقل من النصاب المطلوب للزكاة.
            `;
        }
        
        const resultSection = document.querySelector('.calculation-result');
        if (resultSection) {
            resultSection.appendChild(message);
        }
    }
    
    async saveZakatCalculation() {
        const calculation = this.calculateZakat();
        
        try {
            const response = await fetch('/api/employee/zakat-calculation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    monthly_income: parseFloat(document.getElementById('monthlyIncome')?.value) || 0,
                    annual_zakat: calculation.annualZakat,
                    monthly_zakat: calculation.monthlyZakat,
                    is_eligible: calculation.isEligible,
                    calculation_date: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                this.showSuccessMessage('تم حفظ حساب الزكاة بنجاح');
                this.updateZakatInfo(calculation);
            } else {
                throw new Error('Failed to save calculation');
            }
        } catch (error) {
            console.error('Error saving zakat calculation:', error);
            this.showErrorMessage('حدث خطأ أثناء حفظ الحساب');
        }
    }
    
    updateZakatInfo(calculation) {
        // Update the zakat info in the sidebar
        const lastCalculationElement = document.querySelector('.zakat-stat .stat-value');
        if (lastCalculationElement) {
            lastCalculationElement.textContent = new Date().toLocaleDateString('ar-SA');
        }
        
        const amountElement = document.querySelectorAll('.zakat-stat .stat-value')[1];
        if (amountElement) {
            amountElement.textContent = this.formatCurrency(calculation.annualZakat);
        }
    }
    
    formatCurrency(amount) {
        return new Intl.NumberFormat('ar-SA', {
            style: 'decimal',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount) + ' ل.س';
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }
    
    showErrorMessage(message) {
        this.showMessage(message, 'error');
    }
    
    showMessage(message, type) {
        // Create and show toast message
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Show toast
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Hide toast after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // Public API methods
    setActiveSection(section) {
        this.navigateToSection(section);
    }
    
    getActiveSection() {
        return this.currentSection;
    }
    
    refreshUserData() {
        // Refresh user data from server
        // This would typically make an API call to get updated user information
        console.log('Refreshing user data...');
    }
    
    // Cleanup method
    destroy() {
        // Remove event listeners and clean up
        this.navLinks.forEach(link => {
            link.removeEventListener('click', this.navigateToSection);
        });
        
        if (this.mobileToggle) {
            this.mobileToggle.removeEventListener('click', this.toggleSidebar);
        }
        
        window.removeEventListener('resize', this.handleResize);
        document.removeEventListener('keydown', this.handleKeydown);
    }
}

// Global functions for template usage
function openZakatCalculator() {
    const modal = document.getElementById('zakatModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Auto-calculate on open
        if (window.panatoSidebar) {
            window.panatoSidebar.calculateZakat();
        }
    }
}

function closeZakatCalculator() {
    const modal = document.getElementById('zakatModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function calculateZakat() {
    if (window.panatoSidebar) {
        return window.panatoSidebar.calculateZakat();
    }
}

function saveZakatCalculation() {
    if (window.panatoSidebar) {
        window.panatoSidebar.saveZakatCalculation();
    }
}

function toggleSidebar() {
    if (window.panatoSidebar) {
        window.panatoSidebar.toggleSidebar();
    }
}

function closeSidebar() {
    if (window.panatoSidebar) {
        window.panatoSidebar.closeSidebar();
    }
}

// Initialize sidebar when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if sidebar exists
    if (document.getElementById('employeeSidebar')) {
        window.panatoSidebar = new PanatoEmployeeSidebar();
        
        // Listen for section changes from main content
        document.addEventListener('mainContentSectionChange', function(e) {
            if (window.panatoSidebar) {
                window.panatoSidebar.setActiveSection(e.detail.section);
            }
        });
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PanatoEmployeeSidebar;
}