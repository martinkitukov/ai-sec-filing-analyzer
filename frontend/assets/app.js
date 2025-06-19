/**
 * AI SEC Filing Analyzer - Frontend JavaScript
 * 
 * This script handles all frontend interactions including:
 * - Form submission and validation
 * - API communication with FastAPI backend
 * - UI state management and animations
 * - Error handling and user feedback
 */

class SECAnalyzer {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api/v1';
        this.form = document.getElementById('analysisForm');
        this.loadingSection = document.getElementById('loadingSection');
        this.resultsSection = document.getElementById('resultsSection');
        this.errorSection = document.getElementById('errorSection');
        this.analyzeBtn = document.getElementById('analyzeBtn');
        
        this.initializeEventListeners();
        this.loadExampleQuestions();
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmission();
        });

        // Example question clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.list-unstyled li')) {
                this.fillExampleQuestion(e.target.closest('li').textContent);
            }
        });

        // Real-time URL validation
        const urlInput = document.getElementById('filingUrl');
        urlInput.addEventListener('input', this.validateURL);
        
        // Real-time question validation
        const questionInput = document.getElementById('question');
        questionInput.addEventListener('input', this.validateQuestion);
    }

    /**
     * Handle form submission
     */
    async handleFormSubmission() {
        const formData = this.getFormData();
        
        if (!this.validateForm(formData)) {
            return;
        }

        this.setLoadingState(true);
        this.hideAllSections();
        this.showSection(this.loadingSection);

        try {
            const response = await this.analyzeDocument(formData);
            this.displayResults(response);
        } catch (error) {
            this.displayError(error);
        } finally {
            this.setLoadingState(false);
        }
    }

    /**
     * Get form data
     */
    getFormData() {
        return {
            filing_url: document.getElementById('filingUrl').value.trim(),
            question: document.getElementById('question').value.trim(),
            include_context: document.getElementById('includeContext').checked,
            max_response_length: 4000
        };
    }

    /**
     * Validate form data
     */
    validateForm(data) {
        const errors = [];

        // URL validation
        if (!data.filing_url) {
            errors.push('SEC filing URL is required');
        } else if (!this.isValidSecURL(data.filing_url)) {
            errors.push('Please enter a valid SEC filing URL');
        }

        // Question validation
        if (!data.question) {
            errors.push('Question is required');
        } else if (data.question.length < 10) {
            errors.push('Question must be at least 10 characters long');
        } else if (data.question.length > 500) {
            errors.push('Question must be less than 500 characters');
        }

        if (errors.length > 0) {
            this.showValidationErrors(errors);
            return false;
        }

        return true;
    }

    /**
     * Validate SEC URL format
     */
    isValidSecURL(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.includes('sec.gov') || 
                   url.toLowerCase().includes('edgar');
        } catch {
            return false;
        }
    }

    /**
     * Real-time URL validation
     */
    validateURL(event) {
        const input = event.target;
        const url = input.value.trim();
        
        if (url && !this.isValidSecURL(url)) {
            input.classList.add('is-invalid');
            this.showInputError(input, 'Please enter a valid SEC filing URL');
        } else {
            input.classList.remove('is-invalid');
            this.hideInputError(input);
        }
    }

    /**
     * Real-time question validation
     */
    validateQuestion(event) {
        const input = event.target;
        const question = input.value.trim();
        
        if (question.length > 0 && question.length < 10) {
            input.classList.add('is-invalid');
            this.showInputError(input, 'Question must be at least 10 characters long');
        } else if (question.length > 500) {
            input.classList.add('is-invalid');
            this.showInputError(input, 'Question must be less than 500 characters');
        } else {
            input.classList.remove('is-invalid');
            this.hideInputError(input);
        }
    }

    /**
     * Show input error message
     */
    showInputError(input, message) {
        let errorDiv = input.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            input.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }

    /**
     * Hide input error message
     */
    hideInputError(input) {
        const errorDiv = input.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    /**
     * Show validation errors
     */
    showValidationErrors(errors) {
        const errorHtml = `
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>Please fix the following errors:</h6>
                <ul class="mb-0">
                    ${errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Insert before the form
        this.form.insertAdjacentHTML('beforebegin', errorHtml);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alert = document.querySelector('.alert-warning');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }

    /**
     * Make API call to analyze document
     */
    async analyzeDocument(data) {
        const response = await fetch(`${this.apiBaseUrl}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail?.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Display analysis results
     */
    displayResults(data) {
        // Populate result elements
        document.getElementById('resultQuestion').textContent = data.question;
        document.getElementById('resultAnswer').innerHTML = this.formatAnswer(data.answer);
        document.getElementById('confidence').textContent = `${(data.confidence_score * 100).toFixed(1)}%`;
        document.getElementById('processingTime').textContent = `${data.processing_time_ms}ms`;
        document.getElementById('aiModel').textContent = data.ai_model_info.llm || 'Google Gemini';

        // Show results section with animation
        this.hideAllSections();
        this.showSection(this.resultsSection, 'fade-in');
        
        // Scroll to results
        this.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Format AI answer for display
     */
    formatAnswer(answer) {
        // Convert line breaks to HTML
        let formatted = answer.replace(/\n/g, '<br>');
        
        // Convert bullet points to HTML lists
        formatted = formatted.replace(/^\s*[\-\*\•]\s+(.+)$/gm, '<li>$1</li>');
        if (formatted.includes('<li>')) {
            formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        }
        
        // Convert numbered lists
        formatted = formatted.replace(/^\s*\d+\.\s+(.+)$/gm, '<li>$1</li>');
        if (formatted.includes('<li>') && !formatted.includes('<ul>')) {
            formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ol>$1</ol>');
        }
        
        return formatted;
    }

    /**
     * Display error message
     */
    displayError(error) {
        console.error('Analysis error:', error);
        
        const errorMessage = this.getErrorMessage(error);
        document.getElementById('errorMessage').innerHTML = errorMessage;
        
        this.hideAllSections();
        this.showSection(this.errorSection, 'slide-in');
    }

    /**
     * Get user-friendly error message
     */
    getErrorMessage(error) {
        const errorStr = error.toString().toLowerCase();
        
        if (errorStr.includes('network') || errorStr.includes('fetch')) {
            return `
                <strong>Network Error:</strong> Unable to connect to the AI service. 
                <br><small>Please check your internet connection and try again.</small>
            `;
        } else if (errorStr.includes('cors')) {
            return `
                <strong>Configuration Error:</strong> CORS issue detected. 
                <br><small>The backend server may need to be configured for your domain.</small>
            `;
        } else if (errorStr.includes('google_api_key')) {
            return `
                <strong>Configuration Error:</strong> Google AI API key is not configured. 
                <br><small>Please set up the GOOGLE_API_KEY environment variable.</small>
            `;
        } else if (errorStr.includes('rate limit')) {
            return `
                <strong>Rate Limit Exceeded:</strong> Too many requests. 
                <br><small>Please wait a moment before trying again.</small>
            `;
        } else {
            return `
                <strong>Analysis Error:</strong> ${error.message || 'An unexpected error occurred'} 
                <br><small>Please try again with a different filing or question.</small>
            `;
        }
    }

    /**
     * Set loading state
     */
    setLoadingState(loading) {
        if (loading) {
            this.analyzeBtn.disabled = true;
            this.analyzeBtn.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                Analyzing...
            `;
            document.body.classList.add('loading');
        } else {
            this.analyzeBtn.disabled = false;
            this.analyzeBtn.innerHTML = `
                <i class="fas fa-magic me-2"></i>
                Analyze Filing with AI
            `;
            document.body.classList.remove('loading');
        }
    }

    /**
     * Hide all result sections
     */
    hideAllSections() {
        [this.loadingSection, this.resultsSection, this.errorSection].forEach(section => {
            section.style.display = 'none';
            section.classList.remove('fade-in', 'slide-in');
        });
    }

    /**
     * Show a specific section with optional animation
     */
    showSection(section, animationClass = '') {
        section.style.display = 'block';
        if (animationClass) {
            section.classList.add(animationClass);
        }
    }

    /**
     * Fill example question into the form
     */
    fillExampleQuestion(questionText) {
        const cleanQuestion = questionText.replace(/^[^\w]*"?/, '').replace(/"?$/, '');
        document.getElementById('question').value = cleanQuestion;
        
        // Scroll to form
        this.form.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Focus on question field
        document.getElementById('question').focus();
    }

    /**
     * Load example questions from API
     */
    async loadExampleQuestions() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/examples`);
            if (response.ok) {
                const data = await response.json();
                // Example questions are already in the HTML, but this could be used
                // to dynamically load them from the backend
                console.log('Example questions loaded:', data.example_questions);
            }
        } catch (error) {
            console.warn('Could not load example questions:', error);
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SECAnalyzer();
});

// Add some utility functions for better UX
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Add copy to clipboard functionality for API examples
    document.querySelectorAll('pre, code').forEach(element => {
        element.addEventListener('click', () => {
            navigator.clipboard.writeText(element.textContent).then(() => {
                // Show temporary success message
                const originalText = element.textContent;
                element.textContent = 'Copied!';
                element.style.background = '#d4edda';
                setTimeout(() => {
                    element.textContent = originalText;
                    element.style.background = '';
                }, 1000);
            });
        });
    });
}); 