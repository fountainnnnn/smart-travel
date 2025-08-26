"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const LINES = ["NSL", "EWL", "DTL", "NEL", "CCL", "TEL"];

type Health = { status: string; time_utc: string };

type ForecastArea = { name: string; forecast: string; label_location?: Record<string, unknown> | null };
type WeatherOut = { updated_at: string; areas: ForecastArea[] };

type MrtAlert = {
  line: string;
  status: string;
  message?: string | null;
  timestamp?: string | null;
  direction?: string | null;
  stations?: string | null;
  bus_shuttle?: string | null;
};
type MrtOut = {
  ok: boolean;
  source: string;
  updated_at: string;
  has_disruption?: boolean | null;
  alerts: MrtAlert[];
};

type CrowdStation = {
  station_code: string | null;
  station: string | null;
  crowd_level: string | null;
  last_update: string | null;
};
type CrowdResp = { ok: boolean; source: string; line: string; updated_at: string; stations: CrowdStation[] };
type CrowdForecastRow = { station_code: string | null; station: string | null; time_slot: string | null; crowd_level: string | null };
type CrowdForecastResp = { ok: boolean; source: string; line: string; updated_at: string; forecast: CrowdForecastRow[] };

export default function Page() {
  const [health, setHealth] = useState<Health | null>(null);
  const [weather, setWeather] = useState<WeatherOut | null>(null);
  const [mrt, setMrt] = useState<MrtOut | null>(null);
  const [line, setLine] = useState<string>("NSL");
  const [crowd, setCrowd] = useState<CrowdResp | null>(null);
  const [forecast, setForecast] = useState<CrowdForecastResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // initial load
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

  // load crowd when line changes
  useEffect(() => {
    const run = async () => {
      try {
        const [c, f] = await Promise.all([
          fetch(`${API_BASE}/mrt/crowd?line=${encodeURIComponent(line)}`).then(r => r.json()),
          fetch(`${API_BASE}/mrt/crowd-forecast?line=${encodeURIComponent(line)}`).then(r => r.json()),
        ]);
        setCrowd(c);
        setForecast(f);
      } catch (e) {
        // ignore UI error; cards will show fallback
      }
    };
    run();
  }, [line]);

  const crowdSorted = useMemo(() => {
    if (!crowd?.stations) return [];
    // sort by crowd level: VeryHigh > High > Moderate > Low
    const rank: Record<string, number> = { veryhigh: 4, high: 3, moderate: 2, low: 1 };
    return [...crowd.stations].sort((a, b) => {
      const ra = rank[(a.crowd_level || "").replace(/\s+/g, "").toLowerCase()] || 0;
      const rb = rank[(b.crowd_level || "").replace(/\s+/g, "").toLowerCase()] || 0;
      return rb - ra || (a.station || "").localeCompare(b.station || "");
    });
  }, [crowd]);

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
          {/* Weather */}
          <div className="card">
            <h2 className="h">Weather (2 hour forecast)</h2>
            <div className="badge">Updated: {weather?.updated_at ?? "Unknown"}</div>
            <div className="mono" style={{ marginTop: 12 }}>
              {weather?.areas?.slice(0, 12).map(a => `• ${a.name}: ${a.forecast}`).join("\n")}
            </div>
          </div>

          {/* MRT Alerts */}
          <div className="card">
            <h2 className="h">MRT Alerts</h2>
            <div className="row">
              <span className="badge">Source: {mrt?.source ?? "Unknown"}</span>
              <span className="badge">Updated: {mrt?.updated_at ?? "Unknown"}</span>
              {mrt?.ok && mrt.has_disruption === false && <span className="badge">All lines normal</span>}
            </div>
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

          {/* Crowd selector + Realtime crowd */}
          <div className="card">
            <h2 className="h">MRT Crowd (Realtime)</h2>
            <div className="row" style={{ marginBottom: 8 }}>
              <label htmlFor="line">Line:</label>
              <select
                id="line"
                value={line}
                onChange={e => setLine(e.target.value)}
                style={{ background: "#0f1420", color: "#e6e6e6", borderRadius: 8, padding: "6px 8px", border: "1px solid #2b3547" }}
              >
                {LINES.map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
              <span className="badge">Updated: {crowd?.updated_at ?? "—"}</span>
            </div>

            {crowd?.ok && crowdSorted.length > 0 ? (
              <div className="mono">
                {crowdSorted.map(s => `• ${s.station ?? s.station_code ?? "Unknown"}: ${s.crowd_level ?? "Unknown"}`).join("\n")}
              </div>
            ) : (
              <div className="mono">No crowd data.</div>
            )}
          </div>

          {/* Forecast crowd */}
          <div className="card">
            <h2 className="h">MRT Crowd Forecast</h2>
            <div className="row" style={{ marginBottom: 8 }}>
              <span className="badge">Line: {line}</span>
              <span className="badge">Updated: {forecast?.updated_at ?? "—"}</span>
            </div>
            {forecast?.ok && forecast.forecast?.length ? (
              <div className="mono">
                {forecast.forecast.slice(0, 20).map(f =>
                  `• ${f.time_slot ?? "Time"} — ${f.station ?? f.station_code ?? "Unknown"}: ${f.crowd_level ?? "Unknown"}`
                ).join("\n")}
              </div>
            ) : (
              <div className="mono">No forecast data.</div>
            )}
          </div>

          {/* Raw JSON (handy for dev) */}
          <div className="card">
            <h2 className="h">Raw JSON</h2>
            <details>
              <summary>mrt (alerts)</summary>
              <pre className="mono">{JSON.stringify(mrt, null, 2)}</pre>
            </details>
            <details>
              <summary>crowd (realtime)</summary>
              <pre className="mono">{JSON.stringify(crowd, null, 2)}</pre>
            </details>
            <details>
              <summary>crowd forecast</summary>
              <pre className="mono">{JSON.stringify(forecast, null, 2)}</pre>
            </details>
            <details>
              <summary>weather</summary>
              <pre className="mono">{JSON.stringify(weather, null, 2)}</pre>
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
