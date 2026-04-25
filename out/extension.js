"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const os = require("os");
const child_process_1 = require("child_process");
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
/**
 * 获取 Python 可执行文件路径
 */
function getPythonPath() {
    const cfg = vscode.workspace.getConfiguration('forgeAI');
    return cfg.get('pythonPath', 'python');
}
/**
 * 获取 forgeai.py 脚本路径
 */
function getScriptPath(extensionRoot) {
    return path.join(extensionRoot, SCRIPTS_DIR, 'forgeai.py');
}
/**
 * 执行 Python CLI 命令
 */
function runPythonCli(scriptPath, args, cwd) {
    const python = getPythonPath();
    return new Promise((resolve, reject) => {
        (0, child_process_1.execFile)(python, [scriptPath, ...args], {
            cwd,
            maxBuffer: 10 * 1024 * 1024,
            timeout: 60000,
        }, (error, stdout, stderr) => {
            if (error) {
                reject(new Error(`Python CLI 错误: ${stderr || error.message}`));
            }
            else {
                resolve(stdout);
            }
        });
    });
}
function activate(context) {
    const extensionRoot = context.extensionPath;
    // ====== 1. 初始化创作套件 ======
    const initCmd = vscode.commands.registerCommand('forgeAI.initKit', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('请先打开一个工作区目录');
            return;
        }
        const root = workspaceFolders[0].uri.fsPath;
        // 选择启动模式
        const mode = await vscode.window.showQuickPick([
            { label: '标准模式', description: '从零开始：样板书分析→脑暴→设定→大纲→正文', value: 'standard' },
            { label: '灵活模式', description: '导入旧稿继续写，或从灵感切入', value: 'flexible' },
            { label: '参考模式', description: '根据样板书自动生成文风/套路/节奏', value: 'reference' },
        ], { placeHolder: '选择启动模式' });
        // 输入项目名称
        const name = await vscode.window.showInputBox({
            prompt: '输入项目名称',
            value: path.basename(root),
        });
        // 输入题材
        const genre = await vscode.window.showQuickPick(['玄幻', '都市', '仙侠', '科幻', '言情', '历史', '悬疑', '系统流', '游戏', '其他'], { placeHolder: '选择题材' });
        // 1. 创建目录结构
        for (const dir of PROJECT_DIRS) {
            const target = path.join(root, dir);
            if (!fs.existsSync(target)) {
                fs.mkdirSync(target, { recursive: true });
            }
        }
        // 2. 复制技能包文件
        const copyDir = (srcDir, destDir) => {
            if (!fs.existsSync(srcDir)) {
                return;
            }
            if (!fs.existsSync(destDir)) {
                fs.mkdirSync(destDir, { recursive: true });
            }
            const entries = fs.readdirSync(srcDir, { withFileTypes: true });
            for (const entry of entries) {
                const srcPath = path.join(srcDir, entry.name);
                const destPath = path.join(destDir, entry.name);
                if (entry.isDirectory()) {
                    copyDir(srcPath, destPath);
                }
                else if (!fs.existsSync(destPath)) {
                    fs.copyFileSync(srcPath, destPath);
                }
            }
        };
        copyDir(path.join(extensionRoot, SKILLS_DIR), path.join(root, '.forgeai/skills'));
        copyDir(path.join(extensionRoot, CHECKERS_DIR), path.join(root, '.forgeai/checkers'));
        copyDir(path.join(extensionRoot, REFERENCES_DIR), path.join(root, '.forgeai/references'));
        copyDir(path.join(extensionRoot, CONSTITUTION_DIR), path.join(root, '.forgeai/constitution'));
        copyDir(path.join(extensionRoot, TEMPLATES_DIR), path.join(root, '.forgeai/templates'));
        // 复制 Python 后端
        copyDir(path.join(extensionRoot, SCRIPTS_DIR), path.join(root, '.forgeai/scripts'));
        // 3. 复制 SOLOENT.md
        const soloentSrc = path.join(extensionRoot, TEMPLATES_DIR, 'SOLOENT.md');
        const soloentDest = path.join(root, 'SOLOENT.md');
        if (fs.existsSync(soloentSrc) && !fs.existsSync(soloentDest)) {
            fs.copyFileSync(soloentSrc, soloentDest);
        }
        // 4. 复制记忆模板
        const memoryTemplates = ['character_state.md', 'foreshadowing.md', 'strand_tracker.md'];
        for (const tmpl of memoryTemplates) {
            const src = path.join(extensionRoot, TEMPLATES_DIR, tmpl);
            const dest = path.join(root, '.forgeai/memory', tmpl);
            if (fs.existsSync(src) && !fs.existsSync(dest)) {
                fs.copyFileSync(src, dest);
            }
        }
        // 5. 运行 Python 初始化（初始化 state.json + index.db + config.json）
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const result = await runPythonCli(scriptPath, [
                'init',
                '--name', name || path.basename(root),
                '--genre', genre || '未设定',
                '--mode', mode?.value || 'standard',
                '--project-root', root,
            ], root);
            vscode.window.showInformationMessage(`ForgeAI 初始化完成！模式: ${mode?.label || '标准'} | 题材: ${genre || '未设定'}\n打开 SOLOENT.md 开始创作。`);
        }
        catch (e) {
            // Python 不可用时，仍然完成基本初始化
            vscode.window.showWarningMessage(`ForgeAI 基础初始化完成（Python 后端未就绪: ${e.message}）。\n核心技能文件已就位，但 RAG/索引功能需要 Python 环境。`);
        }
    });
    // ====== 2. 六维审查快捷命令 ======
    const reviewCmd = vscode.commands.registerCommand('forgeAI.sixDimReview', async () => {
        const checkers = [
            '爽点检查 (high-point-checker)',
            '一致性检查 (consistency-checker)',
            '节奏检查 (pacing-checker)',
            'OOC检查 (ooc-checker)',
            '连贯性检查 (continuity-checker)',
            '追读力检查 (reader-pull-checker)',
        ];
        const selected = await vscode.window.showQuickPick(checkers, {
            placeHolder: '选择要执行的审查维度',
            canPickMany: true,
        });
        if (selected && selected.length > 0) {
            const checkerNames = selected.map(s => s.match(/\((.+)\)/)?.[1] || s);
            const msg = `请在AI对话中输入：读取 .forgeai/checkers/ 下的 ${checkerNames.join(', ')} .md，对当前章节进行审查。`;
            vscode.window.showInformationMessage(msg, { modal: true });
        }
    });
    // ====== 3. AI味评分 ======
    const scoreCmd = vscode.commands.registerCommand('forgeAI.scoreText', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('请先打开要评分的文本文件');
            return;
        }
        const text = editor.document.getText();
        if (!text.trim()) {
            vscode.window.showErrorMessage('当前文件为空');
            return;
        }
        try {
            const scriptPath = getScriptPath(extensionRoot);
            // 将文本写入临时文件
            const tmpFile = path.join(os.tmpdir(), `forgeai_score_${Date.now()}.txt`);
            fs.writeFileSync(tmpFile, text, 'utf-8');
            const result = await runPythonCli(scriptPath, ['score', tmpFile], editor.document.uri.fsPath);
            const scoreData = JSON.parse(result);
            const panel = vscode.window.createWebviewPanel('forgeAIScore', 'ForgeAI AI味评分', vscode.ViewColumn.Beside, {});
            panel.webview.html = `
                <html><body style="font-family: system-ui; padding: 20px;">
                <h1>AI味评分报告</h1>
                <div style="font-size: 48px; text-align: center; margin: 20px 0;">
                    <span style="color: ${scoreData.score >= 0.6 ? '#4CAF50' : '#f44336'}">
                        ${scoreData.score.toFixed(2)}
                    </span>
                    <span style="font-size: 24px; color: #666">/1.0</span>
                </div>
                <p style="text-align: center; color: #666;">
                    ${scoreData.score >= 0.6 ? '✅ 通过 - 文本足够自然' : '⚠️ 未通过 - 检测到AI痕迹'}
                </p>
                <h2>检测到的AI模式</h2>
                <ul>${(scoreData.detected_patterns || []).map((p) => `<li>${p.name || p.type}: ${p.count || 1}次 (权重${p.weight || 1})</li>`).join('')}</ul>
                <h2>详细分析</h2>
                <pre style="background: #f5f5f5; padding: 10px; white-space: pre-wrap;">${scoreData.details || '无'}</pre>
                </body></html>
            `;
            // 清理临时文件
            try {
                fs.unlinkSync(tmpFile);
            }
            catch { }
        }
        catch (e) {
            vscode.window.showErrorMessage(`评分失败: ${e.message}`);
        }
    });
    // ====== 4. 提取上下文 ======
    const contextCmd = vscode.commands.registerCommand('forgeAI.extractContext', async () => {
        const chapterStr = await vscode.window.showInputBox({
            prompt: '输入当前章节号',
            value: '1',
        });
        if (!chapterStr) {
            return;
        }
        const chapter = parseInt(chapterStr, 10);
        const query = await vscode.window.showInputBox({
            prompt: '补充查询（可选）',
            placeHolder: '如：主角战斗场景',
        });
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const args = ['context', String(chapter)];
            if (query) {
                args.push('--query', query);
            }
            args.push('--project-root', cwd);
            const result = await runPythonCli(scriptPath, args, cwd);
            // 在新文档中显示
            const doc = await vscode.workspace.openTextDocument({
                content: result,
                language: 'markdown',
            });
            await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
        }
        catch (e) {
            vscode.window.showErrorMessage(`上下文提取失败: ${e.message}`);
        }
    });
    // ====== 5. 搜索 ======
    const searchCmd = vscode.commands.registerCommand('forgeAI.search', async () => {
        const query = await vscode.window.showInputBox({
            prompt: '搜索内容',
            placeHolder: '如：主角突破境界',
        });
        if (!query) {
            return;
        }
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const result = await runPythonCli(scriptPath, [
                'search', query, '--project-root', cwd,
            ], cwd);
            const doc = await vscode.workspace.openTextDocument({
                content: result,
                language: 'json',
            });
            await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
        }
        catch (e) {
            vscode.window.showErrorMessage(`搜索失败: ${e.message}`);
        }
    });
    // ====== 6. 项目状态 ======
    const statusCmd = vscode.commands.registerCommand('forgeAI.status', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const result = await runPythonCli(scriptPath, ['status', '--project-root', cwd], cwd);
            const data = JSON.parse(result);
            vscode.window.showInformationMessage(`项目: ${data.project?.name || '未命名'} | ` +
                `进度: 第${data.progress?.current_chapter || 0}章 | ` +
                `实体: ${data.entity_count || 0} | ` +
                `活跃伏笔: ${data.active_foreshadowing || 0} | ` +
                `追读力: ${(data.avg_reading_power || 0).toFixed(2)}`);
        }
        catch (e) {
            vscode.window.showErrorMessage(`获取状态失败: ${e.message}`);
        }
    });
    // ====== 7. 索引章节 ======
    const indexCmd = vscode.commands.registerCommand('forgeAI.indexChapter', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('请先打开要索引的章节文件');
            return;
        }
        const chapterStr = await vscode.window.showInputBox({
            prompt: '输入章节号',
            value: '1',
        });
        if (!chapterStr) {
            return;
        }
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const result = await runPythonCli(scriptPath, [
                'index', chapterStr, editor.document.uri.fsPath,
                '--project-root', cwd,
            ], cwd);
            vscode.window.showInformationMessage(`章节 ${chapterStr} 索引完成: ${result.trim()}`);
        }
        catch (e) {
            vscode.window.showErrorMessage(`索引失败: ${e.message}`);
        }
    });
    // ====== 8. 写作后流水线 ======
    const postWriteCmd = vscode.commands.registerCommand('forgeAI.postWrite', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('请先打开章节文件');
            return;
        }
        const chapterStr = await vscode.window.showInputBox({
            prompt: '输入章节号',
            value: '1',
        });
        if (!chapterStr) {
            return;
        }
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const result = await runPythonCli(scriptPath, [
                'post-write', chapterStr, editor.document.uri.fsPath,
                '--project-root', cwd,
            ], cwd);
            const data = JSON.parse(result);
            const steps = data.steps || {};
            const summary = Object.entries(steps).map(([k, v]) => `${k}: ${v.status}${v.status === 'ok' ? (v.entities !== undefined ? ` (${v.entities}实体,${v.state_changes}变化)` : '') : ' ❌'}`).join(' | ');
            vscode.window.showInformationMessage(`第${chapterStr}章后处理完成: ${summary}`);
        }
        catch (e) {
            vscode.window.showErrorMessage(`后处理失败: ${e.message}`);
        }
    });
    // ====== 9. 写前检查 ======
    const preCheckCmd = vscode.commands.registerCommand('forgeAI.preCheck', async () => {
        const chapterStr = await vscode.window.showInputBox({
            prompt: '输入下一章章节号',
            value: '1',
        });
        if (!chapterStr) {
            return;
        }
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const result = await runPythonCli(scriptPath, [
                'pre-check', chapterStr,
                '--project-root', cwd,
            ], cwd);
            const data = JSON.parse(result);
            const alerts = data.alerts || [];
            if (alerts.length === 0) {
                vscode.window.showInformationMessage(`第${chapterStr}章写前检查: 一切正常`);
            }
            else {
                const alertMsg = alerts.map((a) => `⚠️ ${a.message}`).join('\n');
                vscode.window.showWarningMessage(`第${chapterStr}章有${alerts.length}个提醒:\n${alertMsg}`, { modal: true });
            }
        }
        catch (e) {
            vscode.window.showErrorMessage(`写前检查失败: ${e.message}`);
        }
    });
    // ====== 10. 智能上下文 ======
    const smartContextCmd = vscode.commands.registerCommand('forgeAI.smartContext', async () => {
        const chapterStr = await vscode.window.showInputBox({
            prompt: '输入当前章节号',
            value: '1',
        });
        if (!chapterStr) {
            return;
        }
        const query = await vscode.window.showInputBox({
            prompt: '补充查询（可选）',
            placeHolder: '如：主角战斗场景',
        });
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
        try {
            const scriptPath = getScriptPath(extensionRoot);
            const args = ['smart-context', chapterStr, '--project-root', cwd];
            if (query) {
                args.push('--query', query);
            }
            const result = await runPythonCli(scriptPath, args, cwd);
            const doc = await vscode.workspace.openTextDocument({
                content: result,
                language: 'markdown',
            });
            await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
        }
        catch (e) {
            vscode.window.showErrorMessage(`智能上下文失败: ${e.message}`);
        }
    });
    context.subscriptions.push(initCmd, reviewCmd, scoreCmd, contextCmd, searchCmd, statusCmd, indexCmd, postWriteCmd, preCheckCmd, smartContextCmd);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map