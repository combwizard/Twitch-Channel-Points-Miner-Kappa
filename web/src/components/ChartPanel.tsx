import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchAnalytics, formatDateInput } from "../api";
import type { AnalyticsData } from "../types";

interface ChartPanelProps {
  streamer: string | null;
  daysAgo: number;
}

export function ChartPanel({ streamer, daysAgo }: ChartPanelProps) {
  const endDefault = useMemo(() => new Date(), []);
  const startDefault = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    return d;
  }, [daysAgo]);

  const [startDate, setStartDate] = useState(formatDateInput(startDefault));
  const [endDate, setEndDate] = useState(formatDateInput(endDefault));
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!streamer) {
      setData(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAnalytics(streamer, startDate, endDate)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) {
          setData(null);
          setError(e instanceof Error ? e.message : "Failed to load chart");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [streamer, startDate, endDate]);

  const chartData = useMemo(() => {
    if (!data?.series?.length) return [];
    return data.series.map((p) => ({
      time: new Date(p.x).toLocaleString(),
      points: p.y,
      event: p.z,
    }));
  }, [data]);

  return (
    <section className="rounded-xl border border-twitch-border bg-twitch-panel p-4">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-medium">
          Analytics{streamer ? `: ${streamer}` : ""}
        </h2>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label className="flex items-center gap-1 text-twitch-muted">
            From
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded border border-twitch-border bg-twitch-dark px-2 py-1 text-white"
            />
          </label>
          <label className="flex items-center gap-1 text-twitch-muted">
            To
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded border border-twitch-border bg-twitch-dark px-2 py-1 text-white"
            />
          </label>
        </div>
      </div>

      {!streamer && (
        <p className="py-12 text-center text-sm text-twitch-muted">
          Select a streamer to view point history.
        </p>
      )}

      {streamer && loading && (
        <p className="py-12 text-center text-sm text-twitch-muted">Loading chart…</p>
      )}

      {streamer && error && !loading && (
        <p className="py-12 text-center text-sm text-amber-400">{error}</p>
      )}

      {streamer && !loading && !error && chartData.length === 0 && (
        <p className="py-12 text-center text-sm text-twitch-muted">
          No analytics data yet. Enable analytics and run the miner while this streamer is live.
        </p>
      )}

      {streamer && chartData.length > 0 && (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#2f2f35" strokeDasharray="3 3" />
              <XAxis dataKey="time" hide />
              <YAxis
                tick={{ fill: "#adadb8", fontSize: 11 }}
                tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
                width={48}
              />
              <Tooltip
                contentStyle={{
                  background: "#18181b",
                  border: "1px solid #2f2f35",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#adadb8" }}
              />
              <Line
                type="monotone"
                dataKey="points"
                stroke="#9146ff"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
