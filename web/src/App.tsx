import { useCallback, useEffect, useState } from "react";
import { fetchMeta, fetchStatus } from "./api";
import { ChartPanel } from "./components/ChartPanel";
import { Header } from "./components/Header";
import { LogDrawer } from "./components/LogDrawer";
import { StreamerGrid } from "./components/StreamerGrid";
import type { StatusSnapshot } from "./types";

const SELECTED_KEY = "twitch-miner-selected-streamer";

export default function App() {
  const [status, setStatus] = useState<StatusSnapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const [daysAgo, setDaysAgo] = useState(7);
  const [selected, setSelected] = useState<string | null>(() =>
    localStorage.getItem(SELECTED_KEY),
  );

  const selectStreamer = useCallback((username: string) => {
    setSelected(username);
    localStorage.setItem(SELECTED_KEY, username);
  }, []);

  useEffect(() => {
    fetchMeta()
      .then((m) => setDaysAgo(m.days_ago))
      .catch(() => undefined);

    fetchStatus()
      .then(setStatus)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const es = new EventSource("/api/events");

    es.onopen = () => setConnected(true);
    es.onmessage = (ev) => {
      try {
        const snap = JSON.parse(ev.data) as StatusSnapshot;
        setStatus(snap);
        setConnected(true);
      } catch {
        /* ignore malformed payloads */
      }
    };
    es.onerror = () => setConnected(false);

    return () => es.close();
  }, []);

  useEffect(() => {
    if (!status?.streamers.length) return;
    const names = status.streamers.map((s) => s.username);
    if (selected && names.includes(selected)) return;
    selectStreamer(names[0]);
  }, [status, selected, selectStreamer]);

  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-6 pb-24">
      <Header status={status} connected={connected} />

      {status && status.predictions.length > 0 && (
        <section className="mt-6 rounded-xl border border-twitch-border bg-twitch-panel p-4">
          <h2 className="mb-2 text-sm font-medium text-twitch-muted">Active predictions</h2>
          <ul className="space-y-1 text-sm">
            {status.predictions.map((p, i) => (
              <li key={`${p.streamer}-${p.title}-${i}`}>
                <span className="text-twitch-purple">{p.streamer}</span>
                {" · "}
                {p.title}
                {p.bet_placed && (
                  <span className="ml-2 text-emerald-400">bet placed</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mt-8 space-y-8">
        <StreamerGrid
          streamers={status?.streamers ?? []}
          selected={selected}
          onSelect={selectStreamer}
        />
        <ChartPanel streamer={selected} daysAgo={daysAgo} />
      </div>

      <footer className="mt-12 border-t border-twitch-border pt-6 text-center text-xs text-twitch-muted">
        Advanced settings: edit{" "}
        <code className="rounded bg-twitch-panel px-1">config.yaml</code> or{" "}
        <code className="rounded bg-twitch-panel px-1">example.py</code> for bets and
        notifications.
      </footer>

      <LogDrawer />
    </div>
  );
}
