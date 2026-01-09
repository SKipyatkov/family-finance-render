// Модуль для работы с API
class FinanceAPI {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.userId = localStorage.getItem('user_id');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': this.userId
            }
        };

        const config = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Транзакции
    async getTransactions(params = {}) {
        const query = new URLSearchParams({
            user_id: this.userId,
            ...params
        }).toString();

        return this.request(`/api/transactions?${query}`);
    }

    async addTransaction(transactionData) {
        return this.request('/api/transactions', {
            method: 'POST',
            body: JSON.stringify(transactionData)
        });
    }

    async deleteTransaction(transactionId) {
        return this.request(`/api/transactions/${transactionId}`, {
            method: 'DELETE'
        });
    }

    // Отчеты
    async getMonthlyReport() {
        return this.request(`/api/reports/monthly?user_id=${this.userId}`);
    }

    async getCategoryReport(startDate, endDate) {
        const params = new URLSearchParams({ user_id: this.userId });
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        return this.request(`/api/reports/categories?${params}`);
    }

    // Семья
    async getFamily() {
        return this.request(`/api/family?user_id=${this.userId}`);
    }

    async createFamily(familyName) {
        return this.request('/api/family', {
            method: 'POST',
            body: JSON.stringify({
                action: 'create',
                family_name: familyName,
                user_id: this.userId
            })
        });
    }

    async joinFamily(inviteCode) {
        return this.request('/api/family', {
            method: 'POST',
            body: JSON.stringify({
                action: 'join',
                invite_code: inviteCode,
                user_id: this.userId
            })
        });
    }

    async getFamilyMembers() {
        const family = await this.getFamily();
        if (family && family.id) {
            return this.request(`/api/family/${family.id}/members`);
        }
        return [];
    }

    // Синхронизация
    async sync(lastSync) {
        return this.request('/api/sync', {
            method: 'POST',
            body: JSON.stringify({
                user_id: this.userId,
                last_sync: lastSync
            })
        });
    }

    // Бюджет
    async getBudgets() {
        return this.request(`/api/budgets?user_id=${this.userId}`);
    }

    async setBudget(category, amountLimit, period = 'monthly') {
        return this.request('/api/budgets', {
            method: 'POST',
            body: JSON.stringify({
                user_id: this.userId,
                category: category,
                amount_limit: amountLimit,
                period: period
            })
        });
    }

    // Категории
    async getCategories(type = null) {
        const params = new URLSearchParams({ user_id: this.userId });
        if (type) params.append('type', type);

        return this.request(`/api/categories?${params}`);
    }

    // Уведомления
    async getNotifications() {
        return this.request(`/api/notifications?user_id=${this.userId}`);
    }

    async markNotificationRead(notificationId) {
        return this.request(`/api/notifications/${notificationId}/read`, {
            method: 'PUT'
        });
    }
}

// Создаем глобальный экземпляр API
window.financeAPI = new FinanceAPI();