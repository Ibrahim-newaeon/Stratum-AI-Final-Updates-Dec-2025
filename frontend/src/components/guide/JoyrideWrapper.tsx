import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import Joyride, { CallBackProps, STATUS, Step, ACTIONS, EVENTS } from 'react-joyride'
import { useTranslation } from 'react-i18next'

interface JoyrideContextType {
  startTour: () => void
  skipTour: () => void
  isRunning: boolean
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
}

export function JoyrideProvider({ children }: JoyrideProviderProps) {
  const { t } = useTranslation()
  const [run, setRun] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)

  // Check if user has completed the tour before
  const hasCompletedTour = localStorage.getItem('stratum_tour_completed') === 'true'

  // Define tour steps
  const steps: Step[] = [
    {
      target: 'body',
      content: (
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">{t('guide.welcome.title')}</h3>
          <p className="text-muted-foreground">{t('guide.welcome.content')}</p>
        </div>
      ),
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '#kpi-tiles',
      content: (
        <div>
          <h3 className="text-lg font-semibold mb-2">{t('guide.kpiTiles.title')}</h3>
          <p className="text-muted-foreground">{t('guide.kpiTiles.content')}</p>
        </div>
      ),
      placement: 'bottom',
    },
    {
      target: '#simulator-widget',
      content: (
        <div>
          <h3 className="text-lg font-semibold mb-2">{t('guide.simulator.title')}</h3>
          <p className="text-muted-foreground">{t('guide.simulator.content')}</p>
        </div>
      ),
      placement: 'left',
    },
    {
      target: '#sidebar-nav',
      content: (
        <div>
          <h3 className="text-lg font-semibold mb-2">{t('guide.navigation.title')}</h3>
          <p className="text-muted-foreground">{t('guide.navigation.content')}</p>
        </div>
      ),
      placement: 'right',
    },
  ]

  const handleJoyrideCallback = useCallback((data: CallBackProps) => {
    const { action, index, status, type } = data

    if ([EVENTS.STEP_AFTER, EVENTS.TARGET_NOT_FOUND].includes(type as any)) {
      // Update step index
      setStepIndex(index + (action === ACTIONS.PREV ? -1 : 1))
    }

    if ([STATUS.FINISHED, STATUS.SKIPPED].includes(status as any)) {
      // Tour completed or skipped
      setRun(false)
      setStepIndex(0)
      localStorage.setItem('stratum_tour_completed', 'true')
    }
  }, [])

  const startTour = useCallback(() => {
    setStepIndex(0)
    setRun(true)
  }, [])

  const skipTour = useCallback(() => {
    setRun(false)
    setStepIndex(0)
    localStorage.setItem('stratum_tour_completed', 'true')
  }, [])

  // Auto-start tour for new users (after a short delay)
  useState(() => {
    if (!hasCompletedTour) {
      const timer = setTimeout(() => {
        setRun(true)
      }, 1000)
      return () => clearTimeout(timer)
    }
  })

  return (
    <JoyrideContext.Provider value={{ startTour, skipTour, isRunning: run }}>
      {children}
      <Joyride
        steps={steps}
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
            primaryColor: '#0ea5e9',
            zIndex: 10000,
          },
          tooltip: {
            borderRadius: '0.75rem',
            padding: '1rem',
          },
          buttonNext: {
            borderRadius: '0.5rem',
            padding: '0.5rem 1rem',
          },
          buttonBack: {
            borderRadius: '0.5rem',
            marginRight: '0.5rem',
          },
          buttonSkip: {
            borderRadius: '0.5rem',
          },
        }}
        locale={{
          back: 'Back',
          close: 'Close',
          last: 'Finish',
          next: 'Next',
          open: 'Open',
          skip: 'Skip',
        }}
      />
    </JoyrideContext.Provider>
  )
}

export default JoyrideProvider
