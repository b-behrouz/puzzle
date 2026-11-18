import { copyFile, mkdir } from 'node:fs/promises';

const source = new URL('../puzzle-fantasy-mobile.html', import.meta.url);
const output = new URL('../www/', import.meta.url);

await mkdir(output, { recursive: true });
await copyFile(source, new URL('index.html', output));
