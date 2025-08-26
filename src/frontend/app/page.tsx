"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type Health = { status: string; time_utc: string };

type ForecastArea = {
  name: string;
  forecast: string;
  label_location?: Record<string, unknown> | null;
};

type WeatherOut = {
  updated_at: string;
  areas: ForecastArea[];
};

type MrtAlert = {
  line: string;
  status: string;
  message?: string | null;
  timestamp?: string | null;
};

type MrtOut = {
  source: string;
  updated_at: string;
  alerts: MrtAlert[];
};

export default function Page() {
  const [health, setHealth] = useState<Health | null>(null);
  const [weather, setWeather] = useState<WeatherOut | null>(null);
  const [mrt, setMrt] = useState<MrtOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const [h, w, m] = await Promise.all([
          fetch(`${API_BASE}/health`).then(r => r.json()),
          fetch(`${API_BASE}/weather`).then(r => r.json()),
          fetch(`${API_BASE}/mrt`).then(r => r.json()),
        ]);
        setHealth(h);
        setWeather(w);
        setMrt(m);
      } catch (e: any) {
        setErr(e?.message || "Fetch error");
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  return (
    <div className="container">
      <h1 className="h">Smart Travel Companion</h1>
      <div className="row" style={{ marginBottom: 16 }}>
        <span className="badge">Backend: {API_BASE}</span>
        {health && <span className="badge">Health: {health.status}</span>}
      </div>

      {loading && <div className="card">Loading...</div>}
      {err && <div className="card">Error: {err}</div>}

      {!loading && !err && (
        <div className="grid">
          <div className="card">
            <h2 className="h">Weather (2 hour forecast)</h2>
            <div className="badge">Updated: {weather?.updated_at ?? "Unknown"}</div>
            <div className="mono" style={{ marginTop: 12 }}>
              {weather?.areas?.slice(0, 12).map(a => `• ${a.name}: ${a.forecast}`).join("\n")}
            </div>
          </div>

          <div className="card">
            <h2 className="h">MRT Alerts</h2>
            <div className="badge">Source: {mrt?.source ?? "Unknown"}</div>
            <div className="badge">Updated: {mrt?.updated_at ?? "Unknown"}</div>
            <div className="mono" style={{ marginTop: 12 }}>
              {(mrt?.alerts?.length ?? 0) === 0
                ? "No alerts."
                : mrt?.alerts
                    ?.map(a => {
                      const parts = [
                        `• Line: ${a.line}`,
                        `Status: ${a.status}`,
                        a.message ? `Message: ${a.message}` : null,
                        a.timestamp ? `Time: ${a.timestamp}` : null,
                      ].filter(Boolean);
                      return parts.join(" | ");
                    })
                    .join("\n")}
            </div>
          </div>

          <div className="card">
            <h2 className="h">Raw JSON</h2>
            <details open>
              <summary>weather</summary>
              <pre className="mono">{JSON.stringify(weather, null, 2)}</pre>
            </details>
            <details>
              <summary>mrt</summary>
              <pre className="mono">{JSON.stringify(mrt, null, 2)}</pre>
            </details>
            <details>
              <summary>health</summary>
              <pre className="mono">{JSON.stringify(health, null, 2)}</pre>
            </details>
          </div>
        </div>
      )}
    </div>
  );
}
