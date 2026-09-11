import { useEffect } from 'react'
import { apiClient } from '../services/apiClient'

const HEARTBEAT_MS = 15_000

/**
 * Keeps the packaged launcher's idle watchdog fresh while a tab is open.
 *
 * Every HTTP request already counts as activity, but an otherwise idle
 * dashboard issues none; this periodic `/api/health` ping guarantees the
 * auto-shutdown only fires after the tab is actually closed. Errors are
 * ignored (the server may be winding down).
 */
export function useHeartbeat(intervalMs = HEARTBEAT_MS): void {
  useEffect(() => {
    const ping = () => {
      void apiClient.health().catch(() => undefined)
    }
    const timer = window.setInterval(ping, intervalMs)
    return () => window.clearInterval(timer)
  }, [intervalMs])
}
