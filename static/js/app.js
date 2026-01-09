// Основной модуль приложения
class FamilyFinanceApp {
    constructor() {
        this.userId = localStorage.getItem('user_id');
        this.userData = null;
        this.transactions = [];
        this.categories = {
            income: ['Зарплата', 'Фриланс', 'Инвестиции', 'Подарки', 'Прочее'],
            expense: ['Еда', 'Транспорт', 'Жилье', 'Развлечения', 'Здоровье', 'Образование', 'Одежда', 'Прочее']
        };
        this.init();
    }

    async init() {
        console.log('Инициализация приложения...');

        // Инициализация Telegram Web App
        this.initTelegramWebApp();

        // Загрузка данных пользователя
        await this.loadUserData();

        // Настройка навигации
        this.setupNavigation();

        // Настройка событий
        this.setupEventListeners();

        // Загрузка начальных данных
        await this.loadDashboardData();

        // Запуск синхронизации
        this.startSync();

        console.log('Приложение инициализировано');
    }

    initTelegramWebApp() {
        if (window.Telegram && window.Telegram.WebApp) {
            this.tg = window.Telegram.WebApp;
            this.tg.expand();
            this.tg.ready();

            // Устанавливаем тему Telegram
            this.applyTelegramTheme();

            // Обработка закрытия
            this.tg.onEvent('viewportChanged', (params) => {
                console.log('Viewport changed:', params);
            });
        }
    }

    applyTelegramTheme() {
        if (!this.tg) return;

        const theme = this.tg.themeParams;
        document.documentElement.style.setProperty('--primary-color', theme.button_color || '#4361ee');
        document.documentElement.style.setProperty('--bg-color', theme.bg_color || '#f5f7fb');
        document.documentElement.style.setProperty('--text-color', theme.text_color || '#212529');
    }

    async loadUserData() {
        try {
            if (!this.userId) {
                throw new Error('User ID not found');
            }

            // Здесь можно добавить запрос к API для получения данных пользователя
            this.userData = {
                id: this.userId,
                name: 'Пользователь',
                family: null
            };

            this.updateUI();
        } catch (error) {
            console.error('Ошибка загрузки данных пользователя:', error);
            this.showNotification('Ошибка загрузки данных', 'error');
        }
    }

    async loadDashboardData() {
        try {
            // Загрузка баланса
            await this.loadBalance();

            // Загрузка последних транзакций
            await this.loadRecentTransactions();

            // Загрузка графиков
            await this.loadCharts();

        } catch (error) {
            console.error('Ошибка загрузки дашборда:', error);
        }
    }

    async loadBalance() {
        try {
            // Запрос к API для получения баланса
            const response = await fetch(`/api/reports/monthly?user_id=${this.userId}`);
            const data = await response.json();

            // Обновление UI
            document.getElementById('totalBalance').textContent = `${data.balance.toLocaleString('ru-RU')} ₽`;
            document.getElementById('totalIncome').textContent = `${data.total_income.toLocaleString('ru-RU')} ₽`;
            document.getElementById('totalExpense').textContent = `${data.total_expense.toLocaleString('ru-RU')} ₽`;

            // Анимация обновления
            document.getElementById('totalBalance').classList.add('balance-update');
            setTimeout(() => {
                document.getElementById('totalBalance').classList.remove('balance-update');
            }, 500);

        } catch (error) {
            console.error('Ошибка загрузки баланса:', error);
        }
    }

    async loadRecentTransactions(limit = 10) {
        try {
            const response = await fetch(`/api/transactions?user_id=${this.userId}&limit=${limit}`);
            this.transactions = await response.json();

            this.renderTransactions(this.transactions, 'recentTransactions');
        } catch (error) {
            console.error('Ошибка загрузки транзакций:', error);
        }
    }

    renderTransactions(transactions, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (transactions.length === 0) {
            container.innerHTML = '<div class="empty-state">Нет транзакций</div>';
            return;
        }

        const html = transactions.map(transaction => this.createTransactionHTML(transaction)).join('');
        container.innerHTML = html;
    }

    createTransactionHTML(transaction) {
        const isIncome = transaction.type === 'income';
        const iconClass = isIncome ? 'fa-arrow-up' : 'fa-arrow-down';
        const amountClass = isIncome ? 'income' : 'expense';
        const sign = isIncome ? '+' : '-';

        const date = new Date(transaction.date);
        const formattedDate = date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: 'short'
        });

        return `
            <div class="transaction-item stagger-item" data-id="${transaction.id}">
                <div class="transaction-info">
                    <div class="transaction-category">
                        <div class="category-icon" style="background: ${this.getCategoryColor(transaction.category)}">
                            <i class="fas ${this.getCategoryIcon(transaction.category)}"></i>
                        </div>
                        <div>
                            <strong>${transaction.category}</strong>
                            <div class="transaction-description">${transaction.description || ''}</div>
                        </div>
                    </div>
                </div>
                <div class="transaction-details">
                    <div class="transaction-amount ${amountClass}">
                        ${sign}${transaction.amount.toLocaleString('ru-RU')} ₽
                    </div>
                    <div class="transaction-date">${formattedDate}</div>
                </div>
            </div>
        `;
    }

    getCategoryColor(category) {
        const colors = {
            'Еда': '#4cc9f0',
            'Транспорт': '#7209b7',
            'Жилье': '#f8961e',
            'Развлечения': '#f72585',
            'Здоровье': '#38b000',
            'Образование': '#4361ee',
            'Зарплата': '#4caf50',
            'Инвестиции': '#9c27b0'
        };
        return colors[category] || '#6c757d';
    }

    getCategoryIcon(category) {
        const icons = {
            'Еда': 'fa-utensils',
            'Транспорт': 'fa-car',
            'Жилье': 'fa-home',
            'Развлечения': 'fa-film',
            'Здоровье': 'fa-heart',
            'Образование': 'fa-graduation-cap',
            'Зарплата': 'fa-money-bill-wave',
            'Инвестиции': 'fa-chart-line'
        };
        return icons[category] || 'fa-receipt';
    }

    setupNavigation() {
        // Переключение между страницами
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.getAttribute('data-page');
                this.showPage(page);

                // Обновление активной кнопки
                document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');
            });
        });

        // Обработка хэшей в URL
        window.addEventListener('hashchange', () => {
            const page = window.location.hash.substring(1) || 'dashboard';
            this.showPage(page);
        });

        // Начальная страница
        const initialPage = window.location.hash.substring(1) || 'dashboard';
        this.showPage(initialPage);
    }

    showPage(pageName) {
        // Скрыть все страницы
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });

        // Показать выбранную страницу
        const targetPage = document.getElementById(pageName);
        if (targetPage) {
            targetPage.classList.add('active');
            targetPage.classList.add('page-transition');

            // Загрузить данные для страницы
            this.loadPageData(pageName);
        }
    }

    async loadPageData(pageName) {
        switch (pageName) {
            case 'dashboard':
                await this.loadDashboardData();
                break;
            case 'transactions':
                await this.loadAllTransactions();
                break;
            case 'reports':
                await this.loadReports();
                break;
            case 'family':
                await this.loadFamilyData();
                break;
            case 'budget':
                await this.loadBudgetData();
                break;
        }
    }

    setupEventListeners() {
        // Кнопка добавления транзакции
        document.getElementById('addTransactionBtn')?.addEventListener('click', () => {
            this.showTransactionModal();
        });

        // Быстрые действия
        document.querySelectorAll('[data-action="add-income"]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.showTransactionModal('income');
            });
        });

        document.querySelectorAll('[data-action="add-expense"]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.showTransactionModal('expense');
            });
        });

        // Закрытие модального окна
        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hideTransactionModal();
            });
        });

        // Обработка формы транзакции
        document.getElementById('transactionForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveTransaction();
        });

        // Переключение типа транзакции
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.getAttribute('data-type');
                this.setTransactionType(type);
            });
        });

        // Фильтры транзакций
        document.getElementById('applyFilters')?.addEventListener('click', () => {
            this.applyTransactionFilters();
        });

        // Синхронизация по кнопке
        document.getElementById('syncButton')?.addEventListener('click', () => {
            this.syncData();
        });
    }

    showTransactionModal(type = 'income') {
        const modal = document.getElementById('transactionModal');
        modal.classList.add('active');

        // Устанавливаем тип
        this.setTransactionType(type);

        // Заполняем категории
        this.populateCategories(type);

        // Устанавливаем сегодняшнюю дату
        document.getElementById('date').value = new Date().toISOString().split('T')[0];

        // Фокус на сумму
        setTimeout(() => {
            document.getElementById('amount').focus();
        }, 100);
    }

    hideTransactionModal() {
        const modal = document.getElementById('transactionModal');
        modal.classList.remove('active');
        document.getElementById('transactionForm').reset();
    }

    setTransactionType(type) {
        // Обновляем кнопки
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-type') === type) {
                btn.classList.add('active');
            }
        });

        // Обновляем скрытое поле
        document.getElementById('transType').value = type;

        // Обновляем категории
        this.populateCategories(type);
    }

    populateCategories(type) {
        const select = document.getElementById('category');
        select.innerHTML = '<option value="">Выберите категорию</option>';

        const categories = this.categories[type] || [];
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            select.appendChild(option);
        });
    }

    async saveTransaction() {
        try {
            const form = document.getElementById('transactionForm');
            const formData = new FormData(form);

            const transactionData = {
                user_id: parseInt(this.userId),
                amount: parseFloat(formData.get('amount')),
                category: formData.get('category'),
                type: formData.get('type'),
                description: formData.get('description'),
                date: formData.get('date')
            };

            // Валидация
            if (!transactionData.amount || transactionData.amount <= 0) {
                throw new Error('Укажите сумму');
            }

            if (!transactionData.category) {
                throw new Error('Выберите категорию');
            }

            // Отправка на сервер
            const response = await fetch('/api/transactions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(transactionData)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Транзакция сохранена!', 'success');
                this.hideTransactionModal();

                // Обновляем данные
                await this.loadDashboardData();

                // Добавляем анимацию
                this.animateNewTransaction(result.transaction_id);

            } else {
                throw new Error('Ошибка сохранения');
            }

        } catch (error) {
            console.error('Ошибка сохранения транзакции:', error);
            this.showNotification(error.message, 'error');
        }
    }

    animateNewTransaction(transactionId) {
        const transactionElement = document.querySelector(`[data-id="${transactionId}"]`);
        if (transactionElement) {
            transactionElement.classList.add('new');
            setTimeout(() => {
                transactionElement.classList.remove('new');
            }, 1000);
        }
    }

    async applyTransactionFilters() {
        const type = document.getElementById('filterType').value;
        const category = document.getElementById('filterCategory').value;
        const date = document.getElementById('filterDate').value;

        try {
            let url = `/api/transactions?user_id=${this.userId}`;

            if (type !== 'all') url += `&type=${type}`;
            if (category !== 'all') url += `&category=${category}`;
            if (date) url += `&date=${date}`;

            const response = await fetch(url);
            const transactions = await response.json();

            this.renderTransactions(transactions, 'transactionsList');

        } catch (error) {
            console.error('Ошибка фильтрации:', error);
        }
    }

    showNotification(message, type = 'info') {
        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
        `;

        // Стили для уведомления
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            z-index: 3000;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        // Удаляем через 3 секунды
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    startSync() {
        // Периодическая синхронизация каждые 30 секунд
        setInterval(() => {
            this.syncData();
        }, 30000);

        // Первая синхронизация
        this.syncData();
    }

    async syncData() {
        try {
            // Обновляем статус синхронизации
            this.updateSyncStatus('syncing');

            const lastSync = localStorage.getItem('last_sync') || new Date().toISOString();

            const response = await fetch('/api/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    last_sync: lastSync
                })
            });

            const data = await response.json();

            if (data.success && data.updates) {
                // Обрабатываем обновления
                this.processUpdates(data.updates);

                // Обновляем время последней синхронизации
                localStorage.setItem('last_sync', data.server_time);

                // Обновляем статус
                this.updateSyncStatus('synced');

                console.log('Синхронизация завершена');
            }

        } catch (error) {
            console.error('Ошибка синхронизации:', error);
            this.updateSyncStatus('error');
        }
    }

    updateSyncStatus(status) {
        const syncElement = document.getElementById('syncStatus');
        if (syncElement) {
            syncElement.className = `sync-status ${status}`;
            syncElement.textContent = this.getSyncStatusText(status);
        }
    }

    getSyncStatusText(status) {
        const texts = {
            'synced': 'онлайн',
            'syncing': 'синхронизация...',
            'error': 'ошибка'
        };
        return texts[status] || 'неизвестно';
    }

    processUpdates(updates) {
        // Обработка полученных обновлений
        if (updates.transactions && updates.transactions.length > 0) {
            this.showNotification(`Получено ${updates.transactions.length} новых транзакций`, 'info');
            this.loadDashboardData();
        }

        if (updates.family_changes) {
            this.showNotification('Обновлены данные семьи', 'info');
        }
    }

    updateUI() {
        // Обновление информации о пользователе
        const userNameElement = document.getElementById('userName');
        if (userNameElement && this.userData) {
            userNameElement.textContent = this.userData.name;
        }
    }

    async loadCharts() {
        // Этот метод будет реализован в charts.js
        if (window.FinanceCharts) {
            const chartData = await this.loadChartData();
            window.FinanceCharts.initExpenseChart(chartData);
        }
    }

    async loadChartData() {
        try {
            const response = await fetch(`/api/reports/categories?user_id=${this.userId}`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка загрузки данных для графиков:', error);
            return { categories: [] };
        }
    }
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.financeApp = new FamilyFinanceApp();
});