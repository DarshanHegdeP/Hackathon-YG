const fs = require('fs');
const path = require('path');

const dirs = [
  'src/reviews',
  'src/controls',
  'src/review-controls',
  'src/users',
  'src/audit',
  'src/shared',
  'seed',
  'tests/reviews',
  'tests/controls',
  'tests/review-controls',
  'tests/audit',
  'docs'
];

dirs.forEach(dir => fs.mkdirSync(dir, { recursive: true }));

const tsconfig = {
  "compilerOptions": {
    "target": "es2022",
    "module": "commonjs",
    "rootDir": "./src",
    "outDir": "./dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "**/*.test.ts"]
};
fs.writeFileSync('tsconfig.json', JSON.stringify(tsconfig, null, 2));

const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
packageJson.scripts = {
  "build": "tsc",
  "test": "jest",
  "seed": "node scripts/seed.js"
};
fs.writeFileSync('package.json', JSON.stringify(packageJson, null, 2));

console.log('Setup complete.');
