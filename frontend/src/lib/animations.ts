/**
 * Framer Motion Animation Utilities
 *
 * Reusable animation variants and utilities for consistent motion design.
 */

import { Variants, Transition } from 'framer-motion';

// =============================================================================
// Transition Presets
// =============================================================================

export const transitions = {
  /** Fast micro-interactions (120ms) */
  fast: {
    type: 'tween',
    duration: 0.12,
    ease: [0.2, 0.8, 0.2, 1],
  } as Transition,

  /** Standard transitions (180ms) */
  base: {
    type: 'tween',
    duration: 0.18,
    ease: [0.2, 0.8, 0.2, 1],
  } as Transition,

  /** Smooth enter transitions (280ms) */
  smooth: {
    type: 'tween',
    duration: 0.28,
    ease: [0.16, 1, 0.3, 1],
  } as Transition,

  /** Slow dramatic transitions (420ms) */
  slow: {
    type: 'tween',
    duration: 0.42,
    ease: [0.16, 1, 0.3, 1],
  } as Transition,

  /** Spring animation for bouncy effects */
  spring: {
    type: 'spring',
    stiffness: 400,
    damping: 30,
  } as Transition,

  /** Gentle spring for larger movements */
  springGentle: {
    type: 'spring',
    stiffness: 200,
    damping: 25,
  } as Transition,
};

// =============================================================================
// Fade Variants
// =============================================================================

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: transitions.base,
  },
  exit: {
    opacity: 0,
    transition: transitions.fast,
  },
};

export const fadeInUp: Variants = {
  hidden: {
    opacity: 0,
    y: 12,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: transitions.fast,
  },
};

export const fadeInDown: Variants = {
  hidden: {
    opacity: 0,
    y: -12,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    y: 8,
    transition: transitions.fast,
  },
};

export const fadeInLeft: Variants = {
  hidden: {
    opacity: 0,
    x: -20,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: transitions.fast,
  },
};

export const fadeInRight: Variants = {
  hidden: {
    opacity: 0,
    x: 20,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: transitions.fast,
  },
};

// =============================================================================
// Scale Variants
// =============================================================================

export const scaleIn: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
  },
  visible: {
    opacity: 1,
    scale: 1,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: transitions.fast,
  },
};

export const scaleInBounce: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.9,
  },
  visible: {
    opacity: 1,
    scale: 1,
    transition: transitions.spring,
  },
  exit: {
    opacity: 0,
    scale: 0.9,
    transition: transitions.fast,
  },
};

// =============================================================================
// Page Transition Variants
// =============================================================================

export const pageTransition: Variants = {
  hidden: {
    opacity: 0,
    y: 8,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.16, 1, 0.3, 1],
      staggerChildren: 0.05,
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: 0.2,
      ease: [0.7, 0, 0.84, 0],
    },
  },
};

export const pageSlide: Variants = {
  hidden: {
    opacity: 0,
    x: 20,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.35,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: {
      duration: 0.25,
      ease: [0.7, 0, 0.84, 0],
    },
  },
};

// =============================================================================
// Container / Stagger Variants
// =============================================================================

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      staggerChildren: 0.03,
      staggerDirection: -1,
    },
  },
};

export const staggerContainerFast: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04,
      delayChildren: 0.05,
    },
  },
};

export const staggerContainerSlow: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.15,
    },
  },
};

// =============================================================================
// List Item Variants
// =============================================================================

export const listItem: Variants = {
  hidden: {
    opacity: 0,
    y: 8,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    y: -4,
    transition: transitions.fast,
  },
};

export const listItemSlide: Variants = {
  hidden: {
    opacity: 0,
    x: -12,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    x: 12,
    transition: transitions.fast,
  },
};

// =============================================================================
// Card Variants
// =============================================================================

export const cardVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 16,
    scale: 0.98,
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    y: -8,
    scale: 0.98,
    transition: transitions.fast,
  },
  hover: {
    y: -4,
    scale: 1.01,
    transition: transitions.base,
  },
  tap: {
    scale: 0.99,
    transition: transitions.fast,
  },
};

export const statCardVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 20,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: transitions.smooth,
  },
  hover: {
    y: -2,
    boxShadow: '0 10px 30px rgba(0, 0, 0, 0.28)',
    transition: transitions.base,
  },
};

// =============================================================================
// Modal / Dialog Variants
// =============================================================================

export const modalOverlay: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.2 },
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.15 },
  },
};

export const modalContent: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: 10,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 10,
    transition: transitions.fast,
  },
};

export const slideUp: Variants = {
  hidden: {
    opacity: 0,
    y: '100%',
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: transitions.springGentle,
  },
  exit: {
    opacity: 0,
    y: '100%',
    transition: transitions.smooth,
  },
};

// =============================================================================
// Sidebar / Navigation Variants
// =============================================================================

export const sidebarVariants: Variants = {
  hidden: {
    x: -280,
    opacity: 0,
  },
  visible: {
    x: 0,
    opacity: 1,
    transition: transitions.smooth,
  },
  exit: {
    x: -280,
    opacity: 0,
    transition: transitions.base,
  },
};

export const navItemVariants: Variants = {
  hidden: {
    opacity: 0,
    x: -12,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: transitions.smooth,
  },
  hover: {
    x: 4,
    transition: transitions.fast,
  },
};

// =============================================================================
// Tooltip / Popover Variants
// =============================================================================

export const tooltipVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.96,
    y: 4,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: transitions.fast,
  },
  exit: {
    opacity: 0,
    scale: 0.96,
    transition: { duration: 0.1 },
  },
};

export const dropdownVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: -8,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: transitions.base,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -8,
    transition: transitions.fast,
  },
};

// =============================================================================
// Button / Interactive Variants
// =============================================================================

export const buttonVariants: Variants = {
  hover: {
    scale: 1.02,
    transition: transitions.fast,
  },
  tap: {
    scale: 0.98,
    transition: transitions.fast,
  },
};

export const iconButtonVariants: Variants = {
  hover: {
    scale: 1.1,
    transition: transitions.fast,
  },
  tap: {
    scale: 0.9,
    transition: transitions.fast,
  },
};

// =============================================================================
// Loading / Skeleton Variants
// =============================================================================

export const pulseVariants: Variants = {
  animate: {
    opacity: [0.5, 1, 0.5],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

export const shimmerVariants: Variants = {
  animate: {
    x: ['-100%', '100%'],
    transition: {
      duration: 1.2,
      repeat: Infinity,
      ease: 'linear',
    },
  },
};

// =============================================================================
// Chart / Data Variants
// =============================================================================

export const chartBarVariants: Variants = {
  hidden: {
    scaleY: 0,
    opacity: 0,
  },
  visible: {
    scaleY: 1,
    opacity: 1,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

export const chartLineVariants: Variants = {
  hidden: {
    pathLength: 0,
    opacity: 0,
  },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 1, ease: 'easeInOut' },
      opacity: { duration: 0.2 },
    },
  },
};

// =============================================================================
// Notification / Toast Variants
// =============================================================================

export const toastVariants: Variants = {
  hidden: {
    opacity: 0,
    y: -20,
    scale: 0.95,
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: transitions.spring,
  },
  exit: {
    opacity: 0,
    y: -20,
    scale: 0.95,
    transition: transitions.base,
  },
};

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Create a stagger delay for list items
 */
export const getStaggerDelay = (index: number, baseDelay = 0.05): number => {
  return index * baseDelay;
};

/**
 * Create custom stagger container with configurable timing
 */
export const createStaggerContainer = (
  staggerChildren = 0.06,
  delayChildren = 0.1
): Variants => ({
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren,
      delayChildren,
    },
  },
});

/**
 * Create fade in variant with custom direction and distance
 */
export const createFadeIn = (
  direction: 'up' | 'down' | 'left' | 'right' = 'up',
  distance = 12
): Variants => {
  const axis = direction === 'up' || direction === 'down' ? 'y' : 'x';
  const value = direction === 'up' || direction === 'left' ? distance : -distance;

  return {
    hidden: {
      opacity: 0,
      [axis]: value,
    },
    visible: {
      opacity: 1,
      [axis]: 0,
      transition: transitions.smooth,
    },
    exit: {
      opacity: 0,
      [axis]: -value / 2,
      transition: transitions.fast,
    },
  };
};
