/**
 * Keyboard Shortcuts System
 *
 * Global keyboard shortcuts for power users
 */

import { useEffect, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJoyride } from '@/components/guide/JoyrideWrapper'

interface ShortcutAction {
  key: string
  ctrl?: boolean
  alt?: boolean
  shift?: boolean
  description: string
  action: () => void
  category: 'navigation' | 'actions' | 'help'
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean
}

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}) {
  const { enabled = true } = options
  const navigate = useNavigate()
  const { startTour } = useJoyride()
  const [showHelp, setShowHelp] = useState(false)

  // Define shortcuts
  const shortcuts: ShortcutAction[] = [
    // Navigation
    {
      key: 'g',
      description: 'Go to Overview',
      action: () => navigate('/dashboard/overview'),
      category: 'navigation',
    },
    {
      key: 'c',
      description: 'Go to Campaigns',
      action: () => navigate('/dashboard/campaigns'),
      category: 'navigation',
    },
    {
      key: 's',
      description: 'Go to Settings',
      action: () => navigate('/dashboard/settings'),
      category: 'navigation',
    },
    {
      key: 'e',
      description: 'Go to EMQ Dashboard',
      action: () => navigate('/dashboard/emq-dashboard'),
      category: 'navigation',
    },
    {
      key: 'a',
      description: 'Go to Assets',
      action: () => navigate('/dashboard/assets'),
      category: 'navigation',
    },
    {
      key: 'r',
      description: 'Go to Rules',
      action: () => navigate('/dashboard/rules'),
      category: 'navigation',
    },
    // Actions
    {
      key: 'n',
      ctrl: true,
      description: 'New Campaign',
      action: () => {
        // Get current tenant context if available
        const match = window.location.pathname.match(/\/app\/(\d+)/)
        if (match) {
          navigate(`/app/${match[1]}/campaigns/new`)
        }
      },
      category: 'actions',
    },
    {
      key: 'f',
      ctrl: true,
      description: 'Search',
      action: () => {
        const searchInput = document.querySelector('input[type="search"], input[placeholder*="Search"]') as HTMLInputElement
        if (searchInput) {
          searchInput.focus()
        }
      },
      category: 'actions',
    },
    {
      key: 'Escape',
      description: 'Close modal/dialog',
      action: () => {
        // Trigger escape key on document to close any open modals
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      },
      category: 'actions',
    },
    // Help
    {
      key: '?',
      shift: true,
      description: 'Show keyboard shortcuts',
      action: () => setShowHelp((prev) => !prev),
      category: 'help',
    },
    {
      key: 't',
      description: 'Start onboarding tour',
      action: () => startTour(),
      category: 'help',
    },
  ]

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return

      // Don't trigger shortcuts when typing in inputs
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // Only allow Escape in inputs
        if (event.key !== 'Escape') return
      }

      // Find matching shortcut
      const shortcut = shortcuts.find((s) => {
        const keyMatch = s.key.toLowerCase() === event.key.toLowerCase()
        const ctrlMatch = s.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey
        const altMatch = s.alt ? event.altKey : !event.altKey
        const shiftMatch = s.shift ? event.shiftKey : !event.shiftKey

        return keyMatch && ctrlMatch && altMatch && shiftMatch
      })

      if (shortcut) {
        event.preventDefault()
        shortcut.action()
      }
    },
    [enabled, shortcuts]
  )

  useEffect(() => {
    if (enabled) {
      window.addEventListener('keydown', handleKeyDown)
      return () => window.removeEventListener('keydown', handleKeyDown)
    }
  }, [enabled, handleKeyDown])

  return {
    shortcuts,
    showHelp,
    setShowHelp,
  }
}

/**
 * Keyboard Shortcuts Help Modal Component
 */
export function KeyboardShortcutsHelp({
  isOpen,
  onClose,
}: {
  isOpen: boolean
  onClose: () => void
}) {
  const { shortcuts } = useKeyboardShortcuts({ enabled: false })

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const categories = {
    navigation: 'Navigation',
    actions: 'Actions',
    help: 'Help',
  }

  const groupedShortcuts = shortcuts.reduce(
    (acc, shortcut) => {
      if (!acc[shortcut.category]) {
        acc[shortcut.category] = []
      }
      acc[shortcut.category].push(shortcut)
      return acc
    },
    {} as Record<string, ShortcutAction[]>
  )

  const formatKey = (shortcut: ShortcutAction) => {
    const parts = []
    if (shortcut.ctrl) parts.push('Ctrl')
    if (shortcut.alt) parts.push('Alt')
    if (shortcut.shift) parts.push('Shift')
    parts.push(shortcut.key.toUpperCase())
    return parts.join(' + ')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface-secondary border border-white/10 rounded-2xl p-6 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">Keyboard Shortcuts</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/5 text-text-muted hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-6">
          {Object.entries(categories).map(([category, label]) => (
            <div key={category}>
              <h3 className="text-sm font-medium text-text-muted mb-3">{label}</h3>
              <div className="space-y-2">
                {groupedShortcuts[category]?.map((shortcut, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between py-2"
                  >
                    <span className="text-white">{shortcut.description}</span>
                    <kbd className="px-2 py-1 rounded bg-surface-tertiary border border-white/10 text-text-muted text-sm font-mono">
                      {formatKey(shortcut)}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t border-white/10">
          <p className="text-sm text-text-muted text-center">
            Press <kbd className="px-1 py-0.5 rounded bg-surface-tertiary text-xs">?</kbd> anytime to show this help
          </p>
        </div>
      </div>
    </div>
  )
}

export default useKeyboardShortcuts
