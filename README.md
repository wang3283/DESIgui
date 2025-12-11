# DESI空间代谢组学分析系统

![Build Status](https://github.com/wang3283/DESIgui/workflows/Build%20Windows%20Executable/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-Commercial-red)

## 快速下载

**Windows用户直接下载：**
- 📥 [下载最新版本](https://github.com/wang3283/DESIgui/releases/latest)
- 🔧 [查看所有版本](https://github.com/wang3283/DESIgui/releases)
- 📦 [下载构建产物](https://github.com/wang3283/DESIgui/actions)

## 项目简介

DESI（Desorption Electrospray Ionization）空间代谢组学分析系统是一个功能完整的商业化质谱成像数据分析平台，集成了数据加载、可视化、代谢物注释、质量校准、许可证管理和计费系统。

## 主要功能

### 核心分析功能
- **数据加载与可视化**：支持多种质谱数据格式
- **空间成像图**：二维热图展示代谢物空间分布
- **质谱图分析**：平均质谱图、单点质谱图
- **ROI分析**：感兴趣区域选择与分析
- **多样本比对**：样本间差异分析

### 代谢物注释
- **在线数据库查询**：HMDB数据库集成
- **缓存机制**：本地缓存提升查询速度
- **批量注释**：支持批量代谢物注释
- **多数据源**：支持多个代谢物数据库

### 质量校准
- **Lock Mass校准**：内标物质量校准
- **批量校准**：多样本批量校准
- **校准历史**：校准记录管理

### 商业化功能
- **许可证管理**：客户许可证生成与验证
- **使用量追踪**：分析次数、导出次数统计
- **自动计费**：季度账单自动生成
- **数据完整性**：防篡改验证机制

## 系统要求

### 开发环境
- Python 3.7+
- PyQt5 5.15+
- matplotlib 3.5+
- numpy 1.21+
- pandas 1.3+
- cryptography 3.4+

### Windows打包
- PyInstaller 5.0+
- 所有依赖库（见 requirements.txt）

## 快速开始

### Windows用户（推荐）

**直接下载运行（无需安装Python）：**

1. 访问 [Releases页面](https://github.com/wang3283/DESIgui/releases/latest)
2. 下载 `DESI空间代谢组学分析系统.exe`（主程序）
3. 下载 `许可证管理器.exe`（可选，管理员使用）
4. 双击运行，首次启动需要3-5秒

### macOS/Linux
```bash
# 安装依赖
pip install -r requirements.txt

# 运行主程序
python main_gui_ultimate.py

# 运行许可证管理器
python license_manager_gui.py
```

### 开发者 - 从源码运行

如果你想修改代码或从源码运行：

```bash
# 克隆仓库
git clone https://github.com/wang3283/DESIgui.git
cd DESIgui

# 安装依赖
pip install -r requirements.txt

# 运行主程序
python main_gui_ultimate.py
```

### 开发者 - Windows打包

#### 方式一：GitHub Actions自动编译（推荐）

1. Fork本仓库或推送代码到GitHub
2. GitHub Actions自动编译成exe
3. 在Actions页面下载构建产物
4. 详见：[GitHub自动编译说明.md](GitHub自动编译说明.md)

#### 方式二：使用批处理文件（本地编译）
1. 双击运行 `安装依赖.bat`
2. 双击运行 `打包程序.bat`
3. 在 `dist/` 目录找到生成的 .exe 文件

#### 方式二：手动命令行
```cmd
# 安装依赖
pip install -r requirements.txt

# 运行打包脚本
python build_windows.py

# 选择打包选项（建议选3全部打包）
```

详细步骤请参考 `Windows打包步骤.txt`

## 项目结构

```
desi_gui_v2/
├── main_gui_ultimate.py          # 主程序
├── license_manager_gui.py        # 许可证管理器
├── data_loader.py                # 数据加载
├── database_manager.py           # 数据库管理
├── license_manager_core.py       # 许可证核心
├── usage_tracker.py              # 使用量追踪
├── invoice_generator.py          # 账单生成
├── online_metabolite_annotator.py # 代谢物注释
├── mass_calibration_manager.py   # 质量校准
├── report_generator.py           # 报告生成
├── hmdb_database.db              # HMDB数据库
├── metabolite_cache.db           # 代谢物缓存
├── license_manager.db            # 许可证数据库
├── build_windows.py              # Windows打包脚本
├── requirements.txt              # 依赖清单
├── Windows打包步骤.txt           # 打包指南
└── tests/                        # 测试文件

文档/
├── 启动指南.md                   # 快速启动
├── 使用指南.md                   # 使用说明
├── 商业化计费系统使用说明.md     # 计费系统
├── QUARTERLY_BILLING_GUIDE.md    # 季度计费
├── ADMIN_RENEWAL_GUIDE.md        # 许可证续费
└── LICENSE_UPDATE_GUIDE.md       # 许可证更新
```

## 数据库文件

所有数据库文件均为SQLite格式，完全跨平台兼容（macOS ↔ Windows ↔ Linux）：

- `hmdb_database.db` - HMDB代谢物数据库（约50MB）
- `metabolite_cache.db` - 代谢物查询缓存
- `license_manager.db` - 许可证和客户信息

## 打包说明

### 生成的文件
- `DESI空间代谢组学分析系统.exe` - 主程序（约150-200MB）
- `许可证管理器.exe` - 管理员工具（约100MB）

### 分发
1. 将 .exe 文件复制到目标Windows电脑
2. 双击运行，无需安装Python
3. 首次启动需要3-5秒

## 许可证系统

### 管理员功能
- 客户管理（添加、编辑、删除）
- 许可证生成与续费
- 使用量统计查看
- 季度账单生成

### 用户功能
- 许可证验证
- 使用量自动追踪
- 数据完整性验证

## 技术特性

- **跨平台**：支持 macOS、Windows、Linux
- **数据库兼容**：SQLite跨平台无缝迁移
- **性能优化**：缓存机制、批量处理
- **安全性**：数据加密、防篡改验证
- **可扩展**：模块化设计，易于扩展

## 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_license_properties.py
pytest tests/test_usage_tracker_properties.py
```

## 常见问题

### Windows打包
- **Q**: 提示缺少DLL文件？
- **A**: 安装 Visual C++ Redistributable

### 数据库
- **Q**: 数据库文件可以在不同系统间复制吗？
- **A**: 可以，SQLite完全跨平台兼容

### 许可证
- **Q**: 如何生成新的许可证？
- **A**: 运行许可证管理器，在客户管理中生成

## 更新日志

### v2.0 (2024-12)
- ✅ 导航栏语言统一（移除英文标签）
- ✅ Windows打包支持
- ✅ 完整的商业化计费系统
- ✅ 代谢物缓存数据库
- ✅ 质量校准功能
- ✅ 数据完整性验证

## 许可证

本项目为商业软件，版权所有。

## 联系方式

如有问题或建议，请联系开发团队。

---

**DESI空间代谢组学分析系统** - 专业的质谱成像数据分析平台
