import os
from pathlib import Path

BASE_DIR = Path("audit")

FILES = {
    "guardrails.md": """You are a strict production auditor.

Rules:
- No generic advice
- No assumptions → label [ASSUMPTION]
- If data missing → add "missing_data"
- Every recommendation must include:
  - metric
  - threshold
  - evidence
- If unknown → say "I don't know based on available evidence"
- Prioritize blockers over improvements
- Output must follow provided structure exactly
""",

    "prompts/master.md": """Audit this project for 100% production readiness.

Scope:
- Product
- Frontend
- Backend
- Database
- Tracking
- DevOps
- Security
- Performance

Return:
- blockers
- exact fixes
- readiness_score
- critical_path
""",

    "prompts/backend.md": """Audit backend only.

Check:
- validation
- auth
- rate limiting
- security

Return exact fixes with code.
""",

    "prompts/frontend.md": """Audit frontend.

Check:
- mobile-first
- loading states
- error states
- performance

Return exact fixes.
""",

    "prompts/tracking.md": """Audit tracking.

Check:
- GA4
- Meta Pixel
- TikTok
- GTM

Return:
- missing events
- broken tracking
- exact fixes
""",

    "run-audit.ts": """import { execSync } from "child_process";
import fs from "fs";
import path from "path";

const OUTPUT_DIR = path.join(__dirname, "outputs");

function runClaude(prompt: string, name: string) {
  console.log(`Running audit: ${name}...`);

  try {
    const result = execSync(`claude chat`, {
      input: prompt,
      encoding: "utf-8",
      maxBuffer: 1024 * 1024 * 10,
    });

    fs.writeFileSync(
      path.join(OUTPUT_DIR, `${name}.md`),
      result
    );

    console.log(`Saved: ${name}.md`);
  } catch (err) {
    console.error(`Error in ${name}`, err);
  }
}

function loadFile(filePath: string) {
  return fs.readFileSync(filePath, "utf-8");
}

function buildPrompt(promptFile: string) {
  const guardrails = loadFile(
    path.join(__dirname, "guardrails.md")
  );
  const prompt = loadFile(promptFile);

  return `
${guardrails}

${prompt}

Read all files in this repository before answering.
`;
}

function runAll() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR);
  }

  runClaude(
    buildPrompt(path.join(__dirname, "prompts/master.md")),
    "master-audit"
  );

  runClaude(
    buildPrompt(path.join(__dirname, "prompts/backend.md")),
    "backend-audit"
  );
}

runAll();
""",

    "utils.ts": """export function timestamp() {
  return Date.now() + "_" + Math.random().toString(36).slice(2);
}
"""
}


def create_structure():
    print("Creating audit structure...")

    # Create base folders
    (BASE_DIR / "prompts").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "outputs").mkdir(parents=True, exist_ok=True)

    for relative_path, content in FILES.items():
        file_path = BASE_DIR / relative_path

        # Ensure parent folders exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            print(f"Skipping (exists): {file_path}")
            continue

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Created: {file_path}")


if __name__ == "__main__":
    create_structure()
    print("\\n✅ Audit system ready.")