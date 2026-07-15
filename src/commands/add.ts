import { Command } from 'commander';
import fs from 'fs-extra';
import path from 'path';

const TARGETS = {
  cursor: {
    trigger: '.cursor',
    dest: '.cursor/rules',
    renameMain: '.mdc', // rename SKILL.md to <skill>.mdc
  },
  copilot: {
    trigger: '.github',
    dest: '.github',
    renameMain: '.md', // rename SKILL.md to <skill>.md
  },
  claude: {
    trigger: '.claude',
    dest: '.claude/skills',
  },
  antigravity: {
    trigger: '.agents',
    dest: '.agents/skills',
  }
};

export const addCommand = new Command('add')
  .description('Add a skill to your project')
  .argument('<skill>', 'Name of the skill to add')
  .option('-g, --global', 'Install globally to ~/.gemini/config/skills')
  .action(async (skill: string, options: { global?: boolean }) => {
    try {
      // Find the skill in the bundled package
      const skillSourcePath = path.resolve(__dirname, '../skills', skill);
      
      if (!fs.existsSync(skillSourcePath)) {
        console.error(`Error: Skill '${skill}' not found in the repository.`);
        process.exit(1);
      }

      if (options.global) {
        // Global installation path
        const homeDir = process.env.HOME || process.env.USERPROFILE || '';
        const globalPath = path.join(homeDir, '.gemini/config/skills', skill);
        await copySkill(skillSourcePath, globalPath, skill);
        console.log(`✅ Successfully installed skill '${skill}' globally to ${globalPath}`);
        return;
      }

      // Local installation with auto-detection
      const cwd = process.cwd();
      let installedCount = 0;

      for (const [agent, config] of Object.entries(TARGETS)) {
        const triggerPath = path.join(cwd, config.trigger);
        if (fs.existsSync(triggerPath)) {
          const destDir = path.join(cwd, config.dest, skill);
          await copySkill(skillSourcePath, destDir, skill, config.renameMain);
          console.log(`✅ Installed skill '${skill}' for ${agent} at ${destDir}`);
          installedCount++;
        }
      }

      if (installedCount === 0) {
        // Fallback if no triggers found, assume antigravity workspace
        const destDir = path.join(cwd, TARGETS.antigravity.dest, skill);
        await copySkill(skillSourcePath, destDir, skill);
        console.log(`⚠️ No agent directories detected. Defaulting to ${destDir}`);
        console.log(`✅ Installed skill '${skill}' at ${destDir}`);
      }

    } catch (error: any) {
      console.error(`Failed to install skill: ${error.message}`);
      process.exit(1);
    }
  });

async function copySkill(src: string, dest: string, skillName: string, renameMainExt?: string) {
  // Ensure the destination exists
  await fs.ensureDir(dest);

  // Copy everything first
  await fs.copy(src, dest, { overwrite: true });

  // If a specific tool requires renaming SKILL.md, handle it here
  if (renameMainExt) {
    const mainFileSrc = path.join(dest, 'SKILL.md');
    if (fs.existsSync(mainFileSrc)) {
      const mainFileDest = path.join(dest, `${skillName}${renameMainExt}`);
      await fs.move(mainFileSrc, mainFileDest, { overwrite: true });
    }
  }
}
