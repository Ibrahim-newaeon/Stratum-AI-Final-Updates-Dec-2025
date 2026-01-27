/**
 * Framer Motion UI Components
 *
 * Animated wrapper components for consistent motion across the app.
 */

import React from 'react';
import { AnimatePresence, HTMLMotionProps, motion } from 'framer-motion';
import {
  buttonVariants,
  cardVariants,
  fadeIn,
  fadeInUp,
  listItem,
  modalContent,
  modalOverlay,
  pageTransition,
  scaleIn,
  staggerContainer,
  statCardVariants,
  toastVariants,
  transitions,
} from '@/lib/animations';
import { cn } from '@/lib/utils';

// =============================================================================
// Page Transition
// =============================================================================

interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
}

export const PageTransition: React.FC<PageTransitionProps> = ({ children, className }) => {
  return (
    <motion.div
      variants={pageTransition}
      initial="hidden"
      animate="visible"
      exit="exit"
      className={className}
    >
      {children}
    </motion.div>
  );
};

// =============================================================================
// Fade In Components
// =============================================================================

interface FadeInProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right' | 'none';
}

export const FadeIn: React.FC<FadeInProps> = ({
  children,
  className,
  delay = 0,
  direction = 'up',
  ...props
}) => {
  const getVariants = () => {
    switch (direction) {
      case 'up':
        return fadeInUp;
      case 'none':
        return fadeIn;
      default:
        return fadeInUp;
    }
  };

  return (
    <motion.div
      variants={getVariants()}
      initial="hidden"
      animate="visible"
      exit="exit"
      transition={{ delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
};

// =============================================================================
// Scale In Component
// =============================================================================

interface ScaleInProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export const ScaleIn: React.FC<ScaleInProps> = ({ children, className, delay = 0, ...props }) => {
  return (
    <motion.div
      variants={scaleIn}
      initial="hidden"
      animate="visible"
      exit="exit"
      transition={{ delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
};

// =============================================================================
// Stagger Container & Items
// =============================================================================

interface StaggerContainerProps {
  children: React.ReactNode;
  className?: string;
  staggerDelay?: number;
  initialDelay?: number;
}

export const StaggerContainer: React.FC<StaggerContainerProps> = ({
  children,
  className,
  staggerDelay = 0.06,
  initialDelay = 0.1,
}) => {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: staggerDelay,
            delayChildren: initialDelay,
          },
        },
      }}
      initial="hidden"
      animate="visible"
      className={className}
    >
      {children}
    </motion.div>
  );
};

interface StaggerItemProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
}

export const StaggerItem: React.FC<StaggerItemProps> = ({ children, className, ...props }) => {
  return (
    <motion.div variants={listItem} className={className} {...props}>
      {children}
    </motion.div>
  );
};

// =============================================================================
// Animated Card
// =============================================================================

interface AnimatedCardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
  delay?: number;
}

export const AnimatedCard: React.FC<AnimatedCardProps> = ({
  children,
  className,
  hoverEffect = true,
  delay = 0,
  ...props
}) => {
  return (
    <motion.div
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      whileHover={hoverEffect ? 'hover' : undefined}
      whileTap={hoverEffect ? 'tap' : undefined}
      transition={{ delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
};

// =============================================================================
// Stat Card (for dashboard metrics)
// =============================================================================

interface StatCardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  index?: number;
}

export const StatCard: React.FC<StatCardProps> = ({ children, className, index = 0, ...props }) => {
  return (
    <motion.div
      variants={statCardVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      transition={{ delay: index * 0.08 }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
};

// =============================================================================
// Animated List
// =============================================================================

interface AnimatedListProps {
  children: React.ReactNode;
  className?: string;
}

export const AnimatedList: React.FC<AnimatedListProps> = ({ children, className }) => {
  return (
    <motion.ul variants={staggerContainer} initial="hidden" animate="visible" className={className}>
      {children}
    </motion.ul>
  );
};

interface AnimatedListItemProps extends HTMLMotionProps<'li'> {
  children: React.ReactNode;
  className?: string;
}

export const AnimatedListItem: React.FC<AnimatedListItemProps> = ({
  children,
  className,
  ...props
}) => {
  return (
    <motion.li variants={listItem} className={className} {...props}>
      {children}
    </motion.li>
  );
};

// =============================================================================
// Animated Button
// =============================================================================

interface AnimatedButtonProps extends HTMLMotionProps<'button'> {
  children: React.ReactNode;
  className?: string;
}

export const AnimatedButton: React.FC<AnimatedButtonProps> = ({
  children,
  className,
  ...props
}) => {
  return (
    <motion.button
      variants={buttonVariants}
      whileHover="hover"
      whileTap="tap"
      className={className}
      {...props}
    >
      {children}
    </motion.button>
  );
};

// =============================================================================
// Modal / Dialog Components
// =============================================================================

interface AnimatedModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
}

export const AnimatedModal: React.FC<AnimatedModalProps> = ({
  isOpen,
  onClose,
  children,
  className,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            variants={modalOverlay}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            variants={modalContent}
            initial="hidden"
            animate="visible"
            exit="exit"
            className={cn(
              'fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2',
              className
            )}
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// =============================================================================
// Toast / Notification
// =============================================================================

interface AnimatedToastProps {
  children: React.ReactNode;
  className?: string;
  isVisible: boolean;
}

export const AnimatedToast: React.FC<AnimatedToastProps> = ({ children, className, isVisible }) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          variants={toastVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className={className}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// =============================================================================
// Hover Scale Effect
// =============================================================================

interface HoverScaleProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  scale?: number;
}

export const HoverScale: React.FC<HoverScaleProps> = ({
  children,
  className,
  scale = 1.02,
  ...props
}) => {
  return (
    <motion.div
      whileHover={{ scale }}
      whileTap={{ scale: 0.98 }}
      transition={transitions.fast}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
};

// =============================================================================
// Presence Wrapper (for AnimatePresence)
// =============================================================================

interface PresenceProps {
  children: React.ReactNode;
  mode?: 'sync' | 'wait' | 'popLayout';
}

export const Presence: React.FC<PresenceProps> = ({ children, mode = 'wait' }) => {
  return <AnimatePresence mode={mode}>{children}</AnimatePresence>;
};

// =============================================================================
// Loading Skeleton with Animation
// =============================================================================

interface SkeletonProps {
  className?: string;
}

export const AnimatedSkeleton: React.FC<SkeletonProps> = ({ className }) => {
  return (
    <motion.div
      className={cn('relative overflow-hidden rounded-md bg-white/5', className)}
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    >
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
        animate={{ x: ['-100%', '100%'] }}
        transition={{
          duration: 1.2,
          repeat: Infinity,
          ease: 'linear',
        }}
      />
    </motion.div>
  );
};

// =============================================================================
// Counter Animation (for stats)
// =============================================================================

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  className?: string;
  formatter?: (value: number) => string;
}

export const AnimatedCounter: React.FC<AnimatedCounterProps> = ({
  value,
  duration = 1,
  className,
  formatter = (v) => v.toLocaleString(),
}) => {
  const [displayValue, setDisplayValue] = React.useState(0);

  React.useEffect(() => {
    const startTime = Date.now();
    const startValue = displayValue;

    const animate = () => {
      const now = Date.now();
      const progress = Math.min((now - startTime) / (duration * 1000), 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = startValue + (value - startValue) * easeOut;

      setDisplayValue(current);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return <span className={className}>{formatter(Math.round(displayValue))}</span>;
};

// =============================================================================
// Reveal on Scroll (Intersection Observer)
// =============================================================================

interface RevealOnScrollProps {
  children: React.ReactNode;
  className?: string;
  threshold?: number;
}

export const RevealOnScroll: React.FC<RevealOnScrollProps> = ({
  children,
  className,
  threshold = 0.1,
}) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = React.useState(false);

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [threshold]);

  return (
    <motion.div
      ref={ref}
      variants={fadeInUp}
      initial="hidden"
      animate={isVisible ? 'visible' : 'hidden'}
      className={className}
    >
      {children}
    </motion.div>
  );
};

// Re-export motion and AnimatePresence for convenience
export { motion, AnimatePresence } from 'framer-motion';
