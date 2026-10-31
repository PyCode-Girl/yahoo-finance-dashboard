import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getHistory, getNews, getTicker } from "../api";
import { Empty, ErrorState, Loading } from "../components/States";
import {
  changeClass,
  formatChange,
  formatCompact,
  formatDateTime,
  formatNumber,
  formatPercent,
  formatPrice,
} from "../format";

const RANGES = [
  { label: "1W", days: 5 },
  { label: "1M", days: 21 },
  { label: "3M", days: null },
];

function shortDate(value) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function formatRange(low, high) {
  if (low === null || low === undefined || high === null || high === undefined) return "—";
  return `${formatPrice(low)} - ${formatPrice(high)}`;
}

function QuoteItem({ label, value }) {
  return (
    <div className="quote-item">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

export default function TickerDetail() {
  const { symbol } = useParams();
  const [ticker, setTicker] = useState(null);
  const [history, setHistory] = useState(null); // null means it failed to load
  const [news, setNews] = useState(null); // null means it failed to load
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rangeLabel, setRangeLabel] = useState("3M");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all([
      getTicker(symbol),
      getHistory(symbol).then((result) => result.results).catch(() => null),
      getNews(symbol).then((result) => result.results).catch(() => null),
    ])
      .then(([tickerData, historyData, newsData]) => {
        if (cancelled) return;
        setTicker(tickerData);
        setHistory(historyData);
        setNews(newsData);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, reloadKey]);

  const chartData = useMemo(() => {
    if (!history) return [];
    const selected = RANGES.find((item) => item.label === rangeLabel);
    const rows = history.filter((row) => row.close_price !== null);
    const sliced = selected.days ? rows.slice(-selected.days) : rows;
    return sliced.map((row) => ({ date: row.date, close: row.close_price }));
  }, [history, rangeLabel]);

  const backLink = (
    <Link className="back-link" to="/">
      ← Back to all tickers
    </Link>
  );

  if (loading) {
    return (
      <div>
        {backLink}
        <Loading text={`Loading ${symbol}...`} />
      </div>
    );
  }

  if (error || !ticker) {
    return (
      <div>
        {backLink}
        <div className="card">
          <ErrorState
            message={error || "Something went wrong. Please try again."}
            onRetry={() => setReloadKey((key) => key + 1)}
          />
        </div>
      </div>
    );
  }

  const quote = ticker.quote || {};
  const tone = changeClass(quote.change);
  const lineColor =
    chartData.length > 1 && chartData[chartData.length - 1].close < chartData[0].close
      ? "#d93025"
      : "#0f9d58";

  return (
    <div>
      {backLink}

      <div className="card detail-header">
        <h1>
          {ticker.symbol} <span className="muted">· {ticker.company_name || "—"}</span>
        </h1>
        <div className="sub">
          {ticker.exchange || "—"} · {ticker.currency || "—"}
        </div>
        <div className="price-row">
          <span className="price">{formatPrice(quote.current_price)}</span>
          <span className={tone}>
            {formatChange(quote.change)} ({formatPercent(quote.change_percent)})
          </span>
        </div>
        <div className="muted" style={{ fontSize: "0.85rem", marginTop: 6 }}>
          Prices are delayed by about 15 minutes. Last updated{" "}
          {formatDateTime(quote.scraped_at)}.
        </div>
      </div>

      <div className="card">
        <h2>Quote</h2>
        <div className="quote-grid">
          <QuoteItem label="Previous Close" value={formatPrice(quote.previous_close)} />
          <QuoteItem label="Open" value={formatPrice(quote.open_price)} />
          <QuoteItem label="Day's Range" value={formatRange(quote.days_low, quote.days_high)} />
          <QuoteItem label="52 Week Range" value={formatRange(quote.week52_low, quote.week52_high)} />
          <QuoteItem label="Volume" value={formatNumber(quote.volume)} />
          <QuoteItem label="Market Cap" value={formatCompact(quote.market_cap)} />
          <QuoteItem label="PE Ratio (TTM)" value={formatPrice(quote.pe_ratio)} />
          <QuoteItem label="EPS (TTM)" value={formatPrice(quote.eps)} />
        </div>
      </div>

      <div className="card">
        <h2>Price chart</h2>
        <div className="range-buttons">
          {RANGES.map((item) => (
            <button
              key={item.label}
              className={item.label === rangeLabel ? "active" : ""}
              onClick={() => setRangeLabel(item.label)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {history === null ? (
          <ErrorState message="We couldn't load the price history right now." />
        ) : chartData.length === 0 ? (
          <Empty text="No price history is available for this ticker." />
        ) : (
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e3e8f0" />
                <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={30} />
                <YAxis domain={["auto", "auto"]} width={60} tickFormatter={(v) => v.toFixed(0)} />
                <Tooltip
                  labelFormatter={shortDate}
                  formatter={(value) => [formatPrice(value), "Close"]}
                />
                <Line
                  type="monotone"
                  dataKey="close"
                  stroke={lineColor}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Company information</h2>
        <div className="info-grid">
          <QuoteItem label="Sector" value={ticker.sector || "—"} />
          <QuoteItem label="Industry" value={ticker.industry || "—"} />
          <QuoteItem label="Employees" value={formatNumber(ticker.full_time_employees)} />
          <QuoteItem
            label="Website"
            value={
              ticker.website ? (
                <a href={ticker.website} target="_blank" rel="noopener noreferrer">
                  {ticker.website}
                </a>
              ) : (
                "—"
              )
            }
          />
        </div>
        <p>{ticker.business_summary || "No company description is available."}</p>
      </div>

      <div className="card">
        <h2>Recent news</h2>
        {news === null ? (
          <ErrorState message="We couldn't load the news right now." />
        ) : news.length === 0 ? (
          <Empty text="No recent news for this ticker." />
        ) : (
          <ul className="news-list">
            {news.map((article) => (
              <li key={article.id}>
                <a href={article.url} target="_blank" rel="noopener noreferrer">
                  {article.title}
                </a>
                <div className="meta">
                  {article.source || "Unknown source"} · {formatDateTime(article.published_at)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}