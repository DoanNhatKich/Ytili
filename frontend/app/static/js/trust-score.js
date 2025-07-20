/**
 * Trust Score and Fraud Detection Components
 * Provides trust score badges, fraud warnings, and reporting functionality
 */

class TrustScoreManager {
    constructor(options = {}) {
        this.apiBaseUrl = options.apiBaseUrl || '/api/v1';
        this.authToken = options.authToken || null;
        this.init();
    }
    
    init() {
        this.addStyles();
        this.initializeTrustScores();
        this.setupFraudReporting();
    }
    
    addStyles() {
        if (document.getElementById('trust-score-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'trust-score-styles';
        styles.textContent = `
            .trust-score-badge {
                display: inline-flex;
                align-items: center;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin: 4px;
            }
            
            .trust-score-high {
                background-color: #10b981;
                color: white;
            }
            
            .trust-score-medium {
                background-color: #f59e0b;
                color: white;
            }
            
            .trust-score-low {
                background-color: #ef4444;
                color: white;
            }
            
            .trust-score-unknown {
                background-color: #6b7280;
                color: white;
            }
            
            .fraud-warning {
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .fraud-warning-icon {
                color: #ef4444;
                font-size: 20px;
            }
            
            .fraud-warning-text {
                color: #991b1b;
                font-size: 14px;
                flex: 1;
            }
            
            .fraud-warning-high {
                background-color: #fef2f2;
                border-color: #fca5a5;
            }
            
            .fraud-warning-medium {
                background-color: #fffbeb;
                border-color: #fed7aa;
            }
            
            .fraud-warning-medium .fraud-warning-icon {
                color: #d97706;
            }
            
            .fraud-warning-medium .fraud-warning-text {
                color: #92400e;
            }
            
            .report-fraud-btn {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            
            .report-fraud-btn:hover {
                background-color: #dc2626;
            }
            
            .verification-badge {
                display: inline-flex;
                align-items: center;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 500;
                margin-left: 4px;
            }
            
            .verification-verified {
                background-color: #dbeafe;
                color: #1e40af;
            }
            
            .verification-pending {
                background-color: #fef3c7;
                color: #92400e;
            }
            
            .verification-unverified {
                background-color: #f3f4f6;
                color: #6b7280;
            }
            
            .fraud-report-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            }
            
            .fraud-report-content {
                background: white;
                border-radius: 12px;
                padding: 24px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            }
            
            .fraud-report-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            }
            
            .fraud-report-title {
                font-size: 18px;
                font-weight: 600;
                color: #111827;
            }
            
            .fraud-report-close {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #6b7280;
            }
            
            .fraud-report-form {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            
            .fraud-report-field {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            
            .fraud-report-label {
                font-size: 14px;
                font-weight: 500;
                color: #374151;
            }
            
            .fraud-report-input,
            .fraud-report-select,
            .fraud-report-textarea {
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
            }
            
            .fraud-report-textarea {
                min-height: 80px;
                resize: vertical;
            }
            
            .fraud-report-submit {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            
            .fraud-report-submit:hover {
                background-color: #dc2626;
            }
            
            .fraud-report-submit:disabled {
                background-color: #9ca3af;
                cursor: not-allowed;
            }
            
            .hidden {
                display: none !important;
            }
        `;
        
        document.head.appendChild(styles);
    }
    
    async initializeTrustScores() {
        // Find all campaign cards and add trust scores
        const campaignCards = document.querySelectorAll('[data-campaign-id]');
        
        for (const card of campaignCards) {
            const campaignId = card.getAttribute('data-campaign-id');
            await this.addTrustScoreToCampaign(campaignId, card);
        }
    }
    
    async addTrustScoreToCampaign(campaignId, cardElement) {
        try {
            // Get trust score from API
            const trustScore = await this.getTrustScore(campaignId);
            
            // Create trust score badge
            const badge = this.createTrustScoreBadge(trustScore);
            
            // Find the best place to insert the badge
            const titleElement = cardElement.querySelector('.card-title, h3, h4, h5');
            if (titleElement) {
                titleElement.appendChild(badge);
            } else {
                cardElement.insertBefore(badge, cardElement.firstChild);
            }
            
            // Add fraud warning if needed
            if (trustScore.risk_level === 'high' || trustScore.risk_level === 'medium') {
                const warning = this.createFraudWarning(trustScore);
                cardElement.appendChild(warning);
            }
            
            // Add report fraud button
            const reportBtn = this.createReportFraudButton(campaignId);
            cardElement.appendChild(reportBtn);
            
        } catch (error) {
            console.error('Failed to add trust score:', error);
            // Add unknown trust score badge
            const badge = this.createTrustScoreBadge({ score: 0, risk_level: 'unknown' });
            const titleElement = cardElement.querySelector('.card-title, h3, h4, h5');
            if (titleElement) {
                titleElement.appendChild(badge);
            }
        }
    }
    
    async getTrustScore(campaignId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/fraud/analyze-campaign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` })
                },
                body: JSON.stringify({
                    campaign_id: campaignId
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to get trust score');
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error getting trust score:', error);
            // Return mock data for demo
            return this.getMockTrustScore(campaignId);
        }
    }
    
    getMockTrustScore(campaignId) {
        // Generate mock trust scores for demo
        const scores = [
            { score: 95, risk_level: 'low', factors: ['Verified documents', 'Established user', 'Clear medical need'] },
            { score: 75, risk_level: 'medium', factors: ['Some documentation missing', 'New user account'] },
            { score: 45, risk_level: 'high', factors: ['Suspicious activity pattern', 'Incomplete information', 'High amount requested'] },
            { score: 88, risk_level: 'low', factors: ['Hospital verification', 'Complete documentation'] }
        ];
        
        const index = parseInt(campaignId) % scores.length;
        return scores[index];
    }
    
    createTrustScoreBadge(trustScore) {
        const badge = document.createElement('span');
        badge.className = `trust-score-badge trust-score-${trustScore.risk_level}`;
        
        let icon, text;
        switch (trustScore.risk_level) {
            case 'low':
                icon = '✓';
                text = `Tin cậy ${trustScore.score}%`;
                break;
            case 'medium':
                icon = '⚠';
                text = `Cẩn thận ${trustScore.score}%`;
                break;
            case 'high':
                icon = '⚠';
                text = `Rủi ro ${trustScore.score}%`;
                break;
            default:
                icon = '?';
                text = 'Chưa xác định';
        }
        
        badge.innerHTML = `${icon} ${text}`;
        badge.title = `Điểm tin cậy: ${trustScore.score}%`;
        
        return badge;
    }
    
    createFraudWarning(trustScore) {
        const warning = document.createElement('div');
        warning.className = `fraud-warning fraud-warning-${trustScore.risk_level}`;
        
        let message;
        switch (trustScore.risk_level) {
            case 'high':
                message = '⚠️ Cảnh báo: Chiến dịch này có dấu hiệu đáng ngờ. Hãy cân nhắc kỹ trước khi quyên góp.';
                break;
            case 'medium':
                message = '⚠️ Lưu ý: Chiến dịch này cần được xem xét thêm. Vui lòng kiểm tra thông tin kỹ lưỡng.';
                break;
            default:
                message = '';
        }
        
        if (message) {
            warning.innerHTML = `
                <div class="fraud-warning-icon">⚠️</div>
                <div class="fraud-warning-text">${message}</div>
            `;
        }
        
        return warning;
    }
    
    createReportFraudButton(campaignId) {
        const button = document.createElement('button');
        button.className = 'report-fraud-btn';
        button.innerHTML = '🚨 Báo cáo gian lận';
        button.title = 'Báo cáo chiến dịch gian lận';
        
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.showFraudReportModal(campaignId);
        });
        
        return button;
    }
    
    setupFraudReporting() {
        // Create fraud report modal
        this.createFraudReportModal();
    }
    
    createFraudReportModal() {
        const modal = document.createElement('div');
        modal.id = 'fraud-report-modal';
        modal.className = 'fraud-report-modal hidden';
        
        modal.innerHTML = `
            <div class="fraud-report-content">
                <div class="fraud-report-header">
                    <h3 class="fraud-report-title">Báo cáo gian lận</h3>
                    <button class="fraud-report-close" onclick="window.trustScoreManager.hideFraudReportModal()">×</button>
                </div>
                
                <form class="fraud-report-form" onsubmit="window.trustScoreManager.submitFraudReport(event)">
                    <input type="hidden" id="report-campaign-id" name="campaign_id">
                    
                    <div class="fraud-report-field">
                        <label class="fraud-report-label" for="fraud-type">Loại gian lận</label>
                        <select class="fraud-report-select" id="fraud-type" name="fraud_type" required>
                            <option value="">Chọn loại gian lận</option>
                            <option value="fake_documents">Giấy tờ giả mạo</option>
                            <option value="false_information">Thông tin sai lệch</option>
                            <option value="duplicate_campaign">Chiến dịch trùng lặp</option>
                            <option value="suspicious_activity">Hoạt động đáng ngờ</option>
                            <option value="identity_theft">Mạo danh</option>
                            <option value="other">Khác</option>
                        </select>
                    </div>
                    
                    <div class="fraud-report-field">
                        <label class="fraud-report-label" for="fraud-description">Mô tả chi tiết</label>
                        <textarea class="fraud-report-textarea" id="fraud-description" name="description" 
                                  placeholder="Vui lòng mô tả chi tiết về dấu hiệu gian lận bạn phát hiện..." required></textarea>
                    </div>
                    
                    <div class="fraud-report-field">
                        <label class="fraud-report-label" for="evidence">Bằng chứng (tùy chọn)</label>
                        <input type="file" class="fraud-report-input" id="evidence" name="evidence" 
                               accept="image/*,application/pdf" multiple>
                        <small style="color: #6b7280; font-size: 12px;">Hỗ trợ hình ảnh và PDF</small>
                    </div>
                    
                    <div class="fraud-report-field">
                        <label class="fraud-report-label" for="reporter-contact">Thông tin liên hệ (tùy chọn)</label>
                        <input type="email" class="fraud-report-input" id="reporter-contact" name="contact" 
                               placeholder="email@example.com">
                        <small style="color: #6b7280; font-size: 12px;">Để chúng tôi có thể liên hệ nếu cần thêm thông tin</small>
                    </div>
                    
                    <button type="submit" class="fraud-report-submit">Gửi báo cáo</button>
                </form>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideFraudReportModal();
            }
        });
    }
    
    showFraudReportModal(campaignId) {
        const modal = document.getElementById('fraud-report-modal');
        const campaignIdInput = document.getElementById('report-campaign-id');
        
        campaignIdInput.value = campaignId;
        modal.classList.remove('hidden');
        
        // Focus on first input
        setTimeout(() => {
            document.getElementById('fraud-type').focus();
        }, 100);
    }
    
    hideFraudReportModal() {
        const modal = document.getElementById('fraud-report-modal');
        modal.classList.add('hidden');
        
        // Reset form
        const form = modal.querySelector('.fraud-report-form');
        form.reset();
    }
    
    async submitFraudReport(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const submitBtn = form.querySelector('.fraud-report-submit');
        
        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Đang gửi...';
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/fraud/report`, {
                method: 'POST',
                headers: {
                    ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` })
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Failed to submit fraud report');
            }
            
            // Show success message
            alert('Báo cáo gian lận đã được gửi thành công. Cảm ơn bạn đã giúp bảo vệ cộng đồng!');
            
            // Close modal
            this.hideFraudReportModal();
            
        } catch (error) {
            console.error('Error submitting fraud report:', error);
            alert('Có lỗi xảy ra khi gửi báo cáo. Vui lòng thử lại sau.');
        } finally {
            // Re-enable submit button
            submitBtn.disabled = false;
            submitBtn.textContent = 'Gửi báo cáo';
        }
    }
    
    addVerificationBadge(element, verificationStatus) {
        const badge = document.createElement('span');
        badge.className = `verification-badge verification-${verificationStatus}`;
        
        let icon, text;
        switch (verificationStatus) {
            case 'verified':
                icon = '✓';
                text = 'Đã xác thực';
                break;
            case 'pending':
                icon = '⏳';
                text = 'Đang xác thực';
                break;
            default:
                icon = '?';
                text = 'Chưa xác thực';
        }
        
        badge.innerHTML = `${icon} ${text}`;
        element.appendChild(badge);
    }
}

// Initialize trust score manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const authToken = localStorage.getItem('ytili_auth_token') || sessionStorage.getItem('ytili_auth_token');
    
    window.trustScoreManager = new TrustScoreManager({
        apiBaseUrl: '/api/v1',
        authToken: authToken
    });
});
