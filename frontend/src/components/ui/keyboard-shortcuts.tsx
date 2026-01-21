/**
 * Keyboard Shortcuts Modal
 *
 * Reference guide for all available keyboard shortcuts
 * with categorized layout and visual key representations.
 */

import * as React from 'react'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Keyboard, Command } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Shortcut {
  keys: string[]
  description: string
}

interface ShortcutCategory {
  name: string
  shortcuts: Shortcut[]
}

const SHORTCUTS: ShortcutCategory[] = [
  {
    name: 'Global',
    shortcuts: [
      { keys: ['Cmd', 'K'], description: 'Open command palette' },
      { keys: ['Cmd', '/'], description: 'Open keyboard shortcuts' },
      { keys: ['Esc'], description: 'Close modal / Cancel' },
      { keys: ['?'], description: 'Show help' },
    ],
  },
  {
    name: 'Navigation',
    shortcuts: [
      { keys: ['G', 'D'], description: 'Go to Dashboard' },
      { keys: ['G', 'C'], description: 'Go to Campaigns' },
      { keys: ['G', 'P'], description: 'Go to CDP Profiles' },
      { keys: ['G', 'S'], description: 'Go to Settings' },
      { keys: ['G', 'R'], description: 'Go to Rules' },
      { keys: ['G', 'B'], description: 'Go to Benchmarks' },
    ],
  },
  {
    name: 'Actions',
    shortcuts: [
      { keys: ['N'], description: 'Create new (context-aware)' },
      { keys: ['E'], description: 'Edit selected item' },
      { keys: ['D'], description: 'Delete selected item' },
      { keys: ['Cmd', 'S'], description: 'Save changes' },
      { keys: ['Cmd', 'Enter'], description: 'Submit form' },
    ],
  },
  {
    name: 'Tables & Lists',
    shortcuts: [
      { keys: ['J'], description: 'Move down' },
      { keys: ['K'], description: 'Move up' },
      { keys: ['Enter'], description: 'Open selected' },
      { keys: ['Cmd', 'A'], description: 'Select all' },
      { keys: ['Space'], description: 'Toggle selection' },
    ],
  },
  {
    name: 'Search & Filter',
    shortcuts: [
      { keys: ['/'], description: 'Focus search input' },
      { keys: ['Cmd', 'F'], description: 'Find in page' },
      { keys: ['Tab'], description: 'Next filter' },
      { keys: ['Shift', 'Tab'], description: 'Previous filter' },
    ],
  },
]

interface KeyProps {
  children: React.ReactNode
  large?: boolean
}

function Key({ children, large }: KeyProps) {
  const isSpecialKey = ['Cmd', 'Ctrl', 'Shift', 'Alt', 'Enter', 'Esc', 'Tab', 'Space'].includes(children as string)

  return (
    <kbd
      className={cn(
        "inline-flex items-center justify-center rounded-md border bg-muted font-mono text-xs font-medium shadow-sm",
        large ? "min-w-[2.5rem] h-8 px-2" : "min-w-[1.75rem] h-6 px-1.5",
        isSpecialKey && "text-muted-foreground"
      )}
    >
      {children === 'Cmd' ? (
        <Command className="h-3 w-3" />
      ) : children === 'Enter' ? (
        '↵'
      ) : children === 'Esc' ? (
        'esc'
      ) : children === 'Tab' ? (
        '⇥'
      ) : children === 'Shift' ? (
        '⇧'
      ) : children === 'Space' ? (
        '␣'
      ) : (
        children
      )}
    </kbd>
  )
}

interface KeyboardShortcutsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  // Open with Cmd+/
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault()
        // Toggle if already open, otherwise open
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-3xl max-h-[85vh] bg-card rounded-2xl border shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Keyboard className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Keyboard Shortcuts</h2>
                  <p className="text-sm text-muted-foreground">Navigate faster with shortcuts</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Key>Cmd</Key>
                  <span>+</span>
                  <Key>/</Key>
                  <span className="ml-1">to toggle</span>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-accent transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(85vh-80px)]">
              <div className="grid md:grid-cols-2 gap-6">
                {SHORTCUTS.map((category) => (
                  <div key={category.name}>
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                      {category.name}
                    </h3>
                    <div className="space-y-2">
                      {category.shortcuts.map((shortcut, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-accent/50 transition-colors"
                        >
                          <span className="text-sm">{shortcut.description}</span>
                          <div className="flex items-center gap-1">
                            {shortcut.keys.map((key, keyIndex) => (
                              <React.Fragment key={keyIndex}>
                                {keyIndex > 0 && (
                                  <span className="text-muted-foreground text-xs mx-0.5">+</span>
                                )}
                                <Key>{key}</Key>
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Vim Mode Hint */}
              <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-purple-500/20">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0">
                    <span className="text-purple-500 font-mono text-sm font-bold">vim</span>
                  </div>
                  <div>
                    <h4 className="font-medium text-sm">Vim-style Navigation</h4>
                    <p className="text-sm text-muted-foreground mt-1">
                      Use <Key>J</Key> and <Key>K</Key> to navigate lists, <Key>G</Key> + letter for quick navigation.
                      Power users can enable full vim mode in settings.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t bg-muted/30 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Pro tip: Most shortcuts work without holding Cmd
              </p>
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90"
              >
                Done
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default KeyboardShortcutsModal
