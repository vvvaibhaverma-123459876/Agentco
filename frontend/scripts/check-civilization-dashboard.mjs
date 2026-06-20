import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const requiredRoutes = [
  'src/app/civilization/page.tsx',
  'src/app/civilization/institution/page.tsx',
  'src/app/civilization/reviews/page.tsx',
  'src/app/civilization/governance/page.tsx',
  'src/app/civilization/memory/page.tsx',
  'src/app/civilization/calibration/page.tsx',
];

for (const route of requiredRoutes) {
  if (!existsSync(join(root, route))) {
    throw new Error(`missing civilization dashboard route: ${route}`);
  }
}

const client = readFileSync(join(root, 'src/lib/civilization-api.ts'), 'utf8');
for (const label of ['Shipped', 'Partially Implemented', 'Experimental', 'Future']) {
  if (!client.includes(label)) {
    throw new Error(`missing capability label: ${label}`);
  }
}

const sidebar = readFileSync(join(root, 'src/components/Sidebar.tsx'), 'utf8');
for (const label of ['Civilization Map', 'Institution', 'Reviews', 'Governance', 'Memory', 'Calibration']) {
  if (!sidebar.includes(label)) {
    throw new Error(`sidebar missing label: ${label}`);
  }
}

console.log('civilization dashboard surface check passed');
