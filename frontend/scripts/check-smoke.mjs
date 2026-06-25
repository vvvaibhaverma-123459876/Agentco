import { access } from "node:fs/promises";

const requiredFiles = [
  "src/app/page.tsx",
  "src/app/autonomy/page.tsx",
  "next.config.js",
  "package.json",
];

for (const file of requiredFiles) {
  await access(new URL(`../${file}`, import.meta.url));
}

console.log(`frontend smoke check passed (${requiredFiles.length} files)`);
