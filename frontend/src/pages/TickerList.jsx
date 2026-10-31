import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { addTicker, getTickers } from "../api";
import { Empty, ErrorState, Loading } from "../components/States";
import {
  changeClass,
  formatChange,
  formatCompact,
  formatPercent,
  formatPrice,
} from "../format";
import { useDebounce } from "../useDebounce";

const COLUMNS = [
  { key: "symbol", label: "Symbol", firstOrder: "asc" },
  { key: "company_name", label: "Company", firstOrder: "asc" },
  { key: "current_price", label: "Price", firstOrder: "desc" },
  { key: "change", label: "Change", firstOrder: "desc" },
  { key: "change_percent", label: "Change %", firstOrder: "desc" },
  { key: "market_cap", label: "Market Cap", firstOrder: "desc" },
];

export default function TickerList() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 400);
  const [sortBy, setSortBy] = useState("symbol");
  const [order, setOrder] = useState("asc");
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [newSymbol, setNewSymbol] = useState("");
  const [adding, setAdding] = useState(false);
  const [addMessage, setAddMessage] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getTickers({ search: debouncedSearch, sortBy, order, page })
      .then((result) => {
        if (!cancelled) setData(result);
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
  }, [debouncedSearch, sortBy, order, page, reloadKey]);

  function handleSearchChange(event) {
    setSearch(event.target.value);
    setPage(1);
  }

  function handleSort(column) {
    if (sortBy === column.key) {
      setOrder(order === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column.key);
      setOrder(column.firstOrder);
    }
    setPage(1);
  }

  async function handleAdd(event) {
    event.preventDefault();
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) return;
    setAdding(true);
    setAddMessage(null);
    try {
      await addTicker(symbol);
      setAddMessage({ type: "success", text: `${symbol} was added.` });
      setNewSymbol("");
      setReloadKey((key) => key + 1);
    } catch (err) {
      setAddMessage({ type: "error", text: err.message });
    } finally {
      setAdding(false);
    }
  }

  const rows = data ? data.results : [];

  let content;
  if (error) {
    content = (
      <ErrorState message={error} onRetry={() => setReloadKey((key) => key + 1)} />
    );
  } else if (loading && !data) {
    content = <Loading text="Loading tickers..." />;
  } else if (rows.length === 0) {
    content = (
      <Empty
        text={
          debouncedSearch
            ? "No tickers match your search."
            : "No tickers are tracked yet. Add one above to get started."
        }
      />
    );
  } else {
    content = (
      <div className="table-wrap" style={{ opacity: loading ? 0.6 : 1 }}>
        <table>
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  className="sortable"
                  onClick={() => handleSort(column)}
                >
                  {column.label}
                  {sortBy === column.key ? (order === "asc" ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((ticker) => {
              const quote = ticker.quote || {};
              const tone = changeClass(quote.change);
              return (
                <tr key={ticker.symbol}>
                  <td className="symbol">
                    <Link to={`/ticker/${ticker.symbol}`}>{ticker.symbol}</Link>
                  </td>
                  <td>{ticker.company_name || "—"}</td>
                  <td>{formatPrice(quote.current_price)}</td>
                  <td className={tone}>{formatChange(quote.change)}</td>
                  <td className={tone}>{formatPercent(quote.change_percent)}</td>
                  <td>{formatCompact(quote.market_cap)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Search by symbol or company..."
          value={search}
          onChange={handleSearchChange}
          aria-label="Search tickers"
        />
        <form className="add-form" onSubmit={handleAdd}>
          <input
            type="text"
            placeholder="Add a ticker, e.g. NVDA"
            value={newSymbol}
            onChange={(event) => setNewSymbol(event.target.value)}
            aria-label="Ticker symbol to add"
            disabled={adding}
          />
          <button className="btn" type="submit" disabled={adding || !newSymbol.trim()}>
            {adding ? "Adding..." : "Add"}
          </button>
        </form>
      </div>

      {adding && (
        <div className="message success">
          Fetching data from Yahoo Finance. This can take up to 30 seconds...
        </div>
      )}
      {addMessage && (
        <div className={`message ${addMessage.type}`}>{addMessage.text}</div>
      )}

      <div className="card">{content}</div>

      {data && data.total_pages > 1 && (
        <div className="toolbar" style={{ justifyContent: "center", alignItems: "center" }}>
          <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {data.page} of {data.total_pages}
          </span>
          <button
            className="btn"
            disabled={page >= data.total_pages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}