# License更新同步指南

## 概述

本文档说明如何更新客户的License到期时间，以及客户端如何同步这些更新。

---

## 三种更新方式对比

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **配置文件** | 简单、快速 | 需要手动操作 | 少量客户、离线环境 |
| **新License** | 安全、可追溯 | 需要重新激活 | 重要客户、安全要求高 |
| **在线同步** | 自动、无感知 | 需要网络 | 大量客户、在线环境 |

---

## 方式1: 配置文件更新（推荐用于离线环境）

### 管理员操作

1. **在License Manager中延长到期时间**
   ```
   编辑客户 → 修改到期日期 → 保存
   例如: 2025-12-31 → 2026-12-31
   ```

2. **生成配置文件**
   ```bash
   # 创建 license_config.txt
   license_key=DESI-F6F9C4FD-C06344B1-4561
   expires_at=2026-12-31T23:59:59
   customer_id=CUST-6FA90D6C
   status=active
   billing_mode=per_sample
   ```

3. **发送给客户**
   - 通过邮件发送配置文件
   - 或通过U盘/网盘传递

### 客户操作

1. **下载配置文件**
   - 保存为 `license_config.txt`

2. **放到指定位置**
   ```bash
   # Windows
   C:\Users\用户名\.desi_analytics\license_config.txt
   
   # macOS/Linux
   ~/.desi_analytics/license_config.txt
   ```

3. **重启软件**
   - 软件会自动读取新配置
   - 无需其他操作

### 验证更新

```python
# 客户可以在软件中查看License信息
打开软件 → 帮助 → License信息
查看到期时间是否已更新
```

---

## 方式2: 新License密钥（推荐用于安全要求高的场景）

### 管理员操作

1. **生成新License**
   ```
   License Manager → 编辑客户 → 生成新License
   新License: DESI-A1B2C3D4-E5F6G7H8-9I0J
   ```

2. **设置新到期时间**
   ```
   到期日期: 2026-12-31
   保存
   ```

3. **通知客户**
   ```
   邮件内容:
   ---
   尊敬的客户，
   
   您的License已续费，新的License密钥为：
   DESI-A1B2C3D4-E5F6G7H8-9I0J
   
   到期时间: 2026-12-31
   
   请在软件中更新License。
   ---
   ```

### 客户操作

1. **打开软件**

2. **更新License**
   ```
   方式A: 菜单更新
   帮助 → 更新License → 输入新密钥 → 确定
   
   方式B: 过期提醒
   如果已过期，启动时会提示 → 点击"更新License" → 输入新密钥
   ```

3. **重启软件**
   - 新License立即生效

### 验证更新

```python
# 查看License信息
帮助 → License信息
确认License密钥和到期时间已更新
```

---

## 方式3: 在线自动同步（推荐用于大规模部署）

### 系统架构

```
┌─────────────────┐         ┌─────────────────┐
│  License Manager│         │  License Server │
│  (管理员端)      │────────▶│  (API服务器)    │
│                 │  更新    │                 │
└─────────────────┘         └─────────────────┘
                                     ▲
                                     │ 定期查询
                                     │ (每24小时)
                            ┌────────┴────────┐
                            │  DESI软件       │
                            │  (客户端)       │
                            └─────────────────┘
```

### 服务器端部署

1. **安装依赖**
   ```bash
   pip install flask requests
   ```

2. **启动License服务器**
   ```bash
   python license_server.py
   # 监听端口: 5000
   ```

3. **配置域名（可选）**
   ```
   https://license.your-company.com
   ```

### 管理员操作

1. **在License Manager中更新**
   ```
   编辑客户 → 修改到期时间 → 保存
   ```

2. **数据自动同步到服务器**
   - License Manager和服务器共享数据库
   - 或通过API同步

### 客户端自动同步

1. **启动时检查**
   ```python
   # 软件启动时
   if should_sync_now():  # 超过24小时未同步
       sync_license_info()  # 后台同步
   ```

2. **后台定期同步**
   ```python
   # 每24小时自动同步一次
   while True:
       sync_license_info()
       sleep(24 * 3600)
   ```

3. **静默更新**
   - 无需用户操作
   - 自动更新本地配置
   - 下次启动生效

### 客户端集成

```python
# 在主程序中添加
from license_sync import LicenseSyncManager

# 初始化
sync_manager = LicenseSyncManager(
    license_key=license_key,
    silent=True
)

# 启动后台同步
sync_manager.start_background_sync(interval_hours=24)

# 启动时立即同步（如果需要）
if sync_manager.should_sync_now():
    success, message = sync_manager.force_sync()
    if success:
        print("License信息已更新")
```

---

## 混合方案（推荐）

结合多种方式，提供最佳用户体验：

### 优先级策略

```
1. 尝试在线同步（如果有网络）
   ↓ 失败
2. 检查配置文件更新
   ↓ 失败
3. 提示用户手动更新License
```

### 实现代码

```python
def update_license_info():
    # 1. 尝试在线同步
    if has_network():
        success, _ = sync_manager.force_sync()
        if success:
            return True
    
    # 2. 检查配置文件
    config = read_config_file()
    if config and config['expires_at'] > current_expires:
        update_local_config(config)
        return True
    
    # 3. 提示手动更新
    if is_expired():
        show_update_dialog()
    
    return False
```

---

## 常见问题

### Q1: 客户离线很久，如何更新？

**A:** 使用配置文件方式
```
1. 管理员生成配置文件
2. 通过U盘/邮件发送
3. 客户放到指定位置
4. 重启软件
```

### Q2: 更新后需要重启软件吗？

**A:** 取决于更新方式
- 配置文件: 需要重启
- 新License: 需要重启
- 在线同步: 下次启动生效（或实时生效，看实现）

### Q3: 如何验证更新成功？

**A:** 查看License信息
```
软件菜单 → 帮助 → License信息
检查到期时间是否正确
```

### Q4: 更新失败怎么办？

**A:** 排查步骤
```
1. 检查配置文件位置是否正确
2. 检查配置文件格式是否正确
3. 检查License密钥是否正确
4. 查看软件日志文件
5. 联系技术支持
```

### Q5: 可以批量更新多个客户吗？

**A:** 可以
```
方式1: 批量生成配置文件
for customer in customers:
    generate_config_file(customer)
    send_email(customer)

方式2: 在线同步（自动）
update_database()  # 所有客户自动同步
```

---

## 安全建议

1. **配置文件加密**
   ```python
   # 可选：加密配置文件
   encrypted_config = encrypt(config_content)
   save_file(encrypted_config)
   ```

2. **License密钥保护**
   - 不要在邮件中明文发送
   - 使用加密附件
   - 或通过安全通道传递

3. **服务器安全**
   - 使用HTTPS
   - API认证
   - 限流保护

4. **日志记录**
   ```python
   # 记录所有更新操作
   log_update(
       customer_id=customer_id,
       old_expires=old_expires,
       new_expires=new_expires,
       update_method='online_sync',
       timestamp=now()
   )
   ```

---

## 总结

| 场景 | 推荐方式 |
|------|---------|
| 离线环境 | 配置文件 |
| 少量客户 | 配置文件或新License |
| 大量客户 | 在线同步 |
| 高安全要求 | 新License + 加密 |
| 混合环境 | 在线同步 + 配置文件备用 |

选择合适的更新方式，可以提供最佳的用户体验和管理效率！
