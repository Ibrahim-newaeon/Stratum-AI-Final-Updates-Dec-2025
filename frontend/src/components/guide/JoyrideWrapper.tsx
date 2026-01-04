import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react'
import Joyride, { CallBackProps, STATUS, ACTIONS, EVENTS } from 'react-joyride'
import {
  TourRole,
  TourConfig,
  getTourByRole,
  getAllTours,
  hasTourCompleted,
  markTourCompleted,
  resetTour,
  resetAllTours,
} from './tours'

interface JoyrideContextType {
  startTour: (role?: TourRole) => void
  startTourById: (tourId: string) => void
  skipTour: () => void
  resetCurrentTour: () => void
  resetAllTours: () => void
  isRunning: boolean
  currentTour: TourConfig | null
  availableTours: TourConfig[]
  completedTours: string[]
}

const JoyrideContext = createContext<JoyrideContextType | undefined>(undefined)

export function useJoyride() {
  const context = useContext(JoyrideContext)
  if (!context) {
    throw new Error('useJoyride must be used within a JoyrideProvider')
  }
  return context
}

interface JoyrideProviderProps {
  children: ReactNode
  userRole?: TourRole
  autoStart?: boolean
}

export function JoyrideProvider({ children, userRole = 'general', autoStart = false }: JoyrideProviderProps) {
  const [run, setRun] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [currentTour, setCurrentTour] = useState<TourConfig | null>(null)
  const [completedTours, setCompletedTours] = useState<string[]>([])

  // Load completed tours from localStorage
  useEffect(() => {
    const allTours = getAllTours()
    const completed = allTours
      .filter(tour => hasTourCompleted(tour.id))
      .map(tour => tour.id)
    setCompletedTours(completed)
  }, [])

  // Auto-start tour for new users
  useEffect(() => {
    if (autoStart && userRole) {
      const tour = getTourByRole(userRole)
      if (!hasTourCompleted(tour.id)) {
        const timer = setTimeout(() => {
          setCurrentTour(tour)
          setStepIndex(0)
          setRun(true)
        }, 1500)
        return () => clearTimeout(timer)
      }
    }
  }, [autoStart, userRole])

  const handleJoyrideCallback = useCallback((data: CallBackProps) => {
    const { action, index, status, type } = data

    if ([EVENTS.STEP_AFTER, EVENTS.TARGET_NOT_FOUND].includes(type as typeof EVENTS.STEP_AFTER)) {
      setStepIndex(index + (action === ACTIONS.PREV ? -1 : 1))
    }

    if ([STATUS.FINISHED, STATUS.SKIPPED].includes(status as typeof STATUS.FINISHED)) {
      setRun(false)
      setStepIndex(0)
      if (currentTour) {
        markTourCompleted(currentTour.id)
        setCompletedTours(prev => [...prev, currentTour.id])
      }
    }
  }, [currentTour])

  const startTour = useCallback((role: TourRole = userRole) => {
    const tour = getTourByRole(role)
    setCurrentTour(tour)
    setStepIndex(0)
    setRun(true)
  }, [userRole])

  const startTourById = useCallback((tourId: string) => {
    const tour = getAllTours().find(t => t.id === tourId)
    if (tour) {
      setCurrentTour(tour)
      setStepIndex(0)
      setRun(true)
    }
  }, [])

  const skipTour = useCallback(() => {
    setRun(false)
    setStepIndex(0)
    if (currentTour) {
      markTourCompleted(currentTour.id)
      setCompletedTours(prev => [...prev, currentTour.id])
    }
  }, [currentTour])

  const resetCurrentTour = useCallback(() => {
    if (currentTour) {
      resetTour(currentTour.id)
      setCompletedTours(prev => prev.filter(id => id !== currentTour.id))
    }
  }, [currentTour])

  const handleResetAllTours = useCallback(() => {
    resetAllTours()
    setCompletedTours([])
  }, [])

  return (
    <JoyrideContext.Provider
      value={{
        startTour,
        startTourById,
        skipTour,
        resetCurrentTour,
        resetAllTours: handleResetAllTours,
        isRunning: run,
        currentTour,
        availableTours: getAllTours(),
        completedTours,
      }}
    >
      {children}
      {currentTour && (
        <Joyride
          steps={currentTour.steps}
          run={run}
          stepIndex={stepIndex}
          continuous
          showProgress
          showSkipButton
          scrollToFirstStep
          spotlightClicks
          callback={handleJoyrideCallback}
          styles={{
            options: {
              primaryColor: '#a855f7', // Stratum purple
              zIndex: 10000,
              backgroundColor: '#0A0A0A',
              textColor: '#ffffff',
              overlayColor: 'rgba(0, 0, 0, 0.75)',
            },
            tooltip: {
              borderRadius: '1rem',
              padding: '1.5rem',
              backgroundColor: '#121212',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            },
            tooltipContent: {
              padding: 0,
            },
            buttonNext: {
              borderRadius: '0.5rem',
              padding: '0.75rem 1.5rem',
              backgroundColor: '#a855f7',
              fontWeight: 500,
            },
            buttonBack: {
              borderRadius: '0.5rem',
              marginRight: '0.75rem',
              color: '#9ca3af',
            },
            buttonSkip: {
              borderRadius: '0.5rem',
              color: '#6b7280',
            },
            spotlight: {
              borderRadius: '0.75rem',
            },
            beacon: {
              display: 'none',
            },
          }}
          floaterProps={{
            styles: {
              floater: {
                filter: 'drop-shadow(0 4px 20px rgba(168, 85, 247, 0.3))',
              },
            },
          }}
          locale={{
            back: 'Back',
            close: 'Close',
            last: 'Complete Tour',
            next: 'Next',
            open: 'Start Tour',
            skip: 'Skip Tour',
          }}
        />
      )}
    </JoyrideContext.Provider>
  )
}

export default JoyrideProvider
