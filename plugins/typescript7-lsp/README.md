# typescript7-lsp

TypeScript 7 code intelligence through the language server built into `tsc`.

TypeScript 7 dropped `tsserver.js`. The official `typescript-lsp` plugin runs `typescript-language-server`, which needs `tsserver.js`, so it fails to start in a TypeScript 7 project. This plugin runs `tsc --lsp --stdio` instead.

## Language server

The plugin declares one server, `typescript`, that runs `tsc --lsp --stdio`. It handles these file types:

| Extension             | Language ID       |
| --------------------- | ----------------- |
| `.ts`, `.mts`, `.cts` | `typescript`      |
| `.tsx`                | `typescriptreact` |
| `.js`, `.mjs`, `.cjs` | `javascript`      |
| `.jsx`                | `javascriptreact` |

## Prerequisites

- TypeScript 7 or later, as the `tsc` found first on `PATH` when Claude Code starts. A project's `node_modules/.bin` on `PATH`, for example through mise's `_.path`, does this.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install typescript7-lsp@gsong-marketplace
```

Enable it only in TypeScript 7 projects, and turn off `typescript-lsp` there. Both plugins claim `.ts` files. In the project's `.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "typescript7-lsp@gsong-marketplace": true,
    "typescript-lsp@claude-plugins-official": false
  }
}
```
