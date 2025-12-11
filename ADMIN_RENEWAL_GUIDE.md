# 管理员License续费处理指南

## 概述

本文档说明管理员如何处理客户的License续费申请。

---

## 客户发送的续费申请示例

客户会通过邮件发送以下格式的续费申请：

```
=================================================
DESI软件 License续费申请
=================================================

申请时间: 2025-12-11 10:30:00

【License信息】
License密钥: DESI-F6F9C4FD-C06344B1-4561
剩余天数: 7 天
状态: 即将过期

【客户信息】
客户ID: CUST-6FA90D6C
客户名称: 张三
公司: 测试公司
邮箱: zhangsan@test.com

【系统信息】
操作系统: Windows 10
机器名称: DESKTOP-ABC123
软件版本: 2.4

【续费需求】
请帮助续费此License，延长使用期限。

【联系方式】
邮箱: zhangsan@test.com
电话: 138-0000-0000

=================================================
请将此信息发送至: license@your-company.com
=================================================
```

---

## 续费处理流程（管理员）

### 步骤1: 接收续费申请

1. **检查邮件**
   - 查看收件箱中的续费申请
   - 确认客户信息完整

2. **验证客户身份**
   - 核对License密钥
   - 核对客户ID
   - 确认是否为有效客户

### 步骤2: 在License Manager中处理

1. **打开License Manager**
   ```bash
   python license_manager_gui.py
   ```

2. **查找客户**
   - 在客户列表中搜索客户名称或License密钥
   - 或使用客户ID查找

3. **编辑客户信息**
   - 双击客户或点击"编辑客户"
   - 修改到期日期
   
   ```
   原到期日期: 2025-12-31
   新到期日期: 2026-12-31  (延长1年)
   ```

4. **保存更改**
   - 点击"保存"
   - 系统会自动更新数据库

### 步骤3: 生成配置文件

#### 方式A: 手动创建（推荐）

1. **创建配置文件**
   ```bash
   # 文件名: license_config.txt
   # 内容:
   license_key=DESI-F6F9C4FD-C06344B1-4561
   expires_at=2026-12-31T23:59:59
   customer_id=CUST-6FA90D6C
   status=active
   billing_mode=per_sample
   ```

2. **保存文件**
   - 保存为 `license_config.txt`
   - 确保使用UTF-8编码

#### 方式B: 使用脚本生成（批量）

```python
# generate_config.py
from database_manager import DatabaseManager

def generate_license_config(customer_id, output_file):
    db = DatabaseManager('license_manager.db', mode='admin')
    customer = db.get_customer(customer_id)
    
    if not customer:
        print(f"客户不存在: {customer_id}")
        return
    
    config_content = f"""license_key={customer['license_key']}
expires_at={customer['expires_at']}
customer_id={customer['customer_id']}
status={customer['status']}
billing_mode={customer['billing_mode']}
"""
    
    with open(output_file, 'w') as f:
        f.write(config_content)
    
    print(f"配置文件已生成: {output_file}")

# 使用
generate_license_config('CUST-6FA90D6C', 'license_config.txt')
```

### 步骤4: 发送给客户

#### 邮件模板

```
主题: License续费完成 - [客户名称]

尊敬的 [客户名称]，

您好！

您的License续费申请已处理完成。

【续费信息】
License密钥: DESI-F6F9C4FD-C06344B1-4561
原到期时间: 2025-12-31
新到期时间: 2026-12-31
续费期限: 1年

【更新步骤】
1. 下载附件中的 license_config.txt 文件
2. 将文件放到以下位置：
   - Windows: C:\Users\用户名\.desi_analytics\license_config.txt
   - macOS/Linux: ~/.desi_analytics/license_config.txt
3. 重启DESI软件
4. 验证更新：打开软件 → 帮助 → License信息

【注意事项】
- 请确保文件放在正确的位置
- 如果目录不存在，请先创建
- 更新后请验证到期时间是否正确

如有任何问题，请随时联系我们。

祝工作顺利！

---
DESI技术支持团队
邮箱: license@your-company.com
电话: 400-XXX-XXXX
```

#### 发送邮件

1. **附加配置文件**
   - 将 `license_config.txt` 作为附件
   - 或压缩后发送（可选）

2. **发送邮件**
   - 使用上述模板
   - 填写客户具体信息
   - 发送

---

## 批量续费处理

### 场景：多个客户同时到期

#### 步骤1: 导出即将到期的客户

```python
# export_expiring_customers.py
from database_manager import DatabaseManager
from datetime import datetime, timedelta
import csv

db = DatabaseManager('license_manager.db', mode='admin')

# 查询30天内到期的客户
expiring_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

customers = db.fetchall('''
    SELECT customer_id, name, email, license_key, expires_at
    FROM customers
    WHERE expires_at <= ? AND status = 'active'
    ORDER BY expires_at
''', (expiring_date,))

# 导出到CSV
with open('expiring_customers.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['客户ID', '姓名', '邮箱', 'License', '到期时间'])
    
    for customer in customers:
        writer.writerow([
            customer['customer_id'],
            customer['name'],
            customer['email'],
            customer['license_key'],
            customer['expires_at']
        ])

print(f"已导出 {len(customers)} 个即将到期的客户")
```

#### 步骤2: 批量延长到期时间

```python
# batch_renew.py
from database_manager import DatabaseManager
from datetime import datetime, timedelta

db = DatabaseManager('license_manager.db', mode='admin')

# 读取客户列表
customer_ids = [
    'CUST-6FA90D6C',
    'CUST-ABC12345',
    'CUST-XYZ67890'
]

# 批量延长1年
for customer_id in customer_ids:
    customer = db.get_customer(customer_id)
    if customer:
        old_expires = customer['expires_at']
        new_expires = (datetime.fromisoformat(old_expires) + timedelta(days=365)).isoformat()
        
        db.update_customer(customer_id, {
            'expires_at': new_expires
        })
        
        print(f"已更新 {customer_id}: {old_expires} → {new_expires}")
```

#### 步骤3: 批量生成配置文件

```python
# batch_generate_configs.py
from database_manager import DatabaseManager
import os

db = DatabaseManager('license_manager.db', mode='admin')

customer_ids = ['CUST-6FA90D6C', 'CUST-ABC12345']

# 创建输出目录
os.makedirs('renewal_configs', exist_ok=True)

for customer_id in customer_ids:
    customer = db.get_customer(customer_id)
    if customer:
        config_content = f"""license_key={customer['license_key']}
expires_at={customer['expires_at']}
customer_id={customer['customer_id']}
status={customer['status']}
billing_mode={customer['billing_mode']}
"""
        
        filename = f"renewal_configs/{customer_id}_license_config.txt"
        with open(filename, 'w') as f:
            f.write(config_content)
        
        print(f"已生成: {filename}")
```

#### 步骤4: 批量发送邮件

```python
# batch_send_emails.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from database_manager import DatabaseManager

def send_renewal_email(customer, config_file):
    # SMTP配置
    smtp_server = "smtp.your-company.com"
    smtp_port = 587
    sender_email = "license@your-company.com"
    sender_password = "your_password"
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = customer['email']
    msg['Subject'] = f"License续费完成 - {customer['name']}"
    
    # 邮件正文
    body = f"""
尊敬的 {customer['name']}，

您好！

您的License续费申请已处理完成。

【续费信息】
License密钥: {customer['license_key']}
新到期时间: {customer['expires_at']}

【更新步骤】
请参考附件中的说明文档。

祝工作顺利！

---
DESI技术支持团队
"""
    
    msg.attach(MIMEText(body, 'plain'))
    
    # 附加配置文件
    with open(config_file, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 
                       f'attachment; filename=license_config.txt')
        msg.attach(part)
    
    # 发送邮件
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"邮件已发送: {customer['email']}")
        return True
    except Exception as e:
        print(f"发送失败: {e}")
        return False

# 批量发送
db = DatabaseManager('license_manager.db', mode='admin')
customer_ids = ['CUST-6FA90D6C', 'CUST-ABC12345']

for customer_id in customer_ids:
    customer = db.get_customer(customer_id)
    config_file = f"renewal_configs/{customer_id}_license_config.txt"
    
    if customer and os.path.exists(config_file):
        send_renewal_email(customer, config_file)
```

---

## 常见问题处理

### Q1: 客户说配置文件不生效

**排查步骤**:
1. 确认文件位置是否正确
2. 确认文件名是否为 `license_config.txt`
3. 确认文件内容格式是否正确
4. 确认客户是否重启了软件

**解决方案**:
```
1. 让客户发送配置文件截图
2. 检查文件内容
3. 如有问题，重新生成并发送
```

### Q2: 客户找不到配置文件存放位置

**解决方案**:
```
Windows用户:
1. 按 Win+R
2. 输入: %USERPROFILE%\.desi_analytics
3. 回车
4. 将配置文件放到此文件夹

macOS/Linux用户:
1. 打开终端
2. 输入: open ~/.desi_analytics
3. 将配置文件放到此文件夹
```

### Q3: 批量续费时出错

**解决方案**:
```python
# 添加错误处理
try:
    db.update_customer(customer_id, {'expires_at': new_expires})
    print(f"✓ {customer_id} 更新成功")
except Exception as e:
    print(f"✗ {customer_id} 更新失败: {e}")
    # 记录到日志
    with open('renewal_errors.log', 'a') as f:
        f.write(f"{customer_id}: {e}\n")
```

---

## 续费记录管理

### 记录续费历史

```python
# 在数据库中添加续费记录表
CREATE TABLE IF NOT EXISTS renewal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    old_expires_at TEXT NOT NULL,
    new_expires_at TEXT NOT NULL,
    renewal_date TEXT NOT NULL,
    renewal_period_days INTEGER,
    processed_by TEXT,
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

# 记录续费
def record_renewal(customer_id, old_expires, new_expires, admin_name):
    from datetime import datetime
    
    db.execute('''
        INSERT INTO renewal_history 
        (customer_id, old_expires_at, new_expires_at, renewal_date, 
         renewal_period_days, processed_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        customer_id,
        old_expires,
        new_expires,
        datetime.now().isoformat(),
        (datetime.fromisoformat(new_expires) - 
         datetime.fromisoformat(old_expires)).days,
        admin_name
    ))
```

---

## 自动化建议

### 1. 自动提醒管理员

```python
# 每天检查即将到期的客户
def check_expiring_licenses():
    db = DatabaseManager('license_manager.db', mode='admin')
    
    # 查询7天内到期的客户
    expiring_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    customers = db.fetchall('''
        SELECT * FROM customers
        WHERE expires_at <= ? AND status = 'active'
    ''', (expiring_date,))
    
    if customers:
        # 发送提醒邮件给管理员
        send_admin_alert(customers)
```

### 2. 自动生成续费报告

```python
# 生成月度续费报告
def generate_monthly_renewal_report():
    db = DatabaseManager('license_manager.db', mode='admin')
    
    # 查询本月续费的客户
    this_month = datetime.now().strftime('%Y-%m')
    
    renewals = db.fetchall('''
        SELECT * FROM renewal_history
        WHERE renewal_date LIKE ?
    ''', (f'{this_month}%',))
    
    # 生成报告
    report = f"本月续费客户数: {len(renewals)}\n"
    for renewal in renewals:
        report += f"- {renewal['customer_id']}: {renewal['renewal_period_days']}天\n"
    
    return report
```

---

## 总结

续费处理的关键步骤：
1. ✅ 接收客户申请
2. ✅ 在License Manager中延长到期时间
3. ✅ 生成配置文件
4. ✅ 发送给客户
5. ✅ 跟踪确认

建议使用批量处理工具提高效率！
