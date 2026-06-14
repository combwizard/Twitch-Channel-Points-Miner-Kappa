import {
  claimDrops,
  formatPoints,
  formatUptime,
  shutdownMiner,
} from "../api";
import type { StatusSnapshot } from "../types";

interface HeaderProps {
  status: StatusSnapshot | null;
  connected: boolean;
}

export function Header({ status, connected }: HeaderProps) {
  const handleClaim = async () => {
    try {
      await claimDrops();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Claim failed");
    }
  };

  const handleStop = async () => {
    if (!confirm("Stop the miner? The process will exit.")) return;
    try {
      await shutdownMiner();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Shutdown failed");
    }
  };

  return (
    <header className="flex flex-col gap-4 border-b border-twitch-border pb-6 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Channel Points Miner Kappa</h1>
        <p className="mt-1 text-sm text-twitch-muted">
          {status?.username ?? "…"}
          {status && (
            <>
              {" · "}
              Session {formatUptime(status.uptime_seconds)}
              {" · "}
              <span className={connected ? "text-emerald-400" : "text-amber-400"}>
                {connected ? "Live" : "Reconnecting…"}
              </span>
              {status.ws_connected === false && " · WS disconnected"}
            </>
          )}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {status && (
          <div className="rounded-lg bg-twitch-panel px-4 py-2 text-sm">
            <span className="text-twitch-muted">Session gain </span>
            <span className="font-semibold text-twitch-purple">
              +{formatPoints(status.session_points_gained)}
            </span>
          </div>
        )}
        <button
          type="button"
          onClick={handleClaim}
          className="rounded-lg bg-twitch-panel px-4 py-2 text-sm font-medium transition hover:bg-twitch-border"
        >
          Claim drops
        </button>
        <button
          type="button"
          onClick={handleStop}
          className="rounded-lg bg-red-900/60 px-4 py-2 text-sm font-medium text-red-100 transition hover:bg-red-800/80"
        >
          Stop miner
        </button>
      </div>
    </header>
  );
}
