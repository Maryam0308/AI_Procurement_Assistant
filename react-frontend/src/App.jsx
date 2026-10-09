
import { useEffect, useRef, useState } from 'react';
import './App.css';

// ==========================================
// P3.1 - SMART SUGGESTED QUESTIONS
// ==========================================

const suggestions = [
  {
    category: 'Spending Analysis',
    icon: '💰',
    title: 'Total Procurement Spending',
    description:
      'Explore the overall California government procurement expenditure.',
    question: 'What is the total procurement spending?',
  },
  {
    category: 'Supplier Intelligence',
    icon: '🏢',
    title: 'Top Suppliers',
    description:
      'Discover the five suppliers with the highest procurement spending.',
    question: 'Who are the top 5 suppliers by spending?',
  },
  {
    category: 'Department Analysis',
    icon: '🏛️',
    title: 'Highest-Spending Department',
    description:
      'Identify the department with the highest spending in 2014.',
    question: 'Which department spent the most in 2014?',
  },
  {
    category: 'Purchase Orders',
    icon: '📦',
    title: 'Purchase Order Count',
    description:
      'Count unique purchase orders created during March 2014.',
    question: 'How many purchase orders were created in March 2014?',
  },
  {
    category: 'Quarterly Insights',
    icon: '📊',
    title: 'Highest-Spending Quarter',
    description:
      'Find the quarter with the greatest procurement spending in 2013.',
    question: 'Which quarter had the highest spending in 2013?',
  },
  {
    category: 'Item Intelligence',
    icon: '🔎',
    title: 'Frequently Purchased Items',
    description:
      'Explore the five most frequently recorded items in 2015.',
    question: 'What were the top 5 most frequently purchased items in 2015?',
  },
];

// ==========================================
// FORMATTING FUNCTIONS
// ==========================================

function formatMoney(value) {
  return (
    '$' +
    Number(value ?? 0).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

function compactMoney(value) {
  const n = Number(value ?? 0);

  if (Math.abs(n) >= 1e9) {
    return '$' + (n / 1e9).toFixed(2) + 'B';
  }

  if (Math.abs(n) >= 1e6) {
    return '$' + (n / 1e6).toFixed(2) + 'M';
  }

  return formatMoney(n);
}

// ==========================================
// DASHBOARD STATISTICS
// ==========================================

function StatCard({ label, value, description }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      <div className="description">{description}</div>
    </div>
  );
}

// ==========================================
// EXISTING DASHBOARD CHARTS
// ==========================================

function SpendingBars({
  title,
  rows = [],
  labelKey = 'name',
}) {
  const safeRows = Array.isArray(rows) ? rows : [];

  const max = Math.max(
    1,
    ...safeRows.map((row) => Number(row.spending) || 0)
  );

  return (
    <section className="panel">
      <h3>{title}</h3>

      {safeRows.length === 0 ? (
        <p>No data available.</p>
      ) : (
        safeRows.map((row, index) => {
          const spending = Number(row.spending) || 0;
          const percentage = Math.max(
            0,
            Math.min(100, (spending / max) * 100)
          );

          return (
            <div
              className="bar-row"
              key={`${row[labelKey]}-${index}`}
            >
              <div className="bar-label">
                <span>{String(row[labelKey])}</span>
                <span>{compactMoney(spending)}</span>
              </div>

              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })
      )}
    </section>
  );
}

// ==========================================
// P3.2 - CHAT RESPONSE CHART
// ==========================================

function ChatResponseChart({ intent, data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return null;
  }

  const chartTypes = {
    top_suppliers: {
      title: 'Supplier Spending Comparison',
      labelKey: 'name',
      valueKey: 'spending',
      format: 'money',
    },
    top_departments: {
      title: 'Department Spending Comparison',
      labelKey: 'name',
      valueKey: 'spending',
      format: 'money',
    },
    top_items: {
      title: 'Item Spending Comparison',
      labelKey: 'name',
      valueKey: 'spending',
      format: 'money',
    },
    yearly_spending: {
      title: 'Annual Procurement Spending',
      labelKey: 'year',
      valueKey: 'spending',
      format: 'money',
    },
    most_frequent_items: {
      title: 'Most Frequently Purchased Items',
      labelKey: 'name',
      valueKey: 'frequency',
      format: 'number',
    },
  };

  const config = chartTypes[intent];

  if (!config) {
    return null;
  }

  const rows = data
    .filter((row) => {
      if (!row || typeof row !== 'object') {
        return false;
      }

      const value = Number(row[config.valueKey]);

      return (
        row[config.labelKey] !== undefined &&
        row[config.labelKey] !== null &&
        Number.isFinite(value)
      );
    })
    .map((row) => ({
      label: String(row[config.labelKey]),
      value: Number(row[config.valueKey]),
    }));

  if (rows.length === 0) {
    return null;
  }

  const max = Math.max(
    1,
    ...rows.map((row) => Math.max(0, row.value))
  );

  function formatValue(value) {
    if (config.format === 'money') {
      return compactMoney(value);
    }

    return value.toLocaleString('en-US');
  }

  return (
    <div className="chat-chart">
      <div className="chat-chart-heading">
        <span className="chat-chart-icon">📊</span>
        <div>
          <h4>{config.title}</h4>
          <p>Based on the MongoDB query results</p>
        </div>
      </div>

      <div
        className="chat-chart-content"
        role="img"
        aria-label={config.title}
      >
        {rows.map((row, index) => {
          const percentage = Math.max(
            0,
            Math.min(100, (row.value / max) * 100)
          );

          return (
            <div
              className="chat-chart-row"
              key={`${row.label}-${index}`}
            >
              <div className="chat-chart-label">
                <span title={row.label}>
                  {row.label}
                </span>

                <strong>
                  {formatValue(row.value)}
                </strong>
              </div>

              <div className="chat-chart-track">
                <div
                  className="chat-chart-fill"
                  style={{
                    width: `${percentage}%`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="chat-chart-footer">
        {config.format === 'money'
          ? 'Values represent recorded procurement spending in USD.'
          : 'Frequency represents the number of matching line-item records.'}
      </div>
    </div>
  );
}



/* ==========================================
   P3.4 - EXPLAIN MY QUERY
   ========================================== */

function ExplainMyQuery({ plan, intent }) {
  const [expanded, setExpanded] = useState(false);

  if (!plan || typeof plan !== 'object') {
    return null;
  }

  const analysisNames = {
    total_spending: 'Total Procurement Spending',
    record_count: 'Procurement Record Count',
    unique_order_count: 'Unique Purchase Order Count',
    top_suppliers: 'Top Suppliers by Spending',
    top_departments: 'Top Departments by Spending',
    top_items: 'Top Items by Spending',
    yearly_spending: 'Yearly Procurement Spending',
    highest_spending_quarter: 'Highest-Spending Quarter',
    most_frequent_items: 'Most Frequently Purchased Items',
  };

  const sourceNames = {
    local_parser: 'Local Question Parser',
    gemini: 'Gemini AI',
  };

  const analysis = plan.analysis || intent;

  const analysisLabel =
    analysisNames[analysis] || analysis || 'Unknown';

  const sourceLabel =
    sourceNames[plan.source] ||
    plan.source ||
    'Not specified';

  const monthNames = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  const filters = [];

  if (plan.year != null) {
    filters.push({
      label: 'Year',
      value: String(plan.year),
    });
  }

  if (plan.month != null) {
    const monthName =
      monthNames[Number(plan.month) - 1];

    filters.push({
      label: 'Month',
      value: monthName || String(plan.month),
    });
  }

  if (plan.quarter != null) {
    filters.push({
      label: 'Quarter',
      value: `Q${plan.quarter}`,
    });
  }

  if (plan.department) {
    filters.push({
      label: 'Department',
      value: String(plan.department),
    });
  }

  if (plan.supplier) {
    filters.push({
      label: 'Supplier',
      value: String(plan.supplier),
    });
  }

  const rankingAnalyses = [
    'top_suppliers',
    'top_departments',
    'top_items',
    'most_frequent_items',
  ];

  const showLimit =
    rankingAnalyses.includes(analysis) &&
    plan.limit != null;

  const calculationDescriptions = {
    total_spending:
      'Sum the total_price_numeric values of matching procurement line items.',

    record_count:
      'Count procurement line-item records matching the selected filters.',

    unique_order_count:
      'Group matching records by nonblank Purchase Order Number and count distinct groups.',

    top_suppliers:
      'Group matching records by Supplier Name, sum spending, and rank from highest to lowest.',

    top_departments:
      'Group matching records by Department Name, sum spending, and rank from highest to lowest.',

    top_items:
      'Group matching records by Item Name, sum spending, and rank from highest to lowest.',

    yearly_spending:
      'Group matching records by calendar year of Creation Date and sum spending.',

    highest_spending_quarter:
      'Group matching records by calendar year and quarter, sum spending, and return the highest-spending group.',

    most_frequent_items:
      'Group matching records by Item Name, count line-item occurrences, and rank by frequency.',
  };

  const calculation =
    calculationDescriptions[analysis] ||
    'Execute the validated procurement analysis.';

  return (
    <section className="query-explanation">
      <button
        type="button"
        className="query-explanation-toggle"
        onClick={() => setExpanded((previous) => !previous)}
        aria-expanded={expanded}
      >
        <span className="query-explanation-toggle-left">
          <span
            className="query-explanation-icon"
            aria-hidden="true"
          >
            🔍
          </span>

          <span className="query-explanation-toggle-text">
            <strong>Explain My Query</strong>
            <small>
              See how your question was interpreted
            </small>
          </span>
        </span>

        <span
          className="query-explanation-arrow"
          aria-hidden="true"
        >
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {expanded && (
        <div className="query-explanation-body">
          <div className="query-explanation-section">
            <span className="query-explanation-label">
              Analysis Type
            </span>

            <strong className="query-explanation-value">
              {analysisLabel}
            </strong>
          </div>

          <div className="query-explanation-section">
            <span className="query-explanation-label">
              Question Interpretation
            </span>

            <span className="query-source">
              {sourceLabel}
            </span>
          </div>

          <div className="query-explanation-section">
            <span className="query-explanation-label">
              Applied Filters
            </span>

            {filters.length > 0 ? (
              <div className="query-filter-list">
                {filters.map((filter) => (
                  <div
                    className="query-filter"
                    key={filter.label}
                  >
                    <span>{filter.label}</span>
                    <strong>{filter.value}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <p className="query-explanation-empty">
                No year, month, quarter, supplier,
                or department filters applied.
              </p>
            )}
          </div>

          {showLimit && (
            <div className="query-explanation-section">
              <span className="query-explanation-label">
                Maximum Results
              </span>

              <strong className="query-explanation-value">
                {plan.limit}
              </strong>
            </div>
          )}

          <div className="query-explanation-section">
            <span className="query-explanation-label">
              Calculation Method
            </span>

            <p className="query-calculation">
              {calculation}
            </p>
          </div>

          <div className="query-explanation-section">
            <span className="query-explanation-label">
              Data Source
            </span>

            <strong className="query-explanation-value">
              MongoDB — procurement_ai.purchase_orders
            </strong>
          </div>

          <div className="query-explanation-footer">
            This explanation describes the validated
            analysis plan. It does not expose or
            execute arbitrary MongoDB commands.
          </div>
        </div>
      )}
    </section>
  );
}


/* ==========================================
   P3.3 - AI PROCUREMENT INSIGHTS
   ========================================== */

function ProcurementInsights({ insights }) {
  if (!Array.isArray(insights) || insights.length === 0) {
    return null;
  }

  return (
    <section
      className="procurement-insights"
      aria-label="Procurement insights"
    >
      <div className="insights-heading">
        <span
          className="insights-icon"
          aria-hidden="true"
        >
          💡
        </span>

        <div>
          <h4>Procurement Insights</h4>
          <p>
            Automatically generated from verified
            MongoDB query results
          </p>
        </div>

        <span className="insights-count">
          {insights.length} insights
        </span>
      </div>

      <div className="insights-list">
        {insights.map((insight, index) => (
          <div
            className="insight-item"
            key={`${index}-${insight}`}
          >
            <span
              className="insight-number"
              aria-hidden="true"
            >
              {index + 1}
            </span>

            <p>{insight}</p>
          </div>
        ))}
      </div>

      <div className="insights-footer">
        <span aria-hidden="true">✓</span>
        <span>
          Data-driven analysis. Insights are calculated
          from the returned procurement records.
        </span>
      </div>
    </section>
  );
}



// ==========================================
// P3.1 - SUGGESTION CARD
// ==========================================

function SuggestionCard({
  item,
  disabled,
  onSelect,
}) {
  return (
    <button
      type="button"
      className="suggestion-card"
      disabled={disabled}
      onClick={() => onSelect(item.question)}
      aria-label={`Ask: ${item.question}`}
    >
      <div className="suggestion-card-top">
        <span
          className="suggestion-icon"
          aria-hidden="true"
        >
          {item.icon}
        </span>

        <span
          className="suggestion-arrow"
          aria-hidden="true"
        >
          ↗
        </span>
      </div>

      <span className="suggestion-category">
        {item.category}
      </span>

      <strong className="suggestion-title">
        {item.title}
      </strong>

      <span className="suggestion-description">
        {item.description}
      </span>

      <span className="suggestion-action">
        Ask this question →
      </span>
    </button>
  );
}

// ==========================================
// CHATBOT
// ==========================================

function Chatbot() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text:
        'Hello! I am your AI Procurement Assistant.\n' +
        'Ask me about procurement spending, suppliers, ' +
        'departments, purchase orders, or yearly trends.',
    },
  ]);

  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);

  const requestInProgress = useRef(false);
  const chatRef = useRef(null);

  // --------------------------------------
  // AUTO-SCROLL CHAT
  // --------------------------------------

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop =
        chatRef.current.scrollHeight;
    }
  }, [messages]);

  // --------------------------------------
  // SEND QUESTION TO FASTAPI
  // --------------------------------------

  async function sendQuestion(value) {
    const text = String(value ?? '').trim();

    if (!text || requestInProgress.current) {
      return;
    }

    requestInProgress.current = true;
    setBusy(true);
    setQuestion('');

    setMessages((previous) => [
      ...previous,
      {
        role: 'user',
        text,
      },
      {
        role: 'assistant',
        text: 'Analyzing procurement data...',
        loading: true,
      },
    ]);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: text,
        }),
      });

      if (!response.ok) {
        throw new Error(
          `Chat API returned ${response.status}`
        );
      }

      const result = await response.json();

      

setMessages((previous) => [
  ...previous.slice(0, -1),
  {
    role: 'assistant',
    text: result.answer || 'No answer returned.',
    intent: result.intent,
    data: result.data,
    insights: Array.isArray(result.insights)
      ? result.insights
      : [],
    plan: result.plan || null,
  },
]);


    } catch (error) {
      console.error('Chat error:', error);

      setMessages((previous) => [
        ...previous.slice(0, -1),
        {
          role: 'assistant',
          text:
            'Unable to process your question. ' +
            'Please try again.',
        },
      ]);
    } finally {
      requestInProgress.current = false;
      setBusy(false);
    }
  }

  // --------------------------------------
  // CHATBOT INTERFACE
  // --------------------------------------

  return (
    <section className="chat-panel">
      <div className="chat-heading">
        Ask Questions About Procurement Data
      </div>

      {/* SMART SUGGESTED QUESTIONS */}

      <div className="smart-suggestions">
        <div className="suggestions-header">
          <div>
            <h3>
              ✨ Explore Procurement Intelligence
            </h3>

            <p>
              Select a suggested question to
              analyze the procurement dataset instantly.
            </p>
          </div>

          <span className="suggestions-count">
            {suggestions.length} suggestions
          </span>
        </div>

        <div className="suggestion-grid">
          {suggestions.map((item) => (
            <SuggestionCard
              key={item.title}
              item={item}
              disabled={busy}
              onSelect={sendQuestion}
            />
          ))}
        </div>
      </div>

      {/* CHAT MESSAGES */}

      <div
        id="chat"
        ref={chatRef}
        role="log"
        aria-live="polite"
        aria-label="Procurement assistant conversation"
      >
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.role}`}
            aria-busy={Boolean(message.loading)}
          >
            <div className="message-text">
              {message.text}
            </div>

            

{message.role === 'assistant' &&
  !message.loading && (
    <>
      <ChatResponseChart
        intent={message.intent}
        data={message.data}
      />

      <ProcurementInsights
        insights={message.insights}
      />

      <ExplainMyQuery
        plan={message.plan}
        intent={message.intent}
      />
    </>
  )}


          </div>
        ))}
      </div>

      {/* CHAT INPUT */}

      <form
        className="input-area"
        onSubmit={(event) => {
          event.preventDefault();
          sendQuestion(question);
        }}
      >
        <input
          id="question"
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value);
          }}
          placeholder="Ask a procurement question..."
          autoComplete="off"
          required
          disabled={busy}
          aria-label="Procurement question"
        />

        <button
          id="send"
          type="submit"
          disabled={busy || !question.trim()}
        >
          {busy ? 'Working...' : 'Send'}
        </button>
      </form>
    </section>
  );
}

// ==========================================
// MAIN APPLICATION
// ==========================================

export default function App() {
  const [data, setData] = useState(null);

  const [status, setStatus] = useState(
    'Loading analytics from MongoDB...'
  );

  // --------------------------------------
  // LOAD DASHBOARD DATA
  // --------------------------------------

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboard() {
      try {
        const response = await fetch('/dashboard', {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(
            `Dashboard API returned ${response.status}`
          );
        }

        const result = await response.json();

        setData(result);

        setStatus(
          'Dashboard loaded successfully from MongoDB.'
        );
      } catch (error) {
        if (error.name === 'AbortError') {
          return;
        }

        console.error('Dashboard error:', error);

        setStatus(
          'Unable to load dashboard data. ' +
          'Please check that FastAPI is running ' +
          'and the /dashboard endpoint is available.'
        );
      }
    }

    loadDashboard();

    return () => controller.abort();
  }, []);

  const summary = data?.summary;
  const suppliers = data?.top_suppliers ?? [];
  const departments = data?.top_departments ?? [];

  return (
    <>
      {/* HEADER */}

      <header>
        <h1>AI Procurement Intelligence</h1>

        <p>
          California Government Procurement Analytics
          {' | '}2012–2015
        </p>
      </header>

      <main>
        {/* PROCUREMENT OVERVIEW */}

        <h2 className="section-title">
          Procurement Overview
        </h2>

        <div className="cards">
          <StatCard
            label="Total Procurement Spending"
            value={
              summary
                ? compactMoney(summary.total_spending)
                : 'Loading...'
            }
            description="Recorded line-item spending"
          />

          <StatCard
            label="Procurement Records"
            value={
              summary
                ? Number(
                    summary.total_records
                  ).toLocaleString('en-US')
                : 'Loading...'
            }
            description="Total database records"
          />

          <StatCard
            label="Top Supplier Spending"
            value={
              data
                ? (
                    suppliers.length
                      ? compactMoney(suppliers[0].spending)
                      : 'N/A'
                  )
                : 'Loading...'
            }
            description="Highest-ranked supplier"
          />

          <StatCard
            label="Top Department Spending"
            value={
              data
                ? (
                    departments.length
                      ? compactMoney(departments[0].spending)
                      : 'N/A'
                  )
                : 'Loading...'
            }
            description="Highest-ranked department"
          />
        </div>

        {/* DASHBOARD STATUS */}

        <div
          className="status"
          role="status"
        >
          {status}
        </div>

        {/* PROCUREMENT ANALYTICS */}

        <h2 className="section-title">
          Procurement Analytics
        </h2>

        <div className="charts">
          <SpendingBars
            title="Spending by Calendar Year"
            rows={data?.yearly_spending}
            labelKey="year"
          />

          <SpendingBars
            title="Top 5 Suppliers by Spending"
            rows={suppliers}
          />

          <SpendingBars
            title="Top 5 Departments by Spending"
            rows={departments}
          />

          <section className="panel">
            <h3>About the Dataset</h3>

            <p>
              This dashboard analyzes California
              government procurement records
              from 2012 to 2015.
            </p>

            <p>
              The dataset includes supplier names,
              department names, purchase information,
              quantities, and prices.
            </p>

            <p>
              Spending totals are calculated from
              procurement line-item total prices.
            </p>

            <p>
              Calendar-year analysis uses the
              purchase record Creation Date.
            </p>

            <p>
              Records do not necessarily represent
              unique purchase orders.
            </p>
          </section>
        </div>

        {/* AI PROCUREMENT ASSISTANT */}

        <h2 className="section-title">
          AI Procurement Assistant
        </h2>

        <Chatbot />
      </main>

      {/* FOOTER */}

      <footer>
        AI Procurement Intelligence
        {' | '}
        California Government Procurement Analytics
      </footer>
    </>
  );
}
