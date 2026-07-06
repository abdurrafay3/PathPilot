import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { MapPanel } from '@/components/MapPanel';
import { ChatPanel } from '@/components/ChatPanel';
import { usePlanRoute, useGetRouteHistory, useHealthCheck, getGetRouteHistoryQueryKey } from '@workspace/api-client-react';
import type { ConstraintValidatorAgentOutput } from '@workspace/api-client-react';
import { useToast } from '@/hooks/use-toast';
import { Activity } from 'lucide-react';

export default function Home() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  
  const [currentRoute, setCurrentRoute] = useState<ConstraintValidatorAgentOutput | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);

  const { data: history = [], isLoading: isLoadingHistory } = useGetRouteHistory();
  const { data: healthData } = useHealthCheck({ query: { refetchInterval: 30000 } });
  
  const planRoute = usePlanRoute({
    mutation: {
      onSuccess: (result) => {
        setCurrentRoute(result);
        queryClient.invalidateQueries({ queryKey: getGetRouteHistoryQueryKey() });
        setPendingPrompt(null);
      },
      onError: (error) => {
        toast({
          title: "Error planning route",
          description: error.error || "An unexpected error occurred",
          variant: "destructive"
        });
        setPendingPrompt(null);
      }
    }
  });

  const handleSendPrompt = (prompt: string) => {
    setPendingPrompt(prompt);
    planRoute.mutate({ data: { prompt } });
  };

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-background font-sans relative">
      <div className="w-full md:w-[60%] h-full relative">
        <MapPanel route={currentRoute} />
        {healthData && (
          <div className="absolute top-4 left-4 z-[400] flex items-center gap-2 bg-background/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-border shadow-sm text-xs font-medium text-muted-foreground">
            <Activity className={`w-3.5 h-3.5 ${healthData.status === 'ok' ? 'text-green-500' : 'text-yellow-500'}`} />
            System {healthData.status}
          </div>
        )}
      </div>
      <div className="w-full md:w-[40%] h-full shadow-2xl z-10 hidden md:block">
        <ChatPanel 
          history={history} 
          isPending={planRoute.isPending} 
          onSendPrompt={handleSendPrompt}
          pendingPrompt={pendingPrompt}
        />
      </div>
    </div>
  );
}
