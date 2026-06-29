/**
 * ErrorScreen — shared terminal-readout surface for HTTP error states.
 *
 * Stratum's domain is signal health and a trust gate that resolves to
 * PASS / HOLD / BLOCK. These error pages lean into that: an instrument
 * readout rather than a generic "big gradient number" page. Ink + ember,
 * hairline borders, Geist Mono for status/diagnostics, one ember CTA.
 *
 * Theme-aware via semantic tokens (dark + light both first-class). The
 * entrance is a single orchestrated stagger; it collapses to a static
 * render under prefers-reduced-motion.
 */

import { Link } from 'react-router-dom';
import { motion, useReducedMotion, type Variants } from 'framer-motion';

export interface ErrorAction {
  label: string;
  /** Render as a router Link when set. */
  to?: string;
  /** Render as a button when set (e.g. history.back). */
  onClick?: () => void;
  variant: 'primary' | 'ghost';
}

export interface DiagnosticRow {
  label: string;
  value: string;
  /** Tints the value — `blocked` uses danger, `accent` uses ember. */
  emphasis?: 'blocked' | 'accent';
}

interface ErrorScreenProps {
  /** HTTP code, shown as the readout numeral. */
  code: string;
  /** Short machine-status, mono, e.g. "NO ROUTE" / "GATE · BLOCKED". */
  status: string;
  /** Whether the status reads as a blocked/denied state (tints the rule). */
  tone?: 'neutral' | 'blocked';
  /** Human headline (the real <h1>). */
  title: string;
  /** One short supporting sentence. */
  body: string;
  diagnostics: DiagnosticRow[];
  actions: ErrorAction[];
  /** Quiet secondary navigation, rendered as a mono link row. */
  links?: { label: string; to: string }[];
}

export function ErrorScreen({
  code,
  status,
  tone = 'neutral',
  title,
  body,
  diagnostics,
  actions,
  links,
}: ErrorScreenProps) {
  const reduce = useReducedMotion();

  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.06, delayChildren: reduce ? 0 : 0.05 } },
  };
  const item: Variants = reduce
    ? { hidden: { opacity: 1 }, show: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: 12 },
        show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
      };

  const ruleColor = tone === 'blocked' ? 'hsl(var(--danger))' : 'hsl(var(--primary))';

  return (
    <main className="relative min-h-screen overflow-hidden bg-background text-foreground">
      {/* Instrument grid — faint, edge-masked. Replaces decorative orbs. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.5]"
        style={{
          backgroundImage:
            'linear-gradient(hsl(var(--border)) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
          maskImage: 'radial-gradient(ellipse 80% 70% at 30% 40%, #000 30%, transparent 100%)',
          WebkitMaskImage:
            'radial-gradient(ellipse 80% 70% at 30% 40%, #000 30%, transparent 100%)',
        }}
      />

      <div className="relative mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16 sm:px-10">
        <motion.div variants={container} initial="hidden" animate="show">
          {/* Status line */}
          <motion.div
            variants={item}
            className="flex items-center justify-between gap-4 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground"
          >
            <span className="inline-flex items-center gap-2">
              <span
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: ruleColor }}
              />
              Stratum · System status
            </span>
            <span className="tabular-nums">HTTP {code}</span>
          </motion.div>

          <motion.div
            variants={item}
            className="mt-4 h-px w-full origin-left"
            style={{ background: `linear-gradient(90deg, ${ruleColor}, transparent 60%)` }}
          />

          {/* Readout numeral + machine status */}
          <motion.div variants={item} className="mt-8 flex items-end gap-5">
            <span
              aria-hidden="true"
              className="font-sans font-semibold leading-[0.85] tracking-tight tabular-nums"
              style={{ fontSize: 'clamp(4.5rem, 16vw, 9rem)' }}
            >
              {code}
            </span>
            <span className="mb-3 font-mono text-sm uppercase tracking-[0.16em] text-muted-foreground">
              {status}
            </span>
          </motion.div>

          {/* Headline + body */}
          <motion.h1
            variants={item}
            className="mt-8 font-sans text-3xl font-semibold tracking-tight sm:text-4xl"
          >
            {title}
          </motion.h1>
          <motion.p
            variants={item}
            className="mt-3 max-w-[58ch] text-base leading-relaxed text-muted-foreground"
          >
            {body}
          </motion.p>

          {/* Diagnostic panel — hairline rows, mono key/value. No side-stripe. */}
          <motion.dl
            variants={item}
            className="mt-8 overflow-hidden rounded-xl border border-border bg-card/40 font-mono text-sm"
          >
            {diagnostics.map((row, i) => (
              <div
                key={row.label}
                className={`grid grid-cols-[10rem_1fr] gap-4 px-4 py-3 ${
                  i > 0 ? 'border-t border-border' : ''
                }`}
              >
                <dt className="uppercase tracking-[0.12em] text-muted-foreground">{row.label}</dt>
                <dd
                  className="truncate tabular-nums"
                  style={
                    row.emphasis === 'blocked'
                      ? { color: 'hsl(var(--danger))' }
                      : row.emphasis === 'accent'
                        ? { color: 'hsl(var(--primary))' }
                        : undefined
                  }
                >
                  {row.value}
                </dd>
              </div>
            ))}
          </motion.dl>

          {/* Actions */}
          <motion.div variants={item} className="mt-8 flex flex-wrap items-center gap-3">
            {actions.map((a) => {
              const cls =
                a.variant === 'primary'
                  ? 'bg-primary text-primary-foreground hover:bg-secondary'
                  : 'border border-border text-foreground hover:bg-muted';
              const base =
                'inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';
              return a.to ? (
                <Link key={a.label} to={a.to} className={`${base} ${cls}`}>
                  {a.label}
                </Link>
              ) : (
                <button key={a.label} type="button" onClick={a.onClick} className={`${base} ${cls}`}>
                  {a.label}
                </button>
              );
            })}
          </motion.div>

          {/* Quiet nav */}
          {links && links.length > 0 && (
            <motion.nav
              variants={item}
              className="mt-10 flex flex-wrap gap-x-6 gap-y-2 border-t border-border pt-6 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground"
              aria-label="Helpful links"
            >
              {links.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:outline-none"
                >
                  {l.label}
                </Link>
              ))}
            </motion.nav>
          )}
        </motion.div>
      </div>
    </main>
  );
}

export default ErrorScreen;
