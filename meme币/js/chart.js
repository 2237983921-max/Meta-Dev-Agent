class SparklineChart {
  static hexToRgba(color, alpha) {
    if (!color || typeof color !== "string") {
      return `rgba(76, 226, 255, ${alpha})`;
    }

    if (color.startsWith("rgba")) {
      return color.replace(/rgba\(([^)]+),[^)]+\)/, `rgba($1, ${alpha})`);
    }

    if (color.startsWith("rgb(")) {
      const values = color.slice(4, -1);
      return `rgba(${values}, ${alpha})`;
    }

    const normalized = color.replace("#", "");
    const full = normalized.length === 3
      ? normalized.split("").map((char) => char + char).join("")
      : normalized;

    const int = parseInt(full, 16);
    const red = (int >> 16) & 255;
    const green = (int >> 8) & 255;
    const blue = int & 255;

    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
  }

  static resizeCanvas(canvas, width, height) {
    const context = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.scale(dpr, dpr);

    return context;
  }

  static buildPoints(data, width, height, padding = 4) {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const step = width / Math.max(1, data.length - 1);

    return data.map((value, index) => ({
      x: index * step,
      y: padding + (1 - (value - min) / range) * (height - padding * 2)
    }));
  }

  static draw(canvas, data, color = "#4ce2ff", fillAlpha = 0.12) {
    if (!canvas || !data || !data.length) {
      return;
    }

    const width = Number(canvas.getAttribute("width")) || 80;
    const height = Number(canvas.getAttribute("height")) || 30;
    const context = SparklineChart.resizeCanvas(canvas, width, height);
    const points = SparklineChart.buildPoints(data, width, height);

    context.clearRect(0, 0, width, height);

    context.beginPath();
    context.moveTo(points[0].x, height);
    points.forEach((point) => context.lineTo(point.x, point.y));
    context.lineTo(points[points.length - 1].x, height);
    context.closePath();
    context.fillStyle = SparklineChart.hexToRgba(color, fillAlpha);
    context.fill();

    context.beginPath();
    context.moveTo(points[0].x, points[0].y);
    for (let index = 1; index < points.length; index += 1) {
      const current = points[index];
      const previous = points[index - 1];
      const controlX = (current.x + previous.x) / 2;
      const controlY = (current.y + previous.y) / 2;
      context.quadraticCurveTo(previous.x, previous.y, controlX, controlY);
    }
    context.lineTo(points[points.length - 1].x, points[points.length - 1].y);
    context.strokeStyle = color;
    context.lineWidth = 2;
    context.stroke();

    const lastPoint = points[points.length - 1];
    context.beginPath();
    context.arc(lastPoint.x, lastPoint.y, 2.8, 0, Math.PI * 2);
    context.fillStyle = color;
    context.fill();
  }

  static drawModalChart(canvas, data, color = "#4ce2ff") {
    if (!canvas || !data || !data.length) {
      return;
    }

    const parentWidth = Math.max(canvas.parentElement?.clientWidth || 500, 260);
    const width = Math.min(parentWidth, 520);
    const height = 150;
    const padding = 28;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const context = SparklineChart.resizeCanvas(canvas, width, height);
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const step = chartWidth / Math.max(1, data.length - 1);
    const points = data.map((value, index) => ({
      x: padding + index * step,
      y: padding + (1 - (value - min) / range) * chartHeight
    }));

    context.clearRect(0, 0, width, height);
    context.strokeStyle = "rgba(255,255,255,0.06)";
    context.lineWidth = 1;

    for (let index = 0; index < 5; index += 1) {
      const y = padding + (chartHeight / 4) * index;
      context.beginPath();
      context.moveTo(padding, y);
      context.lineTo(width - padding, y);
      context.stroke();
    }

    const gradient = context.createLinearGradient(0, padding, 0, height - padding);
    gradient.addColorStop(0, SparklineChart.hexToRgba(color, 0.22));
    gradient.addColorStop(1, SparklineChart.hexToRgba(color, 0.02));

    context.beginPath();
    context.moveTo(points[0].x, height - padding);
    points.forEach((point) => context.lineTo(point.x, point.y));
    context.lineTo(points[points.length - 1].x, height - padding);
    context.closePath();
    context.fillStyle = gradient;
    context.fill();

    context.beginPath();
    context.moveTo(points[0].x, points[0].y);
    for (let index = 1; index < points.length; index += 1) {
      const current = points[index];
      const previous = points[index - 1];
      const controlX = (current.x + previous.x) / 2;
      const controlY = (current.y + previous.y) / 2;
      context.quadraticCurveTo(previous.x, previous.y, controlX, controlY);
    }
    context.lineTo(points[points.length - 1].x, points[points.length - 1].y);
    context.strokeStyle = color;
    context.lineWidth = 2.6;
    context.stroke();

    const lastPoint = points[points.length - 1];
    context.beginPath();
    context.arc(lastPoint.x, lastPoint.y, 4, 0, Math.PI * 2);
    context.fillStyle = color;
    context.fill();
    context.beginPath();
    context.arc(lastPoint.x, lastPoint.y, 8, 0, Math.PI * 2);
    context.strokeStyle = SparklineChart.hexToRgba(color, 0.3);
    context.lineWidth = 2;
    context.stroke();
  }
}
