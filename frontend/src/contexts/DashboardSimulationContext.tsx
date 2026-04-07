/**
 * Dashboard Simulation Context
 * Shared context that provides live simulation data to all Custom Dashboard widgets.
 * This avoids duplicate simulation calls and ensures data consistency across widgets.
 */

import { createContext, useContext, type ReactNode } from 'react'
import { useLiveSimulation } from '@/lib/liveSimulation'

type SimulationData = ReturnType<typeof useLiveSimulation>

const DashboardSimulationContext = createContext<SimulationData | null>(null)

interface DashboardSimulationProviderProps {
  children: ReactNode
  refreshInterval?: number
}

export function DashboardSimulationProvider({
  children,
  refreshInterval = 10000,
}: DashboardSimulationProviderProps) {
  const simulation = useLiveSimulation(refreshInterval)

  return (
    <DashboardSimulationContext.Provider value={simulation}>
      {children}
    </DashboardSimulationContext.Provider>
  )
}

/**
 * Access shared simulation data from the DashboardSimulationProvider.
 * Must be used inside <DashboardSimulationProvider>.
 */
export function useDashboardSimulation(): SimulationData {
  const ctx = useContext(DashboardSimulationContext)
  if (!ctx) {
    throw new Error(
      'useDashboardSimulation must be used inside <DashboardSimulationProvider>'
    )
  }
  return ctx
}
