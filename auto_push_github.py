#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动推送到GitHub脚本
"""

import os
import subprocess
import sys

def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    print("=" * 60)
    print("DESI系统 - 自动推送到GitHub")
    print("=" * 60)
    print()
    
    # 获取当前目录
    current_dir = os.getcwd()
    print(f"当前目录: {current_dir}")
    print()
    
    # 1. 检查Git是否安装
    print("[1/7] 检查Git...")
    code, out, err = run_command("git --version")
    if code != 0:
        print("❌ Git未安装！")
        print("请从 https://git-scm.com/ 下载安装")
        sys.exit(1)
    print(f"✓ {out.strip()}")
    print()
    
    # 2. 初始化Git仓库
    print("[2/7] 初始化Git仓库...")
    if not os.path.exists(".git"):
        code, out, err = run_command("git init")
        if code == 0:
            print("✓ Git仓库初始化成功")
        else:
            print(f"❌ 初始化失败: {err}")
            sys.exit(1)
    else:
        print("✓ Git仓库已存在")
    print()
    
    # 3. 配置Git用户信息（如果需要）
    print("[3/7] 配置Git用户信息...")
    code, out, err = run_command("git config user.name")
    if not out.strip():
        run_command('git config user.name "DESI Developer"')
        print("✓ 设置用户名: DESI Developer")
    else:
        print(f"✓ 用户名: {out.strip()}")
    
    code, out, err = run_command("git config user.email")
    if not out.strip():
        run_command('git config user.email "desi@example.com"')
        print("✓ 设置邮箱: desi@example.com")
    else:
        print(f"✓ 邮箱: {out.strip()}")
    print()
    
    # 4. 添加远程仓库
    print("[4/7] 配置远程仓库...")
    code, out, err = run_command("git remote")
    if "origin" not in out:
        code, out, err = run_command(
            "git remote add origin https://github.com/wang3283/DESIgui.git"
        )
        if code == 0:
            print("✓ 远程仓库添加成功")
        else:
            print(f"❌ 添加失败: {err}")
            sys.exit(1)
    else:
        print("✓ 远程仓库已存在")
        code, out, err = run_command("git remote -v")
        print(out)
    print()
    
    # 5. 添加文件
    print("[5/7] 添加文件到Git...")
    code, out, err = run_command("git add .")
    if code == 0:
        print("✓ 文件添加成功")
    else:
        print(f"⚠️  添加文件时有警告: {err}")
    print()
    
    # 6. 提交
    print("[6/7] 提交更改...")
    commit_message = """Initial commit: DESI空间代谢组学分析系统

主要功能:
- 数据加载与可视化
- 代谢物注释（HMDB数据库）
- 质量校准（Lock Mass）
- 商业化计费系统
- 许可证管理
- Windows打包支持

技术栈:
- Python 3.7+
- PyQt5
- matplotlib
- numpy/pandas
- SQLite数据库

已完成:
✅ 导航栏语言统一
✅ Windows打包脚本
✅ 完整文档
✅ 跨平台数据库兼容
"""
    
    code, out, err = run_command(f'git commit -m "{commit_message}"')
    if code == 0:
        print("✓ 提交成功")
        print(out)
    elif "nothing to commit" in out or "nothing to commit" in err:
        print("✓ 没有新的更改需要提交")
    else:
        print(f"⚠️  提交时有警告: {err}")
    print()
    
    # 7. 推送到GitHub
    print("[7/7] 推送到GitHub...")
    print("尝试推送到 main 分支...")
    
    # 先尝试main分支
    code, out, err = run_command("git push -u origin main")
    
    if code == 0:
        print("✓ 推送成功！")
        print(out)
    else:
        # 如果main失败，尝试master
        print("main分支推送失败，尝试 master 分支...")
        code, out, err = run_command("git push -u origin master")
        
        if code == 0:
            print("✓ 推送成功！")
            print(out)
        else:
            # 两个都失败，尝试强制推送
            print()
            print("⚠️  常规推送失败")
            print("错误信息:", err)
            print()
            print("可能的原因:")
            print("1. 远程仓库已有内容（需要先pull）")
            print("2. 认证失败（需要配置GitHub token）")
            print("3. 文件太大（需要使用Git LFS）")
            print()
            
            response = input("是否尝试强制推送（会覆盖远程内容）? (y/n): ")
            if response.lower() == 'y':
                print()
                print("执行强制推送...")
                code, out, err = run_command("git push -u origin main --force")
                if code != 0:
                    code, out, err = run_command("git push -u origin master --force")
                
                if code == 0:
                    print("✓ 强制推送成功！")
                    print(out)
                else:
                    print("❌ 强制推送也失败了")
                    print("错误:", err)
                    print()
                    print("建议手动操作:")
                    print("1. 检查GitHub仓库是否存在")
                    print("2. 配置GitHub认证（token或SSH）")
                    print("3. 检查网络连接")
                    sys.exit(1)
            else:
                print("取消推送")
                sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ 完成！")
    print("=" * 60)
    print()
    print("GitHub仓库: https://github.com/wang3283/DESIgui.git")
    print()
    print("在Windows上克隆:")
    print("  git clone https://github.com/wang3283/DESIgui.git")
    print()

if __name__ == '__main__':
    main()
