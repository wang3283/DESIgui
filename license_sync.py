#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License在线同步模块
用于自动同步许可证到期时间和状态
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class LicenseSyncManager:
    """License同步管理器"""
    
    # 服务器配置
    SERVER_URL = "https://your-server.com/api/license"
    
    def __init__(self, license_key: str, silent: bool = True):
        """
        初始化同步管理器
        
        参数:
            license_key: 许可证密钥
            silent: 静默模式
        """
        self.license_key = license_key
        self.silent = silent
        self.config_dir = Path.home() / ".desi_analytics"
        self.config_file = self.config_dir / "license_config.txt"
        self.last_sync_file = self.config_dir / "last_sync.txt"
        
        # 同步线程
        self._sync_thread = None
        self._stop_sync = False
    
    def start_background_sync(self, interval_hours: int = 24):
        """
        启动后台同步线程
        
        参数:
            interval_hours: 同步间隔（小时）
        """
        if not HAS_REQUESTS:
            if not self.silent:
                print("[警告] 未安装requests库，无法启用在线同步")
            return
        
        def sync_loop():
            # 延迟启动（避免影响软件启动速度）
            time.sleep(60)
            
            while not self._stop_sync:
                try:
                    self.sync_license_info()
                except Exception as e:
                    if not self.silent:
                        print(f"[警告] License同步失败: {e}")
                
                # 等待下次同步
                time.sleep(interval_hours * 3600)
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        
        if not self.silent:
            print(f"[信息] License后台同步已启动（间隔{interval_hours}小时）")
    
    def stop_background_sync(self):
        """停止后台同步"""
        self._stop_sync = True
    
    def sync_license_info(self) -> Tuple[bool, str]:
        """
        同步许可证信息
        
        返回:
            (是否成功, 消息)
        """
        if not HAS_REQUESTS:
            return (False, "未安装requests库")
        
        try:
            # 发送请求到服务器
            response = requests.post(
                f"{self.SERVER_URL}/check",
                json={
                    'license_key': self.license_key,
                    'client_version': '2.4',
                    'last_sync': self._get_last_sync_time()
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 更新本地配置
                self._update_local_config(data)
                
                # 记录同步时间
                self._save_last_sync_time()
                
                if not self.silent:
                    print(f"[成功] License同步成功")
                    print(f"  到期时间: {data.get('expires_at', 'N/A')}")
                    print(f"  状态: {data.get('status', 'N/A')}")
                
                return (True, "同步成功")
            
            elif response.status_code == 404:
                return (False, "License不存在")
            
            elif response.status_code == 403:
                return (False, "License已被禁用")
            
            else:
                return (False, f"服务器错误: {response.status_code}")
        
        except requests.exceptions.ConnectionError:
            return (False, "无法连接到服务器（离线模式）")
        
        except requests.exceptions.Timeout:
            return (False, "连接超时")
        
        except Exception as e:
            return (False, f"同步失败: {str(e)}")
    
    def _update_local_config(self, server_data: Dict):
        """
        更新本地配置
        
        参数:
            server_data: 服务器返回的数据
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建配置内容
        config_lines = [
            f"license_key={self.license_key}",
            f"expires_at={server_data.get('expires_at', '')}",
            f"status={server_data.get('status', 'active')}",
            f"customer_id={server_data.get('customer_id', '')}",
            f"customer_name={server_data.get('customer_name', '')}",
            f"billing_mode={server_data.get('billing_mode', 'per_sample')}",
            f"last_updated={datetime.now().isoformat()}"
        ]
        
        # 保存到文件
        self.config_file.write_text('\n'.join(config_lines))
        
        if not self.silent:
            print(f"[信息] 本地配置已更新: {self.config_file}")
    
    def _get_last_sync_time(self) -> Optional[str]:
        """获取上次同步时间"""
        if self.last_sync_file.exists():
            try:
                return self.last_sync_file.read_text().strip()
            except:
                pass
        return None
    
    def _save_last_sync_time(self):
        """保存同步时间"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.last_sync_file.write_text(datetime.now().isoformat())
    
    def should_sync_now(self) -> bool:
        """
        判断是否应该立即同步
        
        返回:
            是否需要同步
        """
        last_sync = self._get_last_sync_time()
        
        if not last_sync:
            return True  # 从未同步过
        
        try:
            last_sync_dt = datetime.fromisoformat(last_sync)
            hours_since_sync = (datetime.now() - last_sync_dt).total_seconds() / 3600
            
            # 超过24小时未同步
            return hours_since_sync > 24
        
        except:
            return True
    
    def force_sync(self) -> Tuple[bool, str]:
        """
        强制立即同步
        
        返回:
            (是否成功, 消息)
        """
        if not self.silent:
            print("[信息] 正在同步许可证信息...")
        
        return self.sync_license_info()
    
    def get_local_config(self) -> Dict:
        """
        读取本地配置
        
        返回:
            配置字典
        """
        config = {}
        
        if self.config_file.exists():
            try:
                lines = self.config_file.read_text().strip().split('\n')
                for line in lines:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
            except:
                pass
        
        return config


# 服务器端API示例（Flask）
"""
from flask import Flask, request, jsonify
from database_manager import DatabaseManager

app = Flask(__name__)
db = DatabaseManager('license_manager.db', mode='admin')

@app.route('/api/license/check', methods=['POST'])
def check_license():
    data = request.json
    license_key = data.get('license_key')
    
    if not license_key:
        return jsonify({'error': 'Missing license_key'}), 400
    
    # 从数据库查询许可证信息
    customer = db.fetchone(
        "SELECT * FROM customers WHERE license_key = ?",
        (license_key,)
    )
    
    if not customer:
        return jsonify({'error': 'License not found'}), 404
    
    # 检查状态
    if customer['status'] == 'suspended':
        return jsonify({'error': 'License suspended'}), 403
    
    # 返回最新信息
    return jsonify({
        'license_key': customer['license_key'],
        'expires_at': customer['expires_at'],
        'status': customer['status'],
        'customer_id': customer['customer_id'],
        'customer_name': customer['name'],
        'billing_mode': customer['billing_mode'],
        'server_time': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
"""


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("License同步模块测试")
    print("=" * 60)
    
    # 创建同步管理器
    sync_manager = LicenseSyncManager(
        license_key="DESI-F6F9C4FD-C06344B1-4561",
        silent=False
    )
    
    # 测试是否需要同步
    print("\n[测试] 检查是否需要同步...")
    should_sync = sync_manager.should_sync_now()
    print(f"需要同步: {should_sync}")
    
    # 测试读取本地配置
    print("\n[测试] 读取本地配置...")
    config = sync_manager.get_local_config()
    print(f"本地配置: {config}")
    
    # 测试强制同步（需要服务器）
    print("\n[测试] 尝试同步...")
    success, message = sync_manager.force_sync()
    print(f"同步结果: {message}")
    
    if success:
        # 读取更新后的配置
        config = sync_manager.get_local_config()
        print(f"更新后配置: {config}")
    
    print("\n[信息] 测试完成")
