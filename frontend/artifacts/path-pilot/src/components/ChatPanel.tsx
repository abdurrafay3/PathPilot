import { useState, useRef, useEffect } from 'react';
import { Send, MapPin, Navigation, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import type { RouteHistoryItem } from '@workspace/api-client-react';

interface ChatPanelProps {
  history: RouteHistoryItem[];
  isPending: boolean;
  onSendPrompt: (prompt: string) => void;
  pendingPrompt: string | null;
}

export function ChatPanel({ history, isPending, onSendPrompt, pendingPrompt }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when history or pending state changes
    const scrollContainer = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  }, [history, isPending, pendingPrompt]);

  const handleSend = () => {
    if (input.trim() && !isPending) {
      onSendPrompt(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-card border-l border-border relative">
      <div className="p-4 border-b border-border bg-background/50 backdrop-blur-sm">
        <h2 className="text-xl font-bold tracking-tight text-primary flex items-center gap-2">
          <Navigation className="w-5 h-5" />
          Path Pilot
        </h2>
        <p className="text-sm text-muted-foreground">Your precision co-pilot</p>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="flex flex-col gap-6 max-w-2xl mx-auto w-full pb-4">
          {history.length === 0 && !isPending && (
            <div className="text-center py-12 text-muted-foreground flex flex-col items-center gap-3">
              <Navigation className="w-12 h-12 text-border" />
              <p>Ready to plan your next route.<br/>Where are we heading?</p>
            </div>
          )}

          {history.map((item) => (
            <div key={item.id} className="flex flex-col gap-3">
              {/* User Prompt */}
              <div className="flex justify-end">
                <div className="bg-secondary text-secondary-foreground px-4 py-3 rounded-2xl rounded-tr-sm max-w-[85%] text-sm shadow-sm">
                  {item.prompt}
                </div>
              </div>

              {/* Assistant Response */}
              <div className="flex justify-start">
                <div className="bg-background border border-border px-4 py-3 rounded-2xl rounded-tl-sm max-w-[90%] flex flex-col gap-3 shadow-sm">
                  {item.status === 'valid_route_found' ? (
                    <>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/20">Route Found</Badge>
                        <span className="text-xs text-muted-foreground">
                          {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className="grid gap-2 text-sm">
                        {item.waypoint_name && (
                          <div className="flex items-center gap-2 text-foreground">
                            <MapPin className="w-4 h-4 text-primary shrink-0" />
                            <span className="font-medium">{item.waypoint_name}</span>
                          </div>
                        )}
                        {item.duration_minutes && (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="w-4 h-4 shrink-0" />
                            <span>Total Duration: {item.duration_minutes} min</span>
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20">No Route</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        I couldn't find a route that meets those constraints. Please try adjusting your request.
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Pending State */}
          {isPending && pendingPrompt && (
            <div className="flex flex-col gap-3">
              <div className="flex justify-end">
                <div className="bg-secondary text-secondary-foreground px-4 py-3 rounded-2xl rounded-tr-sm max-w-[85%] text-sm opacity-70">
                  {pendingPrompt}
                </div>
              </div>
              <div className="flex justify-start">
                <div className="bg-background border border-border px-4 py-4 rounded-2xl rounded-tl-sm w-20 flex items-center justify-center gap-1.5 shadow-sm">
                  <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-4 bg-background border-t border-border">
        <div className="relative max-w-2xl mx-auto flex items-end gap-2">
          <Textarea
            placeholder="Plan a route (e.g. 'I want to stop by a highly rated coffee shop on my way')..."
            className="min-h-[60px] max-h-[160px] resize-none bg-card border-border pr-12 text-sm py-3"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isPending}
          />
          <Button 
            size="icon" 
            className="absolute right-2 bottom-2 h-8 w-8 rounded-full shadow-md transition-transform active:scale-95"
            onClick={handleSend}
            disabled={!input.trim() || isPending}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <div className="text-center mt-2">
          <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">Press Enter to send, Shift+Enter for newline</span>
        </div>
      </div>
    </div>
  );
}
