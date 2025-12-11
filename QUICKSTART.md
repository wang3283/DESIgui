# 快速开始指南

## 🚀 5分钟上手

### Windows用户（最简单）

1. **下载程序**
   - 访问：https://github.com/wang3283/DESIgui/releases/latest
   - 下载：`DESI空间代谢组学分析系统.exe`

2. **运行程序**
   - 双击 .exe 文件
   - 首次启动需要3-5秒
   - 如果Windows提示"未知发行商"，点击"仍要运行"

3. **开始使用**
   - 点击"打开工作目录"加载数据
   - 选择包含质谱数据的文件夹
   - 开始分析！

### macOS/Linux用户

```bash
# 1. 克隆仓库
git clone https://github.com/wang3283/DESIgui.git
cd DESIgui

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python main_gui_ultimate.py
```

## 📦 获取exe文件的三种方式

### 方式一：从Release下载（推荐）

**优点**：最简单，无需登录
**步骤**：
1. 访问：https://github.com/wang3283/DESIgui/releases
2. 选择最新版本
3. 在"Assets"下载 .exe 文件

### 方式二：从Actions下载

**优点**：获取最新构建
**步骤**：
1. 访问：https://github.com/wang3283/DESIgui/actions
2. 点击最新的成功构建（绿色勾）
3. 滚动到底部"Artifacts"
4. 下载 `DESI-Windows-Executables.zip`
5. 解压得到 .exe 文件

**注意**：需要登录GitHub账号

### 方式三：自己编译

**优点**：可以修改代码
**步骤**：
1. 克隆仓库到Windows电脑
2. 运行 `安装依赖.bat`
3. 运行 `打包程序.bat`
4. 在 `dist/` 目录找到 .exe 文件

## 🔧 开发者快速开始

### 1. 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/wang3283/DESIgui.git
cd DESIgui

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行程序

```bash
# 主程序
python main_gui_ultimate.py

# 许可证管理器
python license_manager_gui.py
```

### 3. 修改代码

主要文件：
- `main_gui_ultimate.py` - 主程序界面
- `data_loader.py` - 数据加载
- `online_metabolite_annotator.py` - 代谢物注释
- `license_manager_core.py` - 许可证管理

### 4. 测试修改

```bash
# 运行测试
pytest tests/

# 检查语法
python -m py_compile main_gui_ultimate.py
```

### 5. 提交代码

```bash
git add .
git commit -m "Your changes"
git push origin main
```

GitHub Actions会自动编译新版本！

## 🎯 使用GitHub Actions自动编译

### 自动触发

推送代码后，GitHub自动编译：

```bash
git add .
git commit -m "Update features"
git push origin main
```

等待10-15分钟，在Actions页面下载编译好的exe。

### 手动触发

1. 访问：https://github.com/wang3283/DESIgui/actions
2. 选择"Build Windows Executable"
3. 点击"Run workflow"
4. 选择分支，点击"Run workflow"
5. 等待构建完成

### 创建Release版本

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

GitHub自动创建Release，任何人都可以下载！

## 📚 下一步

- 📖 阅读 [完整文档](使用指南.md)
- 🔧 查看 [GitHub自动编译说明](GitHub自动编译说明.md)
- 💼 了解 [商业化计费系统](商业化计费系统使用说明.md)
- 🐛 遇到问题？查看 [常见问题](#常见问题)

## ❓ 常见问题

### Q: exe文件太大？
A: 正常的，包含了Python和所有库，约150-200MB。

### Q: 杀毒软件报警？
A: 这是误报，PyInstaller打包的程序常被误报，添加到白名单即可。

### Q: 启动很慢？
A: 首次启动需要解压，约3-5秒，后续会快一些。

### Q: 提示缺少DLL？
A: 安装 Visual C++ Redistributable：
   https://aka.ms/vs/17/release/vc_redist.x64.exe

### Q: 如何更新到新版本？
A: 下载新版本的exe文件，替换旧文件即可。数据库文件可以保留。

### Q: 数据库文件在哪里？
A: 与exe文件同目录，或在用户文档目录。

### Q: 如何获取许可证？
A: 联系管理员，使用"许可证管理器.exe"生成。

## 🆘 获取帮助

- 📧 提交Issue：https://github.com/wang3283/DESIgui/issues
- 📖 查看文档：项目根目录的各种 .md 文件
- 💬 讨论区：https://github.com/wang3283/DESIgui/discussions

---

**开始使用DESI空间代谢组学分析系统！** 🎉
