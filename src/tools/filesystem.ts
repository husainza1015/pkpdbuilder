/**
 * Filesystem tools — MCP-compatible file operations
 * Gives the agent direct read/write/search access to the user's project
 * Author: Husain Z Attarwala, PhD
 */

import * as fs from 'fs';
import * as path from 'path';

export const filesystemTools = [
  {
    name: 'read_file',
    description: 'Read the contents of a file. Use for loading datasets, reading R scripts, config files, or any text file in the project.',
    input_schema: {
      type: 'object' as const,
      properties: {
        path: { type: 'string', description: 'Path to the file (relative to cwd or absolute)' },
      },
      required: ['path'],
    },
  },
  {
    name: 'write_file',
    description: 'Write content to a file. Creates parent directories if needed. Use for saving datasets, R scripts, reports, or any output.',
    input_schema: {
      type: 'object' as const,
      properties: {
        path: { type: 'string', description: 'Path to write to (relative to cwd or absolute)' },
        content: { type: 'string', description: 'Content to write' },
      },
      required: ['path', 'content'],
    },
  },
  {
    name: 'list_directory',
    description: 'List files and directories in a given path. Use to explore project structure, find datasets, or check output files.',
    input_schema: {
      type: 'object' as const,
      properties: {
        path: { type: 'string', description: 'Directory path (default: current directory)' },
      },
      required: [],
    },
  },
  {
    name: 'search_files',
    description: 'Search for files matching a glob pattern. Use to find datasets (*.csv), R scripts (*.R), model fits (*.rds), etc.',
    input_schema: {
      type: 'object' as const,
      properties: {
        pattern: { type: 'string', description: 'Glob pattern (e.g., "**/*.csv", "*.R", "output/*.png")' },
        path: { type: 'string', description: 'Base directory to search from (default: current directory)' },
      },
      required: ['pattern'],
    },
  },
  {
    name: 'move_file',
    description: 'Move or rename a file.',
    input_schema: {
      type: 'object' as const,
      properties: {
        source: { type: 'string', description: 'Source file path' },
        destination: { type: 'string', description: 'Destination file path' },
      },
      required: ['source', 'destination'],
    },
  },
  {
    name: 'get_file_info',
    description: 'Get metadata about a file: size, modified time, type. Use to check if a dataset exists before loading.',
    input_schema: {
      type: 'object' as const,
      properties: {
        path: { type: 'string', description: 'Path to the file' },
      },
      required: ['path'],
    },
  },
];

function resolvePath(p: string): string {
  return path.resolve(process.cwd(), p);
}

export async function executeFilesystemTool(
  name: string,
  args: Record<string, any>
): Promise<any> {
  switch (name) {
    case 'read_file': {
      const filePath = resolvePath(args.path);
      if (!fs.existsSync(filePath)) {
        return { success: false, error: `File not found: ${args.path}` };
      }
      const stat = fs.statSync(filePath);
      if (stat.size > 10 * 1024 * 1024) {
        return { success: false, error: `File too large (${(stat.size / 1024 / 1024).toFixed(1)}MB). Max 10MB.` };
      }
      const content = fs.readFileSync(filePath, 'utf-8');
      return {
        success: true,
        path: filePath,
        size: stat.size,
        lines: content.split('\n').length,
        content: content.length > 50000 ? content.substring(0, 50000) + '\n... (truncated)' : content,
      };
    }

    case 'write_file': {
      const filePath = resolvePath(args.path);
      const dir = path.dirname(filePath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(filePath, args.content, 'utf-8');
      return {
        success: true,
        path: filePath,
        size: Buffer.byteLength(args.content, 'utf-8'),
        message: `Written to ${args.path}`,
      };
    }

    case 'list_directory': {
      const dirPath = resolvePath(args.path || '.');
      if (!fs.existsSync(dirPath)) {
        return { success: false, error: `Directory not found: ${args.path || '.'}` };
      }
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      const items = entries.map(e => ({
        name: e.name,
        type: e.isDirectory() ? 'directory' : 'file',
        size: e.isFile() ? fs.statSync(path.join(dirPath, e.name)).size : undefined,
      }));
      return {
        success: true,
        path: dirPath,
        count: items.length,
        items,
      };
    }

    case 'search_files': {
      const basePath = resolvePath(args.path || '.');
      try {
        const matches: string[] = [];
        const searchDir = (dir: string, pattern: string) => {
          // Simple glob implementation for common patterns
          const parts = pattern.split('/');
          const isRecursive = parts[0] === '**';

          if (isRecursive && parts.length === 2) {
            // **/*.ext pattern
            const ext = parts[1];
            const walkDir = (d: string) => {
              try {
                const entries = fs.readdirSync(d, { withFileTypes: true });
                for (const entry of entries) {
                  const fullPath = path.join(d, entry.name);
                  if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
                    walkDir(fullPath);
                  } else if (entry.isFile()) {
                    if (matchGlob(entry.name, ext)) {
                      matches.push(path.relative(basePath, fullPath));
                    }
                  }
                }
              } catch {
                // skip inaccessible dirs
              }
            };
            walkDir(dir);
          } else {
            // Simple pattern like *.csv
            try {
              const entries = fs.readdirSync(dir, { withFileTypes: true });
              for (const entry of entries) {
                if (entry.isFile() && matchGlob(entry.name, pattern)) {
                  matches.push(path.relative(basePath, path.join(dir, entry.name)));
                }
              }
            } catch {
              // skip
            }
          }
        };
        searchDir(basePath, args.pattern);
        return {
          success: true,
          pattern: args.pattern,
          count: matches.length,
          files: matches.slice(0, 100),
        };
      } catch (err: any) {
        return { success: false, error: err.message };
      }
    }

    case 'move_file': {
      const src = resolvePath(args.source);
      const dest = resolvePath(args.destination);
      if (!fs.existsSync(src)) {
        return { success: false, error: `Source not found: ${args.source}` };
      }
      const destDir = path.dirname(dest);
      if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
      }
      fs.renameSync(src, dest);
      return { success: true, source: args.source, destination: args.destination };
    }

    case 'get_file_info': {
      const filePath = resolvePath(args.path);
      if (!fs.existsSync(filePath)) {
        return { success: false, error: `File not found: ${args.path}` };
      }
      const stat = fs.statSync(filePath);
      return {
        success: true,
        path: filePath,
        size: stat.size,
        sizeHuman: stat.size > 1024 * 1024
          ? `${(stat.size / 1024 / 1024).toFixed(1)}MB`
          : `${(stat.size / 1024).toFixed(1)}KB`,
        isFile: stat.isFile(),
        isDirectory: stat.isDirectory(),
        modified: stat.mtime.toISOString(),
        created: stat.birthtime.toISOString(),
      };
    }

    default:
      return { success: false, error: `Unknown filesystem tool: ${name}` };
  }
}

function matchGlob(filename: string, pattern: string): boolean {
  // Simple glob matching for *.ext patterns
  if (pattern.startsWith('*.')) {
    return filename.endsWith(pattern.substring(1));
  }
  if (pattern === '*') return true;
  return filename === pattern;
}
