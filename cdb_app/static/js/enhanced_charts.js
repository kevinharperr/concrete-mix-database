/**
 * Enhanced Charts for Concrete Mix Database
 * This file contains enhanced chart configurations and utility functions
 */

// Color schemes for different material classes
const MATERIAL_COLORS = {
    'CEMENT': {
        backgroundColor: 'rgba(128, 128, 128, 0.7)',
        borderColor: 'rgb(100, 100, 100)'
    },
    'SCM': {
        backgroundColor: 'rgba(0, 128, 0, 0.7)',
        borderColor: 'rgb(0, 100, 0)'
    },
    'AGG': {
        backgroundColor: 'rgba(210, 180, 140, 0.7)',
        borderColor: 'rgb(160, 120, 90)'
    },
    'ADM': {
        backgroundColor: 'rgba(255, 165, 0, 0.7)',
        borderColor: 'rgb(220, 140, 0)'
    },
    'WATER': {
        backgroundColor: 'rgba(0, 191, 255, 0.7)',
        borderColor: 'rgb(0, 120, 215)'
    },
    'OTHER': {
        backgroundColor: 'rgba(148, 0, 211, 0.7)', 
        borderColor: 'rgb(100, 0, 150)'
    }
};

// Default color palette for charts
const DEFAULT_COLORS = [
    { backgroundColor: 'rgba(75, 192, 192, 0.7)', borderColor: 'rgb(75, 192, 192)' },
    { backgroundColor: 'rgba(54, 162, 235, 0.7)', borderColor: 'rgb(54, 162, 235)' },
    { backgroundColor: 'rgba(255, 206, 86, 0.7)', borderColor: 'rgb(255, 206, 86)' },
    { backgroundColor: 'rgba(255, 99, 132, 0.7)', borderColor: 'rgb(255, 99, 132)' },
    { backgroundColor: 'rgba(153, 102, 255, 0.7)', borderColor: 'rgb(153, 102, 255)' },
    { backgroundColor: 'rgba(255, 159, 64, 0.7)', borderColor: 'rgb(255, 159, 64)' },
    { backgroundColor: 'rgba(199, 199, 199, 0.7)', borderColor: 'rgb(199, 199, 199)' }
];

/**
 * Creates an enhanced material proportions chart
 * @param {string} elementId - The ID of the canvas element
 * @param {Array} labels - Material names
 * @param {Array} data - Material dosages
 * @param {Array} materialClasses - Material class codes corresponding to each material
 */
function createEnhancedMaterialProportionsChart(elementId, labels, data, materialClasses) {
    const ctx = document.getElementById(elementId);
    
    // Prepare colors based on material classes
    const backgroundColors = [];
    const borderColors = [];
    
    materialClasses.forEach(classCode => {
        const colorScheme = MATERIAL_COLORS[classCode] || MATERIAL_COLORS.OTHER;
        backgroundColors.push(colorScheme.backgroundColor);
        borderColors.push(colorScheme.borderColor);
    });
    
    // Group materials by class for the stacked view
    const materialsByClass = {};
    const classLabels = [...new Set(materialClasses)];
    
    classLabels.forEach(classCode => {
        materialsByClass[classCode] = {
            label: getClassLabel(classCode),
            data: data.map((val, idx) => materialClasses[idx] === classCode ? val : 0),
            backgroundColor: MATERIAL_COLORS[classCode]?.backgroundColor || MATERIAL_COLORS.OTHER.backgroundColor,
            borderColor: MATERIAL_COLORS[classCode]?.borderColor || MATERIAL_COLORS.OTHER.borderColor,
            borderWidth: 1
        };
    });
    
    const datasets = Object.values(materialsByClass);
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Materials'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Dosage (kg/m³)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        footer: (tooltipItems) => {
                            // Calculate percentage of total for this material
                            const totalDosage = data.reduce((a, b) => a + b, 0);
                            const value = data[tooltipItems[0].dataIndex];
                            const percentage = (value / totalDosage * 100).toFixed(1);
                            return `${percentage}% of total mix`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Material Proportions by Category'
                }
            }
        }
    });
}

/**
 * Creates a pie chart showing material distribution
 * @param {string} elementId - The ID of the canvas element
 * @param {Array} labels - Material names
 * @param {Array} data - Material dosages
 * @param {Array} materialClasses - Material class codes
 */
function createMaterialDistributionPieChart(elementId, labels, data, materialClasses) {
    const ctx = document.getElementById(elementId);
    
    // Prepare colors based on material classes
    const backgroundColors = [];
    const borderColors = [];
    
    materialClasses.forEach(classCode => {
        const colorScheme = MATERIAL_COLORS[classCode] || MATERIAL_COLORS.OTHER;
        backgroundColors.push(colorScheme.backgroundColor);
        borderColors.push(colorScheme.borderColor);
    });
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => {
                            const value = tooltipItem.raw;
                            const total = data.reduce((a, b) => a + b, 0);
                            const percentage = (value / total * 100).toFixed(1);
                            return `${tooltipItem.label}: ${value} kg/m³ (${percentage}%)`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Material Distribution'
                }
            }
        }
    });
}

/**
 * Creates an enhanced strength development chart
 * @param {string} elementId - The ID of the canvas element
 * @param {Array} labels - Age labels (days)
 * @param {Array} data - Strength values
 * @param {Array} targetStrength - Target strength (optional)
 */
function createEnhancedStrengthChart(elementId, labels, data, targetStrength = null) {
    const ctx = document.getElementById(elementId);
    
    // Create data points for a basic strength prediction model (if we have enough data)
    let predictedData = [];
    let predictedLabels = [];
    
    // Only try to predict if we have at least 2 data points
    if (labels.length >= 2) {
        // Sort the data pairs by age
        const dataPairs = labels.map((label, index) => ({ age: label, value: data[index] }));
        dataPairs.sort((a, b) => a.age - b.age);
        
        // Extract sorted data
        const sortedLabels = dataPairs.map(pair => pair.age);
        const sortedData = dataPairs.map(pair => pair.value);
        
        // Simple logarithmic model for concrete strength development
        // S(t) = S28 * (log(t) / log(28))
        if (sortedLabels.includes(28)) {
            // If we have 28-day strength, use it as basis
            const idx28 = sortedLabels.findIndex(age => age === 28);
            const s28 = sortedData[idx28];
            
            // Generate prediction points
            const predictionDays = [1, 3, 7, 14, 28, 56, 90, 180, 365];
            predictionDays.forEach(day => {
                if (!sortedLabels.includes(day)) {
                    predictedLabels.push(day);
                    const predictedStrength = s28 * (Math.log(day) / Math.log(28));
                    predictedData.push(predictedStrength);
                }
            });
        }
    }
    
    const datasets = [{
        label: 'Actual Strength',
        data: data,
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.1,
        fill: false
    }];
    
    if (predictedData.length > 0) {
        datasets.push({
            label: 'Predicted Strength',
            data: predictedData,
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderDash: [5, 5],
            tension: 0.1,
            fill: false,
            pointStyle: 'circle'
        });
    }
    
    // Add target strength line if provided
    if (targetStrength) {
        // Get the max age from actual and predicted data
        const allLabels = [...labels, ...predictedLabels];
        const maxAge = Math.max(...allLabels);
        
        datasets.push({
            label: 'Target Strength',
            data: [{x: 0, y: targetStrength}, {x: maxAge, y: targetStrength}],
            borderColor: 'rgba(255, 159, 64, 1)',
            borderWidth: 2,
            borderDash: [10, 5],
            fill: false,
            pointRadius: 0
        });
    }
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [...labels, ...predictedLabels],
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'logarithmic',
                    title: {
                        display: true,
                        text: 'Age (days)'
                    },
                    ticks: {
                        callback: function(value) {
                            if ([1, 3, 7, 28, 56, 90, 180, 365].includes(value)) {
                                return value;
                            }
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Compressive Strength (MPa)'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label + ' days';
                        }
                    }
                },
                legend: {
                    display: true
                },
                title: {
                    display: true,
                    text: 'Strength Development Over Time'
                }
            }
        }
    });
}

/**
 * Creates a radar chart showing various performance metrics
 * @param {string} elementId - The ID of the canvas element
 * @param {Object} performanceData - Object with categories and values
 */
function createPerformanceRadarChart(elementId, performanceData) {
    const ctx = document.getElementById(elementId);
    
    const labels = Object.keys(performanceData);
    const values = Object.values(performanceData);
    
    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Performance Metrics',
                data: values,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgb(54, 162, 235)',
                pointBackgroundColor: 'rgb(54, 162, 235)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                line: {
                    borderWidth: 3
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Performance Profile'
                }
            }
        }
    });
}

/**
 * Creates a sustainability dashboard with multiple charts
 * @param {string} elementId - The ID of the container element
 * @param {Object} sustainabilityData - Object with sustainability metrics
 */
function createSustainabilityDashboard(containerId, sustainabilityData) {
    const container = document.getElementById(containerId);
    
    // Clear any existing content
    container.innerHTML = '';
    
    // Create canvases for each chart
    const gwpCanvas = document.createElement('canvas');
    gwpCanvas.id = 'gwpChart';
    
    const energyCanvas = document.createElement('canvas');
    energyCanvas.id = 'energyChart';
    
    const waterCanvas = document.createElement('canvas');
    waterCanvas.id = 'waterChart';
    
    // Create a row for charts
    const row = document.createElement('div');
    row.className = 'row mt-3';
    
    // Create columns for each chart
    const gwpCol = document.createElement('div');
    gwpCol.className = 'col-md-4';
    gwpCol.appendChild(createCardWithCanvas('Carbon Footprint', gwpCanvas));
    
    const energyCol = document.createElement('div');
    energyCol.className = 'col-md-4';
    energyCol.appendChild(createCardWithCanvas('Energy Consumption', energyCanvas));
    
    const waterCol = document.createElement('div');
    waterCol.className = 'col-md-4';
    waterCol.appendChild(createCardWithCanvas('Water Usage', waterCanvas));
    
    // Assemble the layout
    row.appendChild(gwpCol);
    row.appendChild(energyCol);
    row.appendChild(waterCol);
    container.appendChild(row);
    
    // Create the charts
    createGaugeChart('gwpChart', 'Carbon Footprint', sustainabilityData.gwp || 0, 400, 'kg CO₂e/m³');
    createGaugeChart('energyChart', 'Energy', sustainabilityData.energy || 0, 3000, 'MJ/m³');
    createGaugeChart('waterChart', 'Water Usage', sustainabilityData.water || 0, 2000, 'L/m³');
}

/**
 * Helper function to create a card with a canvas inside
 */
function createCardWithCanvas(title, canvas) {
    const card = document.createElement('div');
    card.className = 'card';
    
    const cardBody = document.createElement('div');
    cardBody.className = 'card-body text-center';
    cardBody.style.height = '250px'; // Set fixed height to control chart size
    
    const cardTitle = document.createElement('h5');
    cardTitle.className = 'card-title';
    cardTitle.textContent = title;
    
    cardBody.appendChild(cardTitle);
    cardBody.appendChild(canvas);
    card.appendChild(cardBody);
    
    return card;
}

/**
 * Creates a gauge chart for sustainability metrics
 */
function createGaugeChart(elementId, label, value, maxValue, units) {
    const ctx = document.getElementById(elementId);
    
    // Calculate percentage for gradient color
    const percentage = (value / maxValue) * 100;
    
    // Determine color based on percentage (green to red gradient)
    let color;
    if (percentage < 33) {
        color = 'rgba(75, 192, 192, 1)'; // Green for good
    } else if (percentage < 66) {
        color = 'rgba(255, 206, 86, 1)'; // Yellow for medium
    } else {
        color = 'rgba(255, 99, 132, 1)'; // Red for high
    }
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [value, maxValue - value],
                backgroundColor: [
                    color,
                    'rgba(220, 220, 220, 0.5)'
                ],
                circumference: 180,
                rotation: 270
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function() {
                            return `${value} ${units}`;
                        }
                    }
                }
            },
            cutout: '70%',
            elements: {
                center: {
                    text: value + ' ' + units,
                    color: '#666',
                    fontStyle: 'Arial', 
                    sidePadding: 20 
                }
            }
        },
        plugins: [{
            id: 'gaugeText',
            afterDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                
                ctx.restore();
                ctx.font = '16px Arial';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#666';
                
                const text = value + ' ' + units;
                const textX = Math.round((width - ctx.measureText(text).width) / 2);
                const textY = height - 20;
                
                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });
}

/**
 * Helper function to get a human-readable label for material classes
 */
function getClassLabel(classCode) {
    const labels = {
        'CEMENT': 'Cement',
        'SCM': 'Supplementary Materials',
        'AGG': 'Aggregates',
        'ADM': 'Admixtures',
        'WATER': 'Water',
        'OTHER': 'Other Materials'
    };
    
    return labels[classCode] || classCode;
}
