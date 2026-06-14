import type { AnalyticsData, MetaInfo, StatusSnapshot } from "./types";

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function fetchStatus(): Promise<StatusSnapshot> {
  const res = await fetch("/api/status");
  return parseJson(res);
}

export async function fetchMeta(): Promise<MetaInfo> {
  const res = await fetch("/api/meta");
  return parseJson(res);
}

export async function fetchAnalytics(
  streamer: string,
  startDate?: string,
  endDate?: string,
): Promise<AnalyticsData> {
  const params = new URLSearchParams();
  if (startDate) params.set("startDate", startDate);
  if (endDate) params.set("endDate", endDate);
  const qs = params.toString();
  const res = await fetch(`/api/analytics/${streamer}${qs ? `?${qs}` : ""}`);
  return parseJson(res);
}

export async function fetchLogs(since: number): Promise<{ text: string; next_since: number }> {
  const res = await fetch(`/api/logs?since=${since}`);
  return parseJson(res);
}

export async function addStreamer(username: string): Promise<{ warning?: string }> {
  const res = await fetch("/api/streamers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  const body = await parseJson<{ ok: boolean; warning?: string }>(res);
  return { warning: body.warning };
}

export async function removeStreamer(username: string): Promise<void> {
  const res = await fetch(`/api/streamers/${encodeURIComponent(username)}`, {
    method: "DELETE",
  });
  await parseJson(res);
}

export async function claimDrops(): Promise<void> {
  const res = await fetch("/api/actions/claim-drops", { method: "POST" });
  await parseJson(res);
}

export async function shutdownMiner(): Promise<void> {
  const res = await fetch("/api/actions/shutdown", { method: "POST" });
  await parseJson(res);
}

export function sortStreamers(streamers: StatusSnapshot["streamers"]) {
  return [...streamers].sort((a, b) => {
    if (a.online !== b.online) return a.online ? -1 : 1;
    if (a.drops_active !== b.drops_active) return a.drops_active ? -1 : 1;
    return b.points - a.points;
  });
}

export function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function formatPoints(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function formatDateInput(d: Date): string {
  return d.toISOString().slice(0, 10);
}
