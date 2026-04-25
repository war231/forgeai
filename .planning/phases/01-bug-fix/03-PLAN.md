---
wave: 2
depends_on: [01]
files_modified:
  - src/extension.ts
autonomous: true
requirements_addressed: [REQ-006]
---

<objective>
修复VSCode扩展命令映射问题，添加错误处理和日志
</objective>

<tasks>
<task id="1" type="execute">
<read_first>
- src/extension.ts (file being modified)
</read_first>

<action>
检查并修复命令注册：

1. 确保所有命令正确注册：
```typescript
// 命令映射表
const COMMAND_MAP: Record<string, string> = {
  'forgeai.init': 'init',
  'forgeai.createProject': 'create-project',
  'forgeai.analyzeBook': 'analyze-book',
  'forgeai.brainstorm': 'brainstorm',
  'forgeai.buildWorld': 'build-world',
  'forgeai.createCharacters': 'create-characters',
  'forgeai.outline': 'outline',
  'forgeai.write': 'write',
  'forgeai.check': 'check',
  'forgeai.checkAfter': 'check-after',
  'forgeai.review': 'review',
  'forgeai.reviewIndependent': 'review-independent',
  'forgeai.updateState': 'update-state',
  'forgeai.query': 'query',
  'forgeai.help': 'help'
};

// 注册所有命令
export function activate(context: vscode.ExtensionContext) {
  console.log('ForgeAI 扩展激活');
  
  for (const [commandId, cliCommand] of Object.entries(COMMAND_MAP)) {
    const disposable = vscode.commands.registerCommand(commandId, async () => {
      await executeForgeAICommand(cliCommand);
    });
    context.subscriptions.push(disposable);
    console.log(`注册命令：${commandId} -> ${cliCommand}`);
  }
}
```

2. 添加命令执行函数：
```typescript
async function executeForgeAICommand(command: string, args?: string[]) {
  const terminal = vscode.window.createTerminal('ForgeAI');
  
  try {
    const fullCommand = args 
      ? `forgeai ${command} ${args.join(' ')}`
      : `forgeai ${command}`;
    
    console.log(`执行命令：${fullCommand}`);
    terminal.sendText(fullCommand);
    terminal.show();
    
  } catch (error) {
    const errorMsg = `命令执行失败：${error}`;
    console.error(errorMsg);
    vscode.window.showErrorMessage(errorMsg);
  }
}
```
</action>

<acceptance_criteria>
- `extension.ts contains "COMMAND_MAP"`
- `extension.ts contains "console.log(\`注册命令"`
- `extension.ts contains "executeForgeAICommand"`
- `extension.ts contains "try {"`
- `extension.ts contains "catch (error)"`
</acceptance_criteria>
</task>

<task id="2" type="execute">
<read_first>
- src/extension.ts (file being modified)
</read_first>

<action>
添加命令参数处理：

```typescript
// 带参数的命令注册示例
vscode.commands.registerCommand('forgeai.check', async () => {
  const chapter = await vscode.window.showInputBox({
    prompt: '请输入章节号',
    placeHolder: '例如：20'
  });
  
  if (chapter) {
    await executeForgeAICommand('check', [chapter]);
  }
});

vscode.commands.registerCommand('forgeai.reviewIndependent', async () => {
  const chapter = await vscode.window.showInputBox({
    prompt: '请输入章节号',
    placeHolder: '例如：20'
  });
  
  if (chapter) {
    await executeForgeAICommand('check', [chapter, '--independent']);
  }
});
```
</action>

<acceptance_criteria>
- `extension.ts contains "showInputBox"`
- `extension.ts contains "prompt: '请输入章节号'"`
- `extension.ts contains "--independent"`
</acceptance_criteria>
</task>

<task id="3" type="execute">
<read_first>
- src/extension.ts (file being modified)
</read_first>

<action>
添加错误处理和用户提示：

```typescript
async function executeForgeAICommand(command: string, args?: string[]) {
  // 检查 forgeai 是否安装
  try {
    const checkResult = await execAsync('forgeai --version');
    console.log(`ForgeAI 版本：${checkResult}`);
  } catch (error) {
    const errorMsg = 'ForgeAI 未安装或不在 PATH 中。请先安装 ForgeAI。';
    vscode.window.showErrorMessage(errorMsg, '查看安装文档').then(selection => {
      if (selection === '查看安装文档') {
        vscode.env.openExternal(vscode.Uri.parse('https://github.com/your-repo/forge-ai#installation'));
      }
    });
    return;
  }
  
  const terminal = vscode.window.createTerminal('ForgeAI');
  
  try {
    const fullCommand = args 
      ? `forgeai ${command} ${args.join(' ')}`
      : `forgeai ${command}`;
    
    console.log(`执行命令：${fullCommand}`);
    vscode.window.showInformationMessage(`执行：${fullCommand}`);
    
    terminal.sendText(fullCommand);
    terminal.show();
    
  } catch (error) {
    const errorMsg = `命令执行失败：${error}`;
    console.error(errorMsg);
    vscode.window.showErrorMessage(errorMsg);
  }
}

// 辅助函数：异步执行命令
function execAsync(command: string): Promise<string> {
  return new Promise((resolve, reject) => {
    require('child_process').exec(command, (error: any, stdout: string) => {
      if (error) {
        reject(error);
      } else {
        resolve(stdout);
      }
    });
  });
}
```
</action>

<acceptance_criteria>
- `extension.ts contains "forgeai --version"`
- `extension.ts contains "ForgeAI 未安装"`
- `extension.ts contains "showInformationMessage"`
- `extension.ts contains "showErrorMessage"`
- `extension.ts contains "execAsync"`
</acceptance_criteria>
</task>
</tasks>

<verification>
1. 在 VSCode 中按 F5 启动扩展调试
2. 测试所有命令是否正确注册（命令面板中可见）
3. 测试命令执行是否正常
4. 测试错误处理（如 forgeai 未安装时）
</verification>

<must_haves>
- 所有命令必须正确映射
- 必须有错误处理
- 必须有用户提示
- 必须添加日志
</must_haves>
