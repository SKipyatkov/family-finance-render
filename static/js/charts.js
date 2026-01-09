// Модуль для работы с графиками
class FinanceCharts {
    static initExpenseChart(data) {
        const ctx = document.getElementById('expenseChart');
        if (!ctx) return;

        // Уничтожаем старый график если есть
        if (this.expenseChart) {
            this.expenseChart.destroy();
        }

        const categories = data.categories || [];
        const labels = categories.map(c => c.category);
        const amounts = categories.map(c => c.total);

        // Создаем градиент
        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(67, 97, 238, 0.7)');
        gradient.addColorStop(1, 'rgba(67, 97, 238, 0.1)');

        this.expenseChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: amounts,
                    backgroundColor: [
                        '#4cc9f0', '#7209b7', '#f8961e',
                        '#f72585', '#38b000', '#4361ee',
                        '#9c27b0', '#ff9800'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: {
                                family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value.toLocaleString('ru-RU')} ₽ (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%',
                animation: {
                    animateScale: true,
                    animateRotate: true,
                    duration: 2000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }

    static initBalanceChart(incomeData, expenseData) {
        const ctx = document.getElementById('balanceChart');
        if (!ctx) return;

        const labels = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];

        this.balanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Доходы',
                        data: incomeData,
                        borderColor: '#4cc9f0',
                        backgroundColor: 'rgba(76, 201, 240, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Расходы',
                        data: expenseData,
                        borderColor: '#f72585',
                        backgroundColor: 'rgba(247, 37, 133, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString('ru-RU') + ' ₽';
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    static initCategoryBarChart(categoryData) {
        const ctx = document.getElementById('categoryBarChart');
        if (!ctx) return;

        const labels = categoryData.map(item => item.category);
        const data = categoryData.map(item => item.total);
        const colors = this.generateColors(labels.length);

        this.categoryBarChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Расходы по категориям',
                    data: data,
                    backgroundColor: colors,
                    borderColor: colors.map(c => this.darkenColor(c, 20)),
                    borderWidth: 1,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString('ru-RU') + ' ₽';
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }

    static generateColors(count) {
        const baseColors = [
            '#4cc9f0', '#7209b7', '#f8961e', '#f72585',
            '#38b000', '#4361ee', '#9c27b0', '#ff9800',
            '#00bcd4', '#8bc34a', '#ff5722', '#673ab7'
        ];

        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        return colors;
    }

    static darkenColor(color, percent) {
        let r = parseInt(color.substring(1, 3), 16);
        let g = parseInt(color.substring(3, 5), 16);
        let b = parseInt(color.substring(5, 7), 16);

        r = Math.floor(r * (100 - percent) / 100);
        g = Math.floor(g * (100 - percent) / 100);
        b = Math.floor(b * (100 - percent) / 100);

        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }

    static updateChart(data, chartType = 'expense') {
        switch(chartType) {
            case 'expense':
                this.initExpenseChart(data);
                break;
            case 'balance':
                this.initBalanceChart(data.income, data.expense);
                break;
            case 'categoryBar':
                this.initCategoryBarChart(data);
                break;
        }
    }
}

// Экспортируем в глобальную область видимости
window.FinanceCharts = FinanceCharts;