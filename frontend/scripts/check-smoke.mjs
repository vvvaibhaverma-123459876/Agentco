import { access, readFile } from "node:fs/promises";
import { readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const requiredFiles = [
  "src/app/page.tsx",
  "src/app/autonomy/page.tsx",
  "src/app/api/[...path]/route.ts",
  "src/app/api/health/route.ts",
  "next.config.js",
  "package.json",
];

for (const file of requiredFiles) {
  await access(new URL(`../${file}`, import.meta.url));
}

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...await walk(full));
    else files.push(full);
  }
  return files;
}

const repoRoot = fileURLToPath(new URL("..", import.meta.url));
const srcRoot = fileURLToPath(new URL("../src", import.meta.url));
const sourceFiles = (await walk(srcRoot)).filter(file => /\.(ts|tsx|js|jsx)$/.test(file));
const forbidden = [];
for (const file of sourceFiles) {
  const text = await readFile(file, "utf8");
  if (text.includes("NEXT_PUBLIC_AGENTCO_API_KEY")) forbidden.push(path.relative(repoRoot, file));
}
if (forbidden.length) {
  throw new Error(`privileged browser API key reference found: ${forbidden.join(", ")}`);
}

console.log(`frontend smoke check passed (${requiredFiles.length} files, ${sourceFiles.length} source files scanned)`);
