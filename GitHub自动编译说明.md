# GitHub Actions 自动编译说明

## 概述

本项目已配置GitHub Actions自动编译工作流，可以自动将Python代码编译成Windows可执行文件（.exe）。

## 工作流说明

### 1. 主构建工作流 (build-windows.yml)

**触发条件：**
- 推送代码到 `main` 或 `master` 分支
- 推送版本标签（如 `v1.0.0`）
- 手动触发
- Pull Request

**构建内容：**
- DESI空间代谢组学分析系统.exe（主程序）
- 许可证管理器.exe（管理工具）

**构建环境：**
- Windows Server 2022
- Python 3.9
- PyInstaller 5.0+

**输出位置：**
- Artifacts（构建产物）：保存30天
- Release（发布版本）：永久保存（仅标签触发）

### 2. 测试构建工作流 (test-build.yml)

**触发条件：**
- 每周日自动运行
- 手动触发

**测试内容：**
- 多Python版本兼容性测试（3.8-3.11）
- 跨平台测试（Windows/macOS/Linux）
- 依赖安装测试
- 快速构建测试

## 使用方法

### 方式一：推送代码自动构建

1. 推送代码到GitHub：
```bash
cd "/Volumes/US100 256G/mouse DESI data/desi_gui_v2"
git add .
git commit -m "Update code"
git push origin main
```

2. 等待构建完成（约10-15分钟）

3. 下载构建产物：
   - 访问：https://github.com/wang3283/DESIgui/actions
   - 点击最新的工作流运行
   - 在 "Artifacts" 部分下载 `DESI-Windows-Executables`

### 方式二：手动触发构建

1. 访问：https://github.com/wang3283/DESIgui/actions

2. 选择 "Build Windows Executable" 工作流

3. 点击 "Run workflow" 按钮

4. 选择分支（通常是 main）

5. 点击绿色的 "Run workflow" 按钮

6. 等待构建完成后下载产物

### 方式三：创建Release版本

1. 创建版本标签：
```bash
cd "/Volumes/US100 256G/mouse DESI data/desi_gui_v2"
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

2. GitHub Actions自动构建并创建Release

3. 访问：https://github.com/wang3283/DESIgui/releases

4. 下载最新版本的 .exe 文件

## 构建流程

```
┌─────────────────┐
│  推送代码/标签   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Actions  │
│   自动触发      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  设置环境       │
│  - Windows VM   │
│  - Python 3.9   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  安装依赖       │
│  - PyQt5        │
│  - matplotlib   │
│  - numpy等      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PyInstaller    │
│  编译主程序     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PyInstaller    │
│  编译管理器     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  打包产物       │
│  - 主程序.exe   │
│  - 管理器.exe   │
│  - 文档         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  上传Artifacts  │
│  或创建Release  │
└─────────────────┘
```

## 查看构建状态

### 在GitHub网页上查看

1. 访问：https://github.com/wang3283/DESIgui/actions

2. 查看工作流运行列表：
   - ✅ 绿色勾：构建成功
   - ❌ 红色叉：构建失败
   - 🟡 黄色圆：正在构建

3. 点击具体的运行查看详细日志

### 在README中显示状态徽章

在 README.md 中添加：

```markdown
![Build Status](https://github.com/wang3283/DESIgui/workflows/Build%20Windows%20Executable/badge.svg)
```

效果：![Build Status](https://github.com/wang3283/DESIgui/workflows/Build%20Windows%20Executable/badge.svg)

## 下载构建产物

### 从Artifacts下载（需要登录GitHub）

1. 访问：https://github.com/wang3283/DESIgui/actions

2. 点击最新的成功构建

3. 滚动到底部的 "Artifacts" 部分

4. 点击 `DESI-Windows-Executables` 下载（ZIP格式）

5. 解压后得到：
   - DESI空间代谢组学分析系统.exe
   - 许可证管理器.exe
   - README.md
   - 使用文档

### 从Release下载（公开访问）

1. 访问：https://github.com/wang3283/DESIgui/releases

2. 选择最新版本

3. 在 "Assets" 部分直接下载 .exe 文件

4. 无需登录，任何人都可以下载

## 版本管理

### 语义化版本号

推荐使用语义化版本号：`v主版本.次版本.修订号`

- **主版本**：重大功能变更或不兼容的API修改
- **次版本**：新增功能，向后兼容
- **修订号**：Bug修复，向后兼容

示例：
```bash
# 第一个正式版本
git tag -a v1.0.0 -m "Initial release"

# 新增功能
git tag -a v1.1.0 -m "Add metabolite annotation"

# Bug修复
git tag -a v1.1.1 -m "Fix database connection issue"

# 推送标签
git push origin v1.1.1
```

### 开发版本

对于开发中的版本，使用日期标识：
- 自动生成：`dev-20241211`
- 手动标记：`v1.0.0-beta`, `v1.0.0-rc1`

## 构建时间

| 任务 | 预计时间 |
|------|---------|
| 环境设置 | 2-3分钟 |
| 安装依赖 | 3-5分钟 |
| 编译主程序 | 3-5分钟 |
| 编译管理器 | 2-3分钟 |
| 打包上传 | 1-2分钟 |
| **总计** | **10-15分钟** |

## 构建限制

### GitHub Actions 免费额度

- **公开仓库**：无限制
- **私有仓库**：
  - 免费账户：2000分钟/月
  - Pro账户：3000分钟/月
  - Team账户：10000分钟/月

### 存储限制

- **Artifacts**：
  - 保存时间：30天（可配置）
  - 总存储：500MB（免费账户）
  
- **Release**：
  - 单个文件：2GB
  - 总存储：无限制

## 故障排查

### 构建失败

1. **依赖安装失败**
   - 检查 requirements.txt 是否正确
   - 查看错误日志中的具体包名

2. **PyInstaller编译失败**
   - 检查是否有语法错误
   - 查看是否缺少隐藏导入

3. **文件缺失**
   - 确保数据库文件已提交到Git
   - 检查 .gitignore 是否排除了必需文件

### 构建成功但无法运行

1. **缺少DLL**
   - 在工作流中添加系统依赖
   - 使用 `--collect-all` 选项

2. **文件路径问题**
   - 使用相对路径
   - 检查 `--add-data` 参数

## 高级配置

### 自定义构建选项

编辑 `.github/workflows/build-windows.yml`：

```yaml
- name: Build with custom options
  run: |
    pyinstaller \
      --name=MyApp \
      --windowed \
      --onefile \
      --icon=icon.ico \
      --add-data="data;data" \
      --hidden-import=mymodule \
      --exclude-module=tkinter \
      main.py
```

### 多平台构建

添加 macOS 和 Linux 构建：

```yaml
jobs:
  build-windows:
    runs-on: windows-latest
    # ... Windows构建步骤
  
  build-macos:
    runs-on: macos-latest
    # ... macOS构建步骤
  
  build-linux:
    runs-on: ubuntu-latest
    # ... Linux构建步骤
```

### 构建缓存

加速构建：

```yaml
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

## 最佳实践

1. **频繁提交**：每次重要更改后提交，触发自动构建
2. **使用标签**：为稳定版本创建标签，自动发布Release
3. **查看日志**：构建失败时仔细查看日志
4. **测试本地**：推送前在本地测试构建
5. **文档更新**：更新README和版本说明

## 相关链接

- GitHub Actions文档：https://docs.github.com/actions
- PyInstaller文档：https://pyinstaller.org/
- 项目仓库：https://github.com/wang3283/DESIgui
- Actions页面：https://github.com/wang3283/DESIgui/actions
- Releases页面：https://github.com/wang3283/DESIgui/releases

## 总结

使用GitHub Actions自动编译的优势：

✅ **自动化**：推送代码即自动构建
✅ **跨平台**：在云端Windows环境构建
✅ **版本管理**：自动创建Release
✅ **免费**：公开仓库完全免费
✅ **可靠**：标准化的构建环境
✅ **分发**：直接从GitHub下载

现在你只需要推送代码，GitHub会自动帮你编译成exe文件！
