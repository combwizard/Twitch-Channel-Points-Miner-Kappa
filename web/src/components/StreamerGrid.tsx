import { useState } from "react";
import { addStreamer, formatPoints, removeStreamer, sortStreamers } from "../api";
import type { StreamerStatus } from "../types";

interface StreamerGridProps {
  streamers: StreamerStatus[];
  selected: string | null;
  onSelect: (username: string) => void;
}

export function StreamerGrid({ streamers, selected, onSelect }: StreamerGridProps) {
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const sorted = sortStreamers(streamers);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setBusy(true);
    try {
      const result = await addStreamer(name);
      setNewName("");
      onSelect(name.toLowerCase());
      if (result.warning) {
        alert(result.warning);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add streamer");
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (username: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Remove ${username} from the miner?`)) return;
    setBusy(true);
    try {
      await removeStreamer(username);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to remove streamer");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-medium">Streamers</h2>
        <form onSubmit={handleAdd} className="flex gap-2">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Add streamer…"
            disabled={busy}
            className="rounded-lg border border-twitch-border bg-twitch-panel px-3 py-2 text-sm outline-none focus:border-twitch-purple"
          />
          <button
            type="submit"
            disabled={busy || !newName.trim()}
            className="rounded-lg bg-twitch-purple px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            Add
          </button>
        </form>
      </div>

      {sorted.length === 0 ? (
        <p className="text-sm text-twitch-muted">No streamers configured.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sorted.map((s) => (
            <button
              key={s.username}
              type="button"
              onClick={() => onSelect(s.username)}
              className={`group relative rounded-xl border p-4 text-left transition ${
                selected === s.username
                  ? "border-twitch-purple bg-twitch-purple/10"
                  : "border-twitch-border bg-twitch-panel hover:border-twitch-muted"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-medium">{s.username}</span>
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${
                    s.online ? "bg-emerald-400" : "bg-zinc-600"
                  }`}
                  title={s.online ? "Online" : "Offline"}
                />
              </div>
              <p className="mt-2 text-xl font-semibold">{formatPoints(s.points)}</p>
              {s.session_gained !== 0 && (
                <p className="text-xs text-emerald-400">+{formatPoints(s.session_gained)} session</p>
              )}
              {s.online && s.title && (
                <p className="mt-2 truncate text-xs text-twitch-muted">{s.title}</p>
              )}
              {s.game && <p className="truncate text-xs text-twitch-muted">{s.game}</p>}
              <div className="mt-2 flex flex-wrap gap-1">
                {s.drops_active && (
                  <span className="rounded bg-blue-900/50 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-blue-200">
                    Drops
                  </span>
                )}
                {s.watch_streak && (
                  <span className="rounded bg-amber-900/50 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-200">
                    Streak
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={(e) => handleRemove(s.username, e)}
                className="absolute right-2 top-2 hidden rounded p-1 text-xs text-twitch-muted hover:bg-red-900/40 hover:text-red-200 group-hover:block"
                title="Remove"
              >
                ✕
              </button>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
