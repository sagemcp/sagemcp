import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { poolApi } from '@/utils/api'
import type { PoolEntry, PoolSummary } from '@/types'

export function usePoolEntries(tenantSlug?: string) {
  return useQuery<PoolEntry[]>({
    queryKey: ['pool-entries', tenantSlug],
    queryFn: () => poolApi.list(tenantSlug).then(res => res.data),
    refetchInterval: 5000,
  })
}

export function usePoolSummary() {
  return useQuery<PoolSummary>({
    queryKey: ['pool-summary'],
    queryFn: () => poolApi.summary().then(res => res.data),
    refetchInterval: 5000,
  })
}

export function useEvictPoolEntry() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantSlug, connectorId }: { tenantSlug: string; connectorId: string }) =>
      poolApi.evict(tenantSlug, connectorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pool-entries'] })
      queryClient.invalidateQueries({ queryKey: ['pool-summary'] })
    },
  })
}

export function useEvictIdle() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (idleSeconds: number) => poolApi.evictIdle(idleSeconds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pool-entries'] })
      queryClient.invalidateQueries({ queryKey: ['pool-summary'] })
    },
  })
}
