import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { execFile, exec } from 'child_process';

const ASSETS_DIR = 'system';
const SKILLS_DIR = `${ASSETS_DIR}/skills`;
const CHECKERS_DIR = `${ASSETS_DIR}/checkers`;
const REFERENCES_DIR = `${ASSETS_DIR}/references`;
const CONSTITUTION_DIR = `${ASSETS_DIR}/constitution`;
const TEMPLATES_DIR = `${ASSETS_DIR}/templates`;
const SCRIPTS_DIR = `${ASSETS_DIR}/scripts`;

const PROJECT_DIRS = [
    '.forgeai',
    '.forgeai/memory',
    '.forgeai/constitution',
    '1-边界',
    '2-设定',
    '3-大纲',
    '4-正文',
    '5-审查',
];

// 命令映射表
const COMMAND_MAP: Record<string, string> = {
    'forgeAI.init': 'init',
    'forgeAI.createProject': 'create-project',
    'forgeAI.analyzeBook': 'analyze-book',
    'forgeAI.brainstorm': 'brainstorm',
    'forgeAI.buildWorld': 'build-world',
    'forgeAI.createCharacters': 'create-characters',
    'forgeAI.outline': 'outline',
    'forgeAI.write': 'write',
    'forgeAI.check': 'check',
    'forgeAI.checkAfter': 'check-after',
    'forgeAI.review': 'review',
    'forgeAI.reviewIndependent': 'review-independent',
    'forgeAI.updateState': 'update-state',
    'forgeAI.query': 'query',
    'forgeAI.help': 'help'
};

/**
 * 获取 Python 可执行文件路径
 */
function getPythonPath(): string {
    const cfg = vscode.workspace.getConfiguration('forgeAI');
    return cfg.get<string>('pythonPath', 'python');
}

/**
 * 获取 forgeai.py 脚本路径
 */
function getScriptPath(extensionRoot: string): string {
    return path.join(extensionRoot, SCRIPTS_DIR, 'forgeai.py');
}

/**
 * 辅助函数：异步执行命令
 */
function execAsync(command: string): Promise<string> {
    return new Promise((resolve, reject) => {
        exec(command, (error: any, stdout: string, stderr: string) => {
            if (error) {
                reject(error);
            } else {
                resolve(stdout);
            }
        });
    });
}

/**
 * 执行 ForgeAI CLI 命令
 */
async function executeForgeAICommand(extensionRoot: string, command: string, args?: string[]) {
    // 检查 forgeai 是否安装
    try {
        const checkResult = await execAsync('python -c "import forgeai_modules"');
        console.log(`ForgeAI 模块检查通过`);
    } catch (error) {
        const errorMsg = 'ForgeAI 未正确安装。请检查 Python 环境和 forgeai_modules。';
        vscode.window.showErrorMessage(errorMsg, '查看安装文档').then(selection => {
            if (selection === '查看安装文档') {
                vscode.env.openExternal(vscode.Uri.parse('https://github.com/your-repo/forge-ai#installation'));
            }
        });
        return;
    }
    
    const scriptPath = getScriptPath(extensionRoot);
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : os.homedir();
    
    const python = getPythonPath();
    const fullArgs = args ? [scriptPath, command, ...args] : [scriptPath, command];
    const fullCommand = `${python} ${fullArgs.join(' ')}`;
    
    console.log(`执行命令：${fullCommand}`);
    vscode.window.showInformationMessage(`执行：forgeai ${command}`);
    
    const terminal = vscode.window.createTerminal('ForgeAI');
    terminal.sendText(fullCommand);
    terminal.show();
}

/**
 * 执行 Python CLI 命令
 */
function runPythonCli(scriptPath: string, args: string[], cwd: string): Promise<string> {
    const python = getPythonPath();
    return new Promise((resolve, reject) => {
        execFile(python, [scriptPath, ...args], {
            cwd,
            maxBuffer: 10 * 1024 * 1024,
            timeout: 60_000,
        }, (error, stdout, stderr) => {
            if (error) {
                reject(new Error(`Python CLI 错误: ${stderr || error.message}`));
            } else {
                resolve(stdout);
            }
        });
    });
}

export function activate(context: vscode.ExtensionContext) {
    const extensionRoot = context.extensionPath;
    console.log('ForgeAI 扩展激活');

    // 注册所有命令
    for (const [commandId, cliCommand] of Object.entries(COMMAND_MAP)) {
        const disposable = vscode.commands.registerCommand(commandId, async () => {
            await executeForgeAICommand(extensionRoot, cliCommand);
        });
        context.subscriptions.push(disposable);
        console.log(`注册命令：${commandId} -> ${cliCommand}`);
    }

    // 带参数的命令：check
    const checkCmd = vscode.commands.registerCommand('forgeAI.checkWithChapter', async () => {
        const chapter = await vscode.window.showInputBox({
            prompt: '请输入章节号',
            placeHolder: '例如：20'
        });
        
        if (chapter) {
            await executeForgeAICommand(extensionRoot, 'check', [chapter]);
        }
    });
    context.subscriptions.push(checkCmd);

    // 带参数的命令：reviewIndependent
    const reviewIndependentCmd = vscode.commands.registerCommand('forgeAI.reviewIndependentWithChapter', async () => {
        const chapter = await vscode.window.showInputBox({
            prompt: '请输入章节号',
            placeHolder: '例如：20'
        });
        
        if (chapter) {
            await executeForgeAICommand(extensionRoot, 'check', [chapter, '--independent']);
        }
    });
    context.subscriptions.push(reviewIndependentCmd);

    // ====== 1. 初始化创作套件 ======
    // 新命令
    const initCmd = vscode.commands.registerCommand('forgeAI.init', async () => {
        // 调用相同的初始化逻辑
        vscode.commands.executeCommand('forgeAI.initKit');
    });
    
    // 旧命令（保持兼容）
    const initKitCmd = vscode.commands.registerCommand('forgeAI.initKit', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('请先打开一个工作区目录');
            return;
        }

        const root = workspaceFolders[0].uri.fsPath;

        // 选择启动模式
        const mode = await vscode.window.showQuickPick(
            [
                { label: '标准模式', description: '从零开始：样板书分析→脑暴→设定→大纲→正文', value: 'standard' },
                { label: '灵活模式', description: '导入旧稿继续写，或从灵感切入', value: 'flexible' },
                { label: '参考模式', description: '根据样板书自动生成文风/套路/节奏', value: 'reference' },
            ],
            { placeHolder: '选择启动模式' }
        );

        // 输入项目名称
        const name = await vscode.window.showInputBox({
            prompt: '输入项目名称',
            value: path.basename(root),
        });

        // 输入题材
        const genre = await vscode.window.showQuickPick(
            ['玄幻', '都市', '仙侠', '科幻', '言情', '历史', '悬疑', '系统流', '游戏', '其他'],
            { placeHolder: '选择题材' }
        );

        // 创建目录结构
        for (const dir of PROJECT_DIRS) {
            const dirPath = path.join(root, dir);
            if (!fs.existsSync(dirPath)) {
                fs.mkdirSync(dirPath, { recursive: true });
            }
        }

        vscode.window.showInformationMessage(`ForgeAI 项目初始化完成：${name}`);
    });
    
    context.subscriptions.push(initCmd);
    context.subscriptions.push(initKitCmd);
}

export function deactivate() {}
