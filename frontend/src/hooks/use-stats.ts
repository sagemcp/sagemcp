import { useQuery } from '@tanstack/react-query'
import { statsApi } from '@/utils/api'
import type { PlatformStats } from '@/types'

export function useStats() {
  return useQuery<PlatformStats>({
    queryKey: ['platform-stats'],
    queryFn: () => statsApi.get().then(res => res.data),
    refetchInterval: 5000,
  })
}
