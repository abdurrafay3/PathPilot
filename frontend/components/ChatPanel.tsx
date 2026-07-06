"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Navigation, MapPin, Clock, AlertCircle } from "lucide-react";
import type { RouteHistoryItem } from "@/lib/types";

interface ChatPanelProps {
  history: RouteHistoryItem[];
  isPending: boolean;
  pendingPrompt: string | null;
  errorMessage: string | null;
  originLabel: string;
  onSendPrompt: (prompt: string) => void;
}

export function ChatPanel({
  history,
  isPending,
  pendingPrompt,
  errorMessage,
  originLabel,
  onSendPrompt,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, isPending, pendingPrompt]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isPending) return;
    onSendPrompt(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col border-l border-slate-800 bg-slate-900">
      <div className="shrink-0 border-b border-slate-800 bg-slate-950/60 px-5 py-4 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Navigation className="h-5 w-5 text-cyan-400" />
          <span className="text-lg font-bold tracking-tight text-white">Path Pilot</span>
        </div>
        <p className="mt-0.5 text-xs text-slate-500">Your precision co-pilot</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-col gap-5">
          {history.length === 0 && !isPending && !errorMessage && (
            <div className="flex flex-col items-center gap-3 py-16 text-center text-slate-500">
              <Navigation className="h-10 w-10 text-slate-700" />
              <p className="text-sm leading-relaxed">
                Ready to plan your next route.
                <br />
                Where are we heading?
              </p>
            </div>
          )}

          {history.map((item) => (
            <div key={item.id} className="flex flex-col gap-2">
              <div className="flex justify-end">
                <div
                  data-testid={`user-message-${item.id}`}
                  className="max-w-[85%] rounded-2xl rounded-tr-sm bg-slate-700 px-4 py-3 text-sm text-slate-100 shadow-sm"
                >
                  {item.prompt}
                </div>
              </div>

              <div className="flex justify-start">
                <div
                  data-testid={`assistant-message-${item.id}`}
                  className="max-w-[90%] rounded-2xl rounded-tl-sm border border-slate-700 bg-slate-800 px-4 py-3 shadow-sm"
                >
                  {item.status === "valid_route_found" ? (
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
                          Route Found
                        </span>
                        <span className="text-xs text-slate-500">
                          {new Date(item.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                      <div className="flex flex-col gap-1.5 text-sm">
                        {item.waypoint_name && (
                          <div className="flex items-center gap-2 text-slate-200">
                            <MapPin className="h-3.5 w-3.5 shrink-0 text-cyan-400" />
                            <span className="font-medium">{item.waypoint_name}</span>
                          </div>
                        )}
                        {item.duration_minutes != null && (
                          <div className="flex items-center gap-2 text-slate-400">
                            <Clock className="h-3.5 w-3.5 shrink-0" />
                            <span>{item.duration_minutes} min total</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <span className="inline-flex w-fit items-center rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-semibold text-red-400 ring-1 ring-inset ring-red-500/20">
                        No Route Found
                      </span>
                      <p className="text-sm text-slate-400">
                        No route matching those constraints could be found. Try adjusting your request.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {isPending && pendingPrompt && (
            <div className="flex flex-col gap-2">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-slate-700/60 px-4 py-3 text-sm text-slate-300 opacity-70 shadow-sm">
                  {pendingPrompt}
                </div>
              </div>
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-slate-700 bg-slate-800 px-5 py-4 shadow-sm">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400 [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400 [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400" />
                </div>
              </div>
            </div>
          )}

          {errorMessage && !isPending && (
            <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="shrink-0 border-t border-slate-800 bg-slate-950/60 p-4 backdrop-blur-sm">
        <div className="mb-3 flex items-center justify-between gap-3 rounded-xl border border-slate-700 bg-slate-800 px-4 py-3">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-slate-500">Origin</p>
            <p className="text-sm text-slate-100">{originLabel}</p>
          </div>
          <p className="text-[10px] text-slate-600">Uses browser location if allowed</p>
        </div>
        <div className="relative flex items-end gap-2">
          <textarea
            data-testid="input-prompt"
            placeholder="Plan a route (e.g. stop at a pharmacy on the way from Central to Causeway Bay)..."
            className="min-h-[60px] max-h-[160px] w-full resize-none rounded-xl border border-slate-700 bg-slate-800 py-3 pl-4 pr-12 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 disabled:opacity-50"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isPending}
            rows={2}
          />
          <button
            data-testid="button-send"
            onClick={handleSend}
            disabled={!input.trim() || isPending}
            className="absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-cyan-500 text-white shadow-md transition hover:bg-cyan-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
        <p className="mt-2 text-center text-[10px] uppercase tracking-widest text-slate-600">
          Enter to send · Shift+Enter for newline
        </p>
      </div>
    </div>
  );
}
