#!/usr/bin/env node

import { Command } from 'commander';
import { addCommand } from './commands/add';
import fs from 'fs-extra';
import path from 'path';

const program = new Command();

// Read package.json to get the version
const packageJsonPath = path.join(__dirname, '../package.json');
let version = '1.0.0';
try {
  const packageJson = fs.readJsonSync(packageJsonPath);
  version = packageJson.version;
} catch (e) {
  // Ignore
}

program
  .name('phnv-skills')
  .description('CLI to manage and install agent skills')
  .version(version);

program.addCommand(addCommand);

program.parse(process.argv);
