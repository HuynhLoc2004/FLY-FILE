import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const assetsDir = join(root, 'dist', 'assets');

const aliases = [
  { alias: 'index-N-GQUgWn.js', prefix: 'index-', mode: 'entry' },
  { alias: 'api-TFXP3eJ6.js', prefix: 'api-', mode: 'named' },
  { alias: 'SplitWorkspace-DpE7Ftj6.js', prefix: 'SplitWorkspace-', mode: 'default' },
  { alias: 'download-BcqDT9Py.js', prefix: 'download-', mode: 'named' },
  { alias: 'upload-DUY3s7e_.js', prefix: 'upload-', mode: 'named' },
];

const files = existsSync(assetsDir) ? readdirSync(assetsDir) : [];

const findTarget = (prefix, alias) => files.find((file) => (
  file.startsWith(prefix)
  && file.endsWith('.js')
  && file !== alias
));

const buildAliasModule = ({ mode }, target) => {
  if (mode === 'entry') return `import './${target}';\n`;
  if (mode === 'default') return `export * from './${target}';\nexport { default } from './${target}';\n`;
  return `export * from './${target}';\n`;
};

mkdirSync(assetsDir, { recursive: true });

for (const alias of aliases) {
  const target = findTarget(alias.prefix, alias.alias);
  if (!target) {
    console.warn(`No asset target found for ${alias.alias}`);
    continue;
  }

  writeFileSync(join(assetsDir, alias.alias), buildAliasModule(alias, target));
  console.log(`Legacy asset alias: ${alias.alias} -> ${target}`);
}
