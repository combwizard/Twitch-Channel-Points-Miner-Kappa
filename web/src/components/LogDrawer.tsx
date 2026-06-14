import { useEffect, useRef, useState } from "react";
import { fetchLogs } from "../api";

function colorizeLine(line: string): string {
  if (/\bERROR\b/i.test(line)) return "text-red-400";
  if (/\bWARNING\b/i.test(line)) return "text-amber-400";
  if (/\bDEBUG\b/i.test(line)) return "text-zinc-500";
  return "text-zinc-300";
}

export function LogDrawer() {
  const [open, setOpen] = useState(false);
  const [lines, setLines] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const sinceRef = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const poll = async () => {
      try {
        const { text, next_since } = await fetchLogs(sinceRef.current);
        sinceRef.current = next_since;
        if (text) {
          const newLines = text.split("\n").filter(Boolean);
          setLines((prev) => [...prev, ...newLines].slice(-500));
        }
      } catch {
        /* ignore transient errors */
      }
    };

    poll();
    const id = window.setInterval(poll, 2000);
    return () => window.clearInterval(id);
  }, [open]);

  useEffect(() => {
    if (open && autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [lines, open, autoScroll]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-4 right-4 z-20 rounded-full bg-twitch-purple px-5 py-2.5 text-sm font-medium shadow-lg transition hover:brightness-110"
      >
        {open ? "Hide logs" : "Show logs"}
      </button>

      {open && (
        <div className="fixed inset-x-0 bottom-0 z-10 flex max-h-[40vh] flex-col border-t border-twitch-border bg-twitch-dark/95 backdrop-blur">
          <div className="flex items-center justify-between border-b border-twitch-border px-4 py-2">
            <span className="text-sm font-medium">Logs</span>
            <label className="flex items-center gap-2 text-xs text-twitch-muted">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
          </div>
          <pre className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed">
            {lines.length === 0 ? (
              <span className="text-twitch-muted">Waiting for log output…</span>
            ) : (
              lines.map((line, i) => (
                <div key={`${i}-${line.slice(0, 24)}`} className={colorizeLine(line)}>
                  {line}
                </div>
              ))
            )}
            <div ref={bottomRef} />
          </pre>
        </div>
      )}
    </>
  );
}
