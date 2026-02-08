document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('healthChart');
    let healthChart;

    if (ctx) {
        healthChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Heart Rate',
                        data: [],
                        borderColor: '#ef4444',
                        tension: 0.4
                    },
                    {
                        label: 'Blood Sugar',
                        data: [],
                        borderColor: '#10b981',
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: false, grid: { color: 'rgba(255,255,255,0.1)' } },
                    x: { grid: { display: false } }
                },
                plugins: { legend: { display: false } }
            }
        });

        // Load History
        if (window.history_api_url && window.current_user_id) {
            fetch(`${window.history_api_url}?user_id=${window.current_user_id}`)
                .then(r => r.json())
                .then(data => {
                    data.forEach(point => {
                        const time = new Date(point.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                        healthChart.data.labels.push(time);
                        healthChart.data.datasets[0].data.push(point.heart_rate);
                        healthChart.data.datasets[1].data.push(point.sugar_level);
                    });
                    healthChart.update();

                    if (data.length > 0) {
                        const latest = data[data.length - 1];
                        updateUI(latest);
                    }
                });
        }
    }

    // SSE Connection
    if (window.stream_api_url && window.current_user_id) {
        const url = `${window.stream_api_url}?user_id=${window.current_user_id}`;
        const eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateUI(data);

            if (healthChart) {
                const time = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                healthChart.data.labels.push(time);
                healthChart.data.datasets[0].data.push(data.heart_rate);
                healthChart.data.datasets[1].data.push(data.sugar_level);

                if (healthChart.data.labels.length > 20) {
                    healthChart.data.labels.shift();
                    healthChart.data.datasets[0].data.shift();
                    healthChart.data.datasets[1].data.shift();
                }
                healthChart.update();
            }

            // Simple Emergency Check
            if (data.heart_rate > 150 || data.heart_rate < 40) {
                document.getElementById('emergency-overlay') ? document.getElementById('emergency-overlay').style.display = 'block' : null;
            } else {
                document.getElementById('emergency-overlay') ? document.getElementById('emergency-overlay').style.display = 'none' : null;
            }
        };

        eventSource.onerror = () => {
            console.error("SSE Connection Failed");
            eventSource.close();
        };
    }

    function updateUI(data) {
        if (document.getElementById('hr-val')) document.getElementById('hr-val').textContent = data.heart_rate;
        if (document.getElementById('bp-val')) document.getElementById('bp-val').textContent = `${data.blood_pressure_sys}/${data.blood_pressure_dia}`;
        if (document.getElementById('spo2-val')) document.getElementById('spo2-val').textContent = data.oxygen_level;
        if (document.getElementById('temp-val')) document.getElementById('temp-val').textContent = data.temperature;
        if (document.getElementById('sugar-val')) document.getElementById('sugar-val').textContent = data.sugar_level;
    }
});
