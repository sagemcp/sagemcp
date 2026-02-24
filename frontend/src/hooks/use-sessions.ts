import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sessionsApi } from '@/utils/api'
import type { SessionInfo } from '@/types'

export function useSessions(tenantSlug?: string) {
  return useQuery<SessionInfo[]>({
    queryKey: ['sessions', tenantSlug],
    queryFn: () => sessionsApi.list(tenantSlug).then(res => res.data),
    refetchInterval: 10000,
  })
}

export function useTerminateSession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sessionId: string) => sessionsApi.delete(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
}
