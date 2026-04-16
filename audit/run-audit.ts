import { execSync } from "child_process";
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
