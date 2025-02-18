document.addEventListener('DOMContentLoaded', function() {
    // Configuration
    const config = {
        width: 450,
        height: 400,
        margin: { top: 30, right: 30, bottom: 50, left: 50 },
        transition: 750,
        colors: {
            all: ['#1cc88a', '#f6c23e'],     // Green, Yellow for all modules
            my: ['#4e73df', '#e74a3b'],      // Blue, Red for my modules
        }
    };

    async function loadDashboardData() {
        try {
            const currentYear = document.getElementById('academicYear').value;
            const response = await fetch(`/module-lead/api/modules?count_only=true&academic_year=${currentYear}`);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            
            if (data.success && data.data) {
                const allCounts = data.data.counts || {};
                const userCounts = data.data.user_counts || {};
                updateDashboard(allCounts, userCounts);
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }

    function updateDashboard(allStats, userStats) {
        console.log('All stats:', allStats);    // Debug print
        console.log('User stats:', userStats);  // Debug print
        
        // Update statistics cards
        document.getElementById('totalModules').textContent = allStats.total || 0;
        document.getElementById('yourModules').textContent = userStats.total || 0;
        document.getElementById('completedReviews').textContent = allStats.completed || 0;
        document.getElementById('pendingReviews').textContent = allStats.pending || 0;

        // Clear and recreate charts
        document.getElementById('modulesPieChart').innerHTML = '';
        document.getElementById('myModulesPieChart').innerHTML = '';
        
        // Create both charts
        createDonutChart('modulesPieChart', allStats, 'All Modules');
        createDonutChart('myModulesPieChart', userStats, 'My Modules');
    }

    function createDonutChart(containerId, stats, title) {
        const isMyModules = containerId === 'myModulesPieChart';
        const radius = Math.min(config.width, config.height) / 2.5;
        const colors = isMyModules ? config.colors.my : config.colors.all;
        
        const chartData = [
            { 
                label: 'Completed Reviews', 
                value: stats.completed || 0, 
                color: colors[0]
            },
            { 
                label: 'Pending Reviews', 
                value: stats.pending || 0, 
                color: colors[1]
            }
        ];

        const svg = d3.select("#" + containerId)
            .append("svg")
            .attr("viewBox", `0 0 ${config.width} ${config.height}`)
            .append("g")
            .attr("transform", `translate(${config.width / 2},${config.height / 2})`);

        // Create arc generators with different inner radius for My Modules
        const arc = d3.arc()
            .innerRadius(radius * (isMyModules ? 0.7 : 0.6))  // Larger inner radius for My Modules
            .outerRadius(radius);

        const labelArc = d3.arc()
            .innerRadius(radius * (isMyModules ? 0.85 : 0.8))
            .outerRadius(radius * (isMyModules ? 0.85 : 0.8));

        const pie = d3.pie()
            .value(d => d.value)
            .sort(null)
            .padAngle(isMyModules ? 0.04 : 0.03);  // Larger padding for My Modules

        // Add slices with animations and hover effects
        const arcs = svg.selectAll("arc")
            .data(pie(chartData))
            .enter()
            .append("g")
            .attr("class", "arc");

        // Add paths with different styling for My Modules
        arcs.append("path")
            .attr("d", arc)
            .attr("fill", d => d.data.color)
            .attr("stroke", "white")
            .style("stroke-width", isMyModules ? "3px" : "2px")  // Thicker border for My Modules
            .style("cursor", "pointer")
            .on("mouseover", function(event, d) {
                const scale = isMyModules ? 1.08 : 1.05;
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("transform", `scale(${scale})`);
                
                // Show tooltip for My Modules
                if (isMyModules) {
                    const percent = total > 0 ? Math.round((d.data.value / total) * 100) : 0;
                    tooltip.style("opacity", 1)
                        .html(`${d.data.label}<br>${d.data.value} (${percent}%)`)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 10) + "px");
                }
            })
            .on("mouseout", function() {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("transform", "scale(1)");
                
                if (isMyModules) {
                    tooltip.style("opacity", 0);
                }
            });

        // Add labels directly on segments
        arcs.append("text")
            .attr("transform", d => `translate(${labelArc.centroid(d)})`)
            .attr("dy", "0.35em")
            .attr("text-anchor", "middle")
            .attr("fill", "#ffffff")
            .attr("font-size", "12px")
            .attr("font-weight", "500")
            .text(d => d.data.value);

        // Add center text with different styling for My Modules
        const total = stats.completed + stats.pending;
        const completionRate = total > 0 ? Math.round((stats.completed / total) * 100) : 0;
        
        svg.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "-0.2em")
            .attr("class", isMyModules ? "donut-center-text-my" : "donut-center-text")
            .text(`${completionRate}%`);
            
        svg.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "1.2em")
            .attr("class", isMyModules ? "donut-center-subtext-my" : "donut-center-subtext")
            .text("Completed");

        // Add compact legend
        const legend = svg.append("g")
            .attr("transform", `translate(${-radius * 1.4}, ${-radius * 1.2})`);

        chartData.forEach((d, i) => {
            const legendRow = legend.append("g")
                .attr("transform", `translate(0, ${i * 16})`);

            legendRow.append("rect")
                .attr("width", 10)
                .attr("height", 10)
                .attr("fill", d.color);

            legendRow.append("text")
                .attr("x", 15)
                .attr("y", 8)
                .attr("font-size", "10px")
                .attr("fill", "#2d2d2d")
                .attr("font-weight", "500")
                .text(`${d.label} (${d.value})`);
        });

        // Add tooltip container for My Modules
        if (isMyModules) {
            const tooltip = d3.select("body").append("div")
                .attr("class", "chart-tooltip")
                .style("opacity", 0);
        }

        // Update CSS styles
        if (!document.getElementById('chartStyles')) {
            const style = document.createElement('style');
            style.id = 'chartStyles';
            style.textContent = `
                .chart-tooltip {
                    position: absolute;
                    padding: 8px;
                    background: rgba(0, 0, 0, 0.8);
                    color: white;
                    border-radius: 4px;
                    font-size: 12px;
                    pointer-events: none;
                    z-index: 100;
                }
                .donut-center-text {
                    font-size: 16px;
                    font-weight: bold;
                    fill: #4e73df;
                }
                .donut-center-subtext {
                    font-size: 12px;
                    fill: #858796;
                }
                .donut-center-text-my {
                    font-size: 18px;
                    font-weight: bold;
                    fill: #4e73df;
                }
                .donut-center-subtext-my {
                    font-size: 13px;
                    fill: #5a5c69;
                    font-weight: 500;
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Initial load
    loadDashboardData();

    // Refresh handler
    document.getElementById('refreshDashboard').addEventListener('click', loadDashboardData);

    // Update dashboard data when academic year changes
    document.getElementById('academicYear').addEventListener('change', function() {
        loadDashboardData();
    });

    // Refresh dashboard data
    document.getElementById('refreshDashboard').addEventListener('click', function() {
        loadDashboardData();
    });

    // Initial load
    loadDashboardData();
});
