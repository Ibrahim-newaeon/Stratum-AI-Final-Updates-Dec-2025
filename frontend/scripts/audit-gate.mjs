#!/usr/bin/env node
/**
 * Frontend dependency-audit gate.
 *
 * `npm audit` has no way to waive a single advisory, so the CI gate used to be
 * all-or-nothing: one unfixable finding turned every PR red, including PRs
 * whose whole purpose was fixing a *different* advisory. This wraps
 * `npm audit --json` and fails only on advisories that are not explicitly
 * waived in `.audit-allowlist.json`.
 *
 * A waiver is a decision with a reason and an expiry, not a mute button:
 * an entry past its `expires` date fails the gate just like an unwaived
 * finding, so waivers get revisited instead of quietly accumulating.
 *
 * Usage: node scripts/audit-gate.mjs [--audit-level=high] [--omit=dev]
 */
import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ALLOWLIST_PATH = resolve(HERE, '..', '.audit-allowlist.json');

const SEVERITY_ORDER = ['info', 'low', 'moderate', 'high', 'critical'];

const args = process.argv.slice(2);
const levelArg = args.find((a) => a.startsWith('--audit-level='));
const minLevel = levelArg ? levelArg.split('=')[1] : 'high';
const omitDev = args.includes('--omit=dev');

const minRank = SEVERITY_ORDER.indexOf(minLevel);
if (minRank === -1) {
  console.error(`audit-gate: unknown --audit-level=${minLevel}`);
  process.exit(2);
}

/**
 * Run `npm audit --json`. It exits non-zero when findings exist, so capture
 * regardless.
 *
 * Built as one command string rather than execFileSync(argv): npm is npm.cmd
 * on Windows, and node refuses to spawn a .cmd without a shell (EINVAL). Every
 * token here is a literal — nothing from the report or the allowlist reaches
 * the command line.
 */
function runAudit() {
  const cmd = `npm audit --json${omitDev ? ' --omit=dev' : ''}`;
  try {
    return execSync(cmd, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  } catch (err) {
    // Findings present => non-zero exit, but stdout still holds the report.
    if (err.stdout) return err.stdout;
    throw err;
  }
}

function loadAllowlist() {
  let raw;
  try {
    raw = readFileSync(ALLOWLIST_PATH, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return [];
    throw err;
  }
  const parsed = JSON.parse(raw);
  return Array.isArray(parsed.waivers) ? parsed.waivers : [];
}

const report = JSON.parse(runAudit());
const waivers = loadAllowlist();
const today = new Date().toISOString().slice(0, 10);

const findings = [];
for (const [name, vuln] of Object.entries(report.vulnerabilities ?? {})) {
  if (SEVERITY_ORDER.indexOf(vuln.severity) < minRank) continue;
  // `via` mixes advisory objects with plain strings (transitive parents).
  const advisories = (vuln.via ?? []).filter((v) => typeof v === 'object');
  for (const adv of advisories) {
    findings.push({
      package: name,
      severity: adv.severity ?? vuln.severity,
      id: adv.url?.split('/').pop() ?? String(adv.source ?? 'unknown'),
      title: adv.title ?? '(no title)',
      url: adv.url ?? '',
    });
  }
}

const blocking = [];
const waived = [];
const expired = [];

for (const f of findings) {
  const w = waivers.find((x) => x.id === f.id && x.package === f.package);
  if (!w) {
    blocking.push(f);
  } else if (w.expires && w.expires < today) {
    expired.push({ ...f, expires: w.expires, reason: w.reason });
  } else {
    waived.push({ ...f, expires: w.expires, reason: w.reason });
  }
}

for (const f of waived) {
  console.log(`WAIVED   ${f.severity.padEnd(8)} ${f.package} ${f.id} (until ${f.expires})`);
  console.log(`         reason: ${f.reason}`);
}
for (const f of expired) {
  console.log(`::error::Audit waiver EXPIRED (${f.expires}) for ${f.package} ${f.id} — re-review it`);
}
for (const f of blocking) {
  console.log(`::error::${f.severity.toUpperCase()} ${f.package} ${f.id} — ${f.title}`);
  if (f.url) console.log(`         ${f.url}`);
}

const failures = blocking.length + expired.length;
if (failures > 0) {
  console.error(
    `\naudit-gate: ${failures} unwaived finding(s) at >= ${minLevel}; ${waived.length} waived.`,
  );
  process.exit(1);
}
console.log(`\naudit-gate: no unwaived findings at >= ${minLevel} (${waived.length} waived).`);
