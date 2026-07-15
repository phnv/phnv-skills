import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/cli.ts'],
  format: ['cjs'], // Node CLIs usually use CommonJS
  target: 'node18',
  clean: true,
  minify: true,
});
