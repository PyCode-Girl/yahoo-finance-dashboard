const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Can't reach the server. Please check your connection and try again.");
  }

  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // keep the friendly default message
    }
    throw new Error(message);
  }
  return response.json();
}

export function getTickers({ search = "", sortBy = "symbol", order = "asc", page = 1, pageSize = 20 } = {}) {
  const params = new URLSearchParams({ sort_by: sortBy, order, page, page_size: pageSize });
  if (search) params.set("search", search);
  return request(`/api/tickers?${params}`);
}

export function addTicker(symbol) {
  return request("/api/tickers", {
    method: "POST",
    body: JSON.stringify({ symbol }),
  });
}

export function getTicker(symbol) {
  return request(`/api/tickers/${encodeURIComponent(symbol)}`);
}

export function getHistory(symbol, { start, end } = {}) {
  const params = new URLSearchParams({ page_size: 500 });
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  return request(`/api/tickers/${encodeURIComponent(symbol)}/history?${params}`);
}

export function getNews(symbol) {
  return request(`/api/tickers/${encodeURIComponent(symbol)}/news`);
}