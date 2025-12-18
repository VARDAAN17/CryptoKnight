/* global bootstrap */
(function () {
  const state = {
    marketData: null,
    history: [],
    interval: 5,
    currentCandles: null,
  };

  const chartElement = document.getElementById('marketChart');
  const tickerElement = document.getElementById('market-ticker');
  const coinSelect = document.getElementById('chart-coin-select');
  const intervalSelect = document.getElementById('chart-interval-select');
  const chartMeta = document.getElementById('chart-meta');
  const timeframeSelect = document.getElementById('prediction-timeframe');
  const timeframeDisplay = document.getElementById('prediction-timeframe-display');
  const tableBody = document.getElementById('chart-data-table-body');
  const fullTableBody = document.getElementById('chart-data-full-table-body');
  const analyticsOpen = document.getElementById('metric-open');
  const analyticsHigh = document.getElementById('metric-high');
  const analyticsLow = document.getElementById('metric-low');
  const analyticsClose = document.getElementById('metric-close');

  if (intervalSelect) {
    const initialInterval = Number(intervalSelect.value);
    if (Number.isFinite(initialInterval) && initialInterval > 0) {
      state.interval = initialInterval;
    }
  }

  if (timeframeDisplay && timeframeSelect) {
    const initial = timeframeSelect.value || '15m';
    timeframeDisplay.textContent = initial.toUpperCase();
  }

  function formatCurrency(value) {
    if (value === undefined || value === null) return '--';
    if (value > 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(2)}B`;
    }
    if (value > 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    }
    return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  }

  function formatPrice(value) {
    if (value === undefined || value === null) return '--';
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '--';
    const fractionDigits = numeric >= 100 ? 2 : numeric >= 1 ? 2 : 4;
    return `$${numeric.toLocaleString(undefined, {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    })}`;
  }

  function formatTimestamp(timestamp) {
    if (timestamp instanceof Date) {
      return timestamp.toLocaleString();
    }
    const parsed = Date.parse(timestamp);
    if (!Number.isNaN(parsed)) {
      return new Date(parsed).toLocaleString();
    }
    return String(timestamp);
  }

  function timestampValue(timestamp) {
    if (timestamp instanceof Date) {
      return timestamp.getTime();
    }
    const parsed = Date.parse(timestamp);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
    return 0;
  }

  function updateAnalyticsSummary(dataset) {
    const targets = [analyticsOpen, analyticsHigh, analyticsLow, analyticsClose];
    if (!dataset || !dataset.open?.length) {
      targets.forEach((node) => {
        if (node) node.textContent = '--';
      });
      return;
    }

    const lastIndex = dataset.open.length - 1;
    const latest = {
      open: dataset.open[lastIndex],
      high: dataset.high[lastIndex],
      low: dataset.low[lastIndex],
      close: dataset.close[lastIndex],
    };

    if (analyticsOpen) analyticsOpen.textContent = formatPrice(latest.open);
    if (analyticsHigh) analyticsHigh.textContent = formatPrice(latest.high);
    if (analyticsLow) analyticsLow.textContent = formatPrice(latest.low);
    if (analyticsClose) analyticsClose.textContent = formatPrice(latest.close);
  }

  function buildTableRows(dataset) {
    if (!dataset || !dataset.timestamps?.length) return [];

    return dataset.timestamps.map((timestamp, index) => ({
      timestamp,
      open: dataset.open[index],
      high: dataset.high[index],
      low: dataset.low[index],
      close: dataset.close[index],
    }));
  }

  function createTableRow(entry) {
    const row = document.createElement('tr');
    const isUp = Number(entry.close) >= Number(entry.open);
    row.classList.add(isUp ? 'table-row-up' : 'table-row-down');

    const values = [
      formatTimestamp(entry.timestamp),
      formatPrice(entry.open),
      formatPrice(entry.high),
      formatPrice(entry.low),
      formatPrice(entry.close),
    ];

    values.forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.appendChild(cell);
    });

    return row;
  }

  function renderDataTable(dataset) {
    if (!tableBody) return;

    tableBody.innerHTML = '';
    if (fullTableBody) fullTableBody.innerHTML = '';

    if (!dataset || !dataset.timestamps?.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 5;
      cell.className = 'text-center text-secondary';
      cell.textContent = 'No market data available for the selected range yet.';
      row.appendChild(cell);
      tableBody.appendChild(row);
      if (fullTableBody) {
        fullTableBody.appendChild(row.cloneNode(true));
      }
      return;
    }

    const entries = buildTableRows(dataset).sort((a, b) => timestampValue(b.timestamp) - timestampValue(a.timestamp));

    const limited = entries.slice(0, 10);
    const fragment = document.createDocumentFragment();
    limited.forEach((entry) => {
      fragment.appendChild(createTableRow(entry));
    });
    tableBody.appendChild(fragment);

    if (fullTableBody) {
      const fullFragment = document.createDocumentFragment();
      entries.forEach((entry) => {
        fullFragment.appendChild(createTableRow(entry));
      });
      fullTableBody.appendChild(fullFragment);
    }
  }

  function renderTicker(tickers) {
    if (!tickerElement) return;
    tickerElement.innerHTML = '';
    tickers.forEach((item) => {
      const li = document.createElement('li');
      li.innerHTML = `
        <strong>${item.symbol}</strong>
        <span class="price">${formatCurrency(item.current_price)}</span>
        <span class="${item.trend === 'up' ? 'trend-up' : 'trend-down'}">
          ${item.price_change_percentage_24h?.toFixed(2)}%
        </span>
      `;
      tickerElement.appendChild(li);
    });
  }

  function buildCandlestickDataset(prices, intervalMinutes, lastUpdated) {
    if (!Array.isArray(prices) || prices.length === 0) return null;

    const baseIntervalMinutes = 5;
    const baseIntervalMs = baseIntervalMinutes * 60 * 1000;
    const groupSize = Math.max(1, Math.round(intervalMinutes / baseIntervalMinutes));
    const maxPoints = 288;
    const lastIndex = prices.length - 1;
    const startIndex = Math.max(0, prices.length - maxPoints);
    let baseTime = Date.parse(lastUpdated);
    if (Number.isNaN(baseTime)) {
      baseTime = Date.now();
    }

    const timestamps = [];
    const open = [];
    const high = [];
    const low = [];
    const close = [];

    for (let start = startIndex; start <= lastIndex; start += groupSize) {
      const end = Math.min(start + groupSize, lastIndex + 1);
      const slice = prices.slice(start, end);
      const sanitized = slice
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value));

      if (!sanitized.length) continue;

      const candleOpen = sanitized[0];
      const candleClose = sanitized[sanitized.length - 1];
      let candleHigh = sanitized[0];
      let candleLow = sanitized[0];

      for (let i = 1; i < sanitized.length; i += 1) {
        const point = sanitized[i];
        if (point > candleHigh) candleHigh = point;
        if (point < candleLow) candleLow = point;
      }

      const endIndex = end - 1;
      const timestamp = baseTime - (lastIndex - endIndex) * baseIntervalMs;

      timestamps.push(new Date(timestamp));
      open.push(Number(candleOpen.toFixed(6)));
      high.push(Number(candleHigh.toFixed(6)));
      low.push(Number(candleLow.toFixed(6)));
      close.push(Number(candleClose.toFixed(6)));
    }

    return timestamps.length
      ? { timestamps, open, high, low, close }
      : null;
  }

  function renderChart(symbol) {
    if (!chartElement || !state.marketData) return;
    const chartEntry = state.marketData.chart_data?.[symbol];
    if (!chartEntry) {
      state.currentCandles = null;
      updateAnalyticsSummary(null);
      renderDataTable(null);
      return;
    }

    const targetInterval = state.interval || 5;
    const dataset = buildCandlestickDataset(
      chartEntry.prices,
      targetInterval,
      chartEntry.last_updated
    );

    if (!dataset) {
      state.currentCandles = null;
      updateAnalyticsSummary(null);
      renderDataTable(null);
      if (chartMeta) {
        chartMeta.textContent = 'Not enough market data to render the chart yet.';
      }
      return;
    }

    if (typeof Plotly === 'undefined') {
      console.error('Plotly failed to load');
      if (chartMeta) {
        chartMeta.textContent = 'Unable to render chart. Plotly failed to load.';
      }
      return;
    }

    const trace = {
      x: dataset.timestamps,
      open: dataset.open,
      high: dataset.high,
      low: dataset.low,
      close: dataset.close,
      type: 'candlestick',
      increasing: {
        line: { color: '#22c55e' },
        fillcolor: 'rgba(34, 197, 94, 0.35)',
      },
      decreasing: {
        line: { color: '#ef4444' },
        fillcolor: 'rgba(239, 68, 68, 0.35)',
      },
    };

    const layout = {
      margin: { t: 24, r: 16, b: 24, l: 48 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#e2e8f0' },
      xaxis: {
        type: 'date',
        gridcolor: 'rgba(148, 163, 184, 0.1)',
        color: '#94a3b8',
        rangeslider: { visible: true },
      },
      yaxis: {
        gridcolor: 'rgba(148, 163, 184, 0.1)',
        color: '#94a3b8',
      },
      dragmode: 'pan',
      showlegend: false,
      height: 450,
    };

    const config = {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['toggleSpikelines', 'select2d', 'lasso2d'],
    };

    Plotly.react(chartElement, [trace], layout, config);
    state.currentCandles = dataset;
    updateAnalyticsSummary(dataset);
    renderDataTable(dataset);

    if (chartMeta) {
      const updatedAt = new Date(chartEntry.last_updated || Date.now());
      const validDate = Number.isNaN(updatedAt.getTime()) ? new Date() : updatedAt;
      chartMeta.textContent = `${symbol} · ${targetInterval}-minute candles · Updated ${validDate.toLocaleTimeString()}`;
    }
  }

  async function loadMarketData() {
    try {
      const response = await fetch('/api/market-data');
      if (!response.ok) throw new Error('Failed to load market data');
      const payload = await response.json();
      state.marketData = payload;
      renderTicker(payload.tickers);
      if (coinSelect && !coinSelect.options.length) {
        payload.tickers.forEach((ticker) => {
          const option = document.createElement('option');
          option.value = ticker.symbol;
          option.textContent = `${ticker.symbol} · ${ticker.name}`;
          coinSelect.appendChild(option);
        });
      }
      const selected = coinSelect?.value || payload.tickers[0]?.symbol;
      if (selected) {
        coinSelect.value = selected;
        renderChart(selected);
      }
    } catch (error) {
      console.error(error);
    }
  }

  async function loadPredictionHistory() {
    try {
      const response = await fetch('/api/predictions/history');
      if (!response.ok) throw new Error('Failed to load history');
      const history = await response.json();
      state.history = history;
      const container = document.getElementById('prediction-history');
      if (!container) return;
      container.innerHTML = '';
      history.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `
          <span><strong>${item.symbol}</strong> · ${item.prediction} <span class="text-secondary">(${item.timeframe ? item.timeframe.toUpperCase() : '--'})</span></span>
          <span class="badge">${(item.confidence * 100).toFixed(1)}%</span>
        `;
        container.appendChild(li);
      });
    } catch (error) {
      console.error(error);
    }
  }
  async function loadAlertsData(){
    try {
      const response = await fetch('/api/get-alerts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // body: JSON.stringify({user_id: current_user.id})
      });
      if (!response.ok) throw new Error('Failed to load alerts data');
      const payload = await response.json();
      state.alerts = payload;
      console.log('API call to get alerts data was successful');
      const alertsList = document.getElementById('alerts_data_render');
      alertsList.innerHTML = '';

      if (payload.alerts.length === 0) {
        const emptyMessage = document.createElement('p');
        emptyMessage.className = 'small mb-0 alerts-empty';
        emptyMessage.textContent = 'No alerts configured yet. Create one to get notified.';
        alertsList.appendChild(emptyMessage);
      } else {
        payload.alerts.forEach((alert) => {
          const alertElement = document.createElement('li');
          alertElement.className = 'list-group-item d-flex justify-content-between align-items-center';

          const alertSymbol = document.createElement('div');
          const strong = document.createElement('strong');
          strong.textContent = alert.symbol;
          alertSymbol.appendChild(strong);

          const alertMeta = document.createElement('span');
          alertMeta.className = 'd-block small alerts-meta';
          alertMeta.textContent = `${alert.direction === 'above' ? 'Upward' : 'Downward'} · $${alert.threshold.toFixed(2)}`;
          alertSymbol.appendChild(alertMeta);

          const alertBadge = document.createElement('span');
          alertBadge.className = `badge ${alert.is_active ? 'bg-success' : 'bg-secondary'}`;
          alertBadge.textContent = `${alert.is_active ? 'Active' : 'Triggered'}`;

          alertElement.appendChild(alertSymbol);
          alertElement.appendChild(alertBadge);

          alertsList.appendChild(alertElement);
        });
      }
    } catch (error) {
      console.error(error);
    }
  }

  async function triggerPrediction() {
    const selected = coinSelect?.value || 'BTC';
    const timeframe = timeframeSelect?.value || '15m';
    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbol: selected, timeframe }),
      });
      if (!response.ok) throw new Error('Prediction failed');
      const result = await response.json();
      if (result.error) throw new Error(result.error);
      document.getElementById('prediction-label').textContent = result.prediction;
      document.getElementById('prediction-confidence').textContent = `${(result.confidence * 100).toFixed(1)}%`;
      document.getElementById('prediction-symbol').textContent = result.symbol;
      if (timeframeSelect && result.timeframe) {
        timeframeSelect.value = result.timeframe;
      }
      if (timeframeDisplay) {
        const displayValue = result.timeframe ? result.timeframe.toUpperCase() : timeframe.toUpperCase();
        timeframeDisplay.textContent = displayValue;
      }
      if (result.metrics) {
        const { accuracy, precision, recall } = result.metrics;
        document.getElementById('metric-accuracy').textContent =
          accuracy !== undefined ? `${(accuracy * 100).toFixed(1)}%` : '--';
        document.getElementById('metric-precision').textContent =
          precision !== undefined ? `${(precision * 100).toFixed(1)}%` : '--';
        document.getElementById('metric-recall').textContent =
          recall !== undefined ? `${(recall * 100).toFixed(1)}%` : '--';
      }
      loadPredictionHistory();
    } catch (error) {
      console.error(error);
      document.getElementById('prediction-label').textContent = 'Error';
      document.getElementById('prediction-confidence').textContent = '--';
    }
  }

  async function retrainModel() {
    try {
      const response = await fetch('/api/predict/retrain', { method: 'POST' });
      if (!response.ok) throw new Error('Retrain failed');
      const payload = await response.json();
      const metrics = payload.metrics || {};
      document.getElementById('metric-accuracy').textContent =
        metrics.accuracy !== undefined ? `${(metrics.accuracy * 100).toFixed(1)}%` : '--';
      document.getElementById('metric-precision').textContent =
        metrics.precision !== undefined ? `${(metrics.precision * 100).toFixed(1)}%` : '--';
      document.getElementById('metric-recall').textContent =
        metrics.recall !== undefined ? `${(metrics.recall * 100).toFixed(1)}%` : '--';
      const toast = document.createElement('div');
      toast.className = 'toast align-items-center text-bg-success border-0 show position-fixed bottom-0 end-0 m-3';
      toast.innerHTML = `<div class="d-flex"><div class="toast-body">Model retrained at ${new Date(payload.updated_at).toLocaleTimeString()}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    } catch (error) {
      console.error(error);
    }
  }

  function exportCSV() {
    if (!state.history.length) return;
    const rows = [
      ['Symbol', 'Prediction', 'Confidence', 'Timeframe', 'Created At'],
      ...state.history.map((item) => [
        item.symbol,
        item.prediction,
        `${(item.confidence * 100).toFixed(2)}%`,
        item.timeframe,
        new Date(item.created_at).toLocaleString(),
      ]),
    ];
    const csvContent = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cryptoknight_predictions.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportPDF() {
    if (!state.history.length) return;
    const popup = window.open('', '_blank');
    const rows = state.history
      .map(
        (item) => `
        <tr>
          <td>${item.symbol}</td>
          <td>${item.prediction}</td>
          <td>${(item.confidence * 100).toFixed(1)}%</td>
          <td>${item.timeframe}</td>
          <td>${new Date(item.created_at).toLocaleString()}</td>
        </tr>`
      )
      .join('');
    popup.document.write(`
      <html><head><title>CryptoKnight Report</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 24px; }
        h1 { color: #0096ff; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background: #f3f4f6; }
      </style>
      </head><body>
      <h1>CryptoKnight Prediction Report</h1>
      <p>Generated at ${new Date().toLocaleString()}</p>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Prediction</th>
            <th>Confidence</th>
            <th>Timeframe</th>
            <th>Created At</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      </body></html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  }

  if (coinSelect) {
    coinSelect.addEventListener('change', (event) => {
      renderChart(event.target.value);
    });
  }

  if (intervalSelect) {
    intervalSelect.addEventListener('change', (event) => {
      const value = Number(event.target.value);
      state.interval = Number.isFinite(value) && value > 0 ? value : 5;
      const selected = coinSelect?.value;
      if (selected) {
        renderChart(selected);
      }
    });
  }

  if (timeframeSelect && timeframeDisplay) {
    timeframeSelect.addEventListener('change', (event) => {
      timeframeDisplay.textContent = event.target.value.toUpperCase();
    });
  }

  document.getElementById('trigger-prediction')?.addEventListener('click', triggerPrediction);
  document.getElementById('retrain-model')?.addEventListener('click', retrainModel);
  function exportXLSX() {
    const dataset = state.currentCandles;
    if (!dataset || !dataset.timestamps?.length) return;

    if (typeof XLSX === 'undefined') {
      console.error('XLSX library is not available');
      return;
    }

    const rows = dataset.timestamps.map((timestamp, index) => ({
      Time: formatTimestamp(timestamp),
      Open: Number(dataset.open[index]),
      High: Number(dataset.high[index]),
      Low: Number(dataset.low[index]),
      Close: Number(dataset.close[index]),
    }));

    const worksheet = XLSX.utils.json_to_sheet(rows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Market Data');
    const symbol = coinSelect?.value || 'data';
    XLSX.writeFile(workbook, `cryptoknight_${symbol}.xlsx`);
  }

  document.getElementById('export-csv')?.addEventListener('click', exportCSV);
  document.getElementById('export-pdf')?.addEventListener('click', exportPDF);
  document.getElementById('export-xlsx')?.addEventListener('click', exportXLSX);

  updateAnalyticsSummary(null);
  renderDataTable(null);
  loadMarketData();
  loadPredictionHistory();
  loadAlertsData();
  setInterval(loadAlertsData, 5000);
  setInterval(loadMarketData, 20_000);
})();
