document.addEventListener('DOMContentLoaded', function() {
    const stats = JSON.parse(document.getElementById('dashboardStats').textContent);
    
    // Chart configuration
    const config = {
        width: 450,
        height: 400,
        margin: { top: 30, right: 30, bottom: 50, left: 50 },
        transition: 750,
        colors: {
            pie: ['#4e73df', '#f6c23e', '#1cc88a'],
            bar: ['#4e73df', '#1cc88a', '#36b9cc']
        }
    };

    // Enhanced Donut Chart
    function createDonutChart() {
        const radius = Math.min(config.width, config.height) / 2.5;
        const moduleData = [
            { label: 'Completed Reviews', value: stats.completed_reviews, color: '#1cc88a' },  // Green
            { label: 'Pending Reviews', value: stats.pending_reviews, color: '#f6c23e' },      // Yellow
            { label: 'Total Modules', value: stats.total_modules, color: '#4e73df' }           // Blue
        ];

        const svg = d3.select("#modulesPieChart")
            .append("svg")
            .attr("viewBox", `0 0 ${config.width} ${config.height}`)
            .append("g")
            .attr("transform", `translate(${config.width / 2},${config.height / 2})`);

        // Create arc generators
        const arc = d3.arc()
            .innerRadius(radius * 0.6)
            .outerRadius(radius);

        const labelArc = d3.arc()
            .innerRadius(radius * 0.8)  // Position labels closer to segments
            .outerRadius(radius * 0.8);

        const pie = d3.pie()
            .value(d => d.value)
            .sort(null)
            .padAngle(0.03);

        // Add slices
        const arcs = svg.selectAll("arc")
            .data(pie(moduleData))
            .enter()
            .append("g")
            .attr("class", "arc");

        // Add paths with solid colors
        arcs.append("path")
            .attr("d", arc)
            .attr("fill", d => d.data.color)
            .attr("stroke", "white")
            .style("stroke-width", "2px")
            .style("cursor", "pointer")
            .on("mouseover", function() {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("transform", "scale(1.05)");
            })
            .on("mouseout", function() {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("transform", "scale(1)");
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

        // Add center text
        const total = stats.completed_reviews + stats.pending_reviews;
        const completionRate = total > 0 ? Math.round((stats.completed_reviews / total) * 100) : 0;
        
        svg.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "-0.2em")
            .attr("class", "donut-center-text")
            .text(`${completionRate}%`);
            
        svg.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "1.2em")
            .attr("class", "donut-center-subtext")
            .text("Completed");

        // Add legend with reduced size and extreme top left position
        const legend = svg.append("g")
            .attr("transform", `translate(${-radius * 1.4}, ${-radius * 1.2})`); // Moved further left and up

        moduleData.forEach((d, i) => {
            const legendRow = legend.append("g")
                .attr("transform", `translate(0, ${i * 16})`); // Reduced vertical spacing

            legendRow.append("rect")
                .attr("width", 10)        // Smaller squares
                .attr("height", 10)
                .attr("fill", d.color);

            legendRow.append("text")
                .attr("x", 15)            // Reduced spacing after square
                .attr("y", 8)             // Adjusted vertical alignment
                .attr("font-size", "10px") // Smaller font
                .attr("fill", "#2d2d2d")
                .attr("font-weight", "500")
                .text(`${d.label} (${d.value})`);
        });
    }

    // Enhanced Bar Chart
    function createBarChart() {
        const userData = [
            { role: 'Total Users', count: stats.total_users },
            { role: 'Admins', count: stats.admin_users },
            { role: 'Module Leads', count: stats.module_leads }
        ];

        const svg = d3.select("#usersBarChart")
            .append("svg")
            .attr("viewBox", `0 0 ${config.width} ${config.height}`)
            .append("g")
            .attr("transform", `translate(${config.margin.left},${config.margin.top})`);

        const width = config.width - config.margin.left - config.margin.right;
        const height = config.height - config.margin.top - config.margin.bottom;

        // Scales
        const x = d3.scaleBand()
            .range([0, width])
            .padding(0.3);

        const y = d3.scaleLinear()
            .range([height, 0]);

        x.domain(userData.map(d => d.role));
        y.domain([0, d3.max(userData, d => d.count) * 1.2]);

        // Add gradients
        userData.forEach((d, i) => {
            const gradient = svg.append("defs")
                .append("linearGradient")
                .attr("id", `bar-gradient-${i}`)
                .attr("gradientUnits", "userSpaceOnUse")
                .attr("x1", "0%")
                .attr("y1", "100%")
                .attr("x2", "0%")
                .attr("y2", "0%");

            gradient.append("stop")
                .attr("offset", "0%")
                .attr("stop-color", config.colors.bar[i]);

            gradient.append("stop")
                .attr("offset", "100%")
                .attr("stop-color", d3.rgb(config.colors.bar[i]).brighter(0.5));
        });

        // Add bars with animations
        svg.selectAll(".bar")
            .data(userData)
            .enter().append("rect")
            .attr("class", "bar")
            .attr("x", d => x(d.role))
            .attr("width", x.bandwidth())
            .attr("y", height)
            .attr("height", 0)
            .attr("fill", (d, i) => `url(#bar-gradient-${i})`)
            .attr("rx", 6)
            .attr("ry", 6)
            .transition()
            .duration(config.transition)
            .attr("y", d => y(d.count))
            .attr("height", d => height - y(d.count));

        // Axes
        svg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x))
            .selectAll("text")
            .attr("class", "axis-label");

        svg.append("g")
            .call(d3.axisLeft(y))
            .selectAll("text")
            .attr("class", "axis-label");

        // Add value labels with animations
        svg.selectAll(".label")
            .data(userData)
            .enter()
            .append("text")
            .attr("class", "value-label")
            .attr("x", d => x(d.role) + x.bandwidth() / 2)
            .attr("y", d => y(d.count) - 5)
            .attr("opacity", 0)
            .transition()
            .duration(config.transition)
            .attr("opacity", 1)
            .text(d => d.count);
    }

    // Add CSS
    const style = document.createElement('style');
    style.textContent = `
        .chart-tooltip {
            position: absolute;
            padding: 8px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
        }
        .axis-label {
            font-size: 12px;
            font-weight: 500;
        }
        .value-label {
            font-size: 12px;
            font-weight: bold;
            text-anchor: middle;
        }
        .donut-center-text {
            font-size: 16px;
            font-weight: bold;
            fill: #4e73df;
        }
    `;
    document.head.appendChild(style);

    // Create charts
    createDonutChart();
    createBarChart();

    // Add refresh handler
    document.getElementById('refreshDashboard').addEventListener('click', function() {
        location.reload();
    });
});
