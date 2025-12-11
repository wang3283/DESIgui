# 季度计费使用指南

## 概述

本系统采用**季度后付费**模式：客户先使用软件，季度结束后导出使用报告，管理员审核并生成账单，客户付费后延长License。

---

## 计费模式

- **计费周期**: 每季度（3个月）
- **计费依据**: 样本处理次数（load_sample操作）
- **付费方式**: 后付费（先使用后付费）
- **License延期**: 付费后延长3个月

---

## 完整流程

```
季度开始 → 客户使用软件 → 季度结束 → 
客户导出报告 → 发送给管理员 → 管理员导入审核 → 
生成账单 → 客户付费 → 管理员延长License → 
发送新配置文件 → 客户更新 → 下个季度开始
```

---

## 客户端操作

### 1. 日常使用（自动记录）

软件会自动记录所有操作：
- 加载样本（load_sample）
- 导出数据（export_data）
- 拆分代谢物（split_metabolites）

**无需任何手动操作**，系统在后台静默记录。

### 2. 季度结束导出报告

#### 方式A: 使用GUI（推荐）

```
1. 打开DESI软件
2. 菜单 → 工具 → 导出使用报告
3. 选择报告期间（默认最近30天，可选90天）
4. 点击"导出"
5. 保存为 .enc 文件
```

#### 方式B: 使用代码

```python
from usage_tracker import UsageTracker

# 初始化追踪器
tracker = UsageTracker()

# 导出季度报告（90天）
tracker.export_usage_report(
    output_file='2025_Q4_usage_report.enc',
    days=90
)

print("报告已导出")
```

### 3. 发送报告给管理员

```
邮件主题: 2025年Q4季度使用报告 - [您的公司名称]

邮件内容:
---
尊敬的管理员，

附件是我们2025年第4季度的使用报告。

客户信息:
- 公司: [您的公司]
- License: DESI-XXXXXXXX-YYYYYYYY-CCCC
- 联系人: [姓名]
- 邮箱: [邮箱]

请审核并发送账单。

谢谢！
---

附件: 2025_Q4_usage_report.enc
```

### 4. 收到账单后付费

管理员会发送账单邮件，包含：
- 使用统计（样本数、导出次数等）
- 计费金额
- 付款方式

### 5. 付费后更新License

收到管理员发送的配置文件后：

```
1. 下载 license_config.txt
2. 放到指定位置:
   - Windows: C:\Users\用户名\.desi_analytics\license_config.txt
   - macOS/Linux: ~/.desi_analytics/license_config.txt
3. 重启软件
4. 验证: 帮助 → License信息
```

---

## 管理员操作

### 1. 接收客户报告

检查邮箱中的季度使用报告（.enc文件）

### 2. 导入报告到License Manager

#### 方式A: 使用GUI（推荐）

```
1. 打开License Manager
   python license_manager_gui.py

2. 菜单 → 文件 → 导入使用报告 (Ctrl+I)

3. 选择客户发送的 .enc 文件
   或直接拖拽文件到窗口

4. 系统自动:
   - 解密报告
   - 识别客户
   - 验证完整性
   - 保存到数据库

5. 查看导入结果
```

#### 方式B: 使用代码

```python
from database_manager import DatabaseManager
from quarterly_billing_workflow import QuarterlyBillingWorkflow

# 初始化
db = DatabaseManager('license_manager.db', mode='admin')
workflow = QuarterlyBillingWorkflow(db)

# 导入报告
success, message, report = workflow.import_quarterly_report(
    report_file='2025_Q4_usage_report.enc'
)

if success:
    print(f"导入成功: {message}")
    print(f"客户: {report['customer_id']}")
    print(f"样本数: {report['usage_summary']['total_samples_loaded']}")
else:
    print(f"导入失败: {message}")
```

### 3. 审核使用数据

在License Manager中查看客户使用统计：

```
1. 选择客户
2. 查看右侧详情面板
3. 检查使用记录是否合理
```

### 4. 生成账单

#### 使用GUI

```
1. 选择客户
2. 点击"生成账单"按钮 (Ctrl+G)
3. 选择计费期间（季度）
4. 确认单价（默认使用客户设置的单价）
5. 点击"生成"
6. 系统自动计算:
   - 样本总数
   - 小计 = 样本数 × 单价
   - 税额 = 小计 × 6%
   - 总计 = 小计 + 税额
```

#### 使用代码

```python
# 生成季度账单
invoice = workflow.generate_quarterly_invoice(
    customer_id='CUST-6FA90D6C',
    quarter='2025-Q4',
    unit_price=10.0  # 10元/样本
)

print(f"账单ID: {invoice['invoice_id']}")
print(f"样本数: {invoice['total_samples']}")
print(f"总金额: ¥{invoice['total_amount']:.2f}")
```

### 5. 发送账单给客户

```
邮件主题: 2025年Q4季度账单 - [客户公司名称]

邮件内容:
---
尊敬的 [客户名称]，

您好！

附件是您2025年第4季度的使用账单。

【账单摘要】
账单编号: INV-2025-Q4-CUST-XXXXXX
计费期间: 2025-10-01 至 2025-12-31

【使用统计】
样本加载: 1,250 次
数据导出: 450 次
代谢物拆分: 320 次

【费用明细】
单价: ¥10.00/样本
样本数: 1,250
小计: ¥12,500.00
税费(6%): ¥750.00
总计: ¥13,250.00

【付款方式】
银行转账:
  账户名称: XXX公司
  账号: XXXX-XXXX-XXXX-XXXX
  开户行: XX银行XX支行

请在收到账单后7个工作日内完成付款。
付款后请告知我们，我们将立即延长您的License。

如有任何问题，请随时联系我们。

谢谢！

---
DESI技术支持团队
邮箱: billing@your-company.com
电话: 400-XXX-XXXX
---
```

### 6. 确认付款

收到客户付款后：

```python
# 标记账单已付款
workflow.mark_invoice_paid(
    invoice_id='INV-2025-Q4-CUST-6FA90D6C',
    payment_date='2025-12-15'
)
```

### 7. 延长License

```python
# 延长License 3个月（一个季度）
success, new_expires = workflow.extend_license_after_payment(
    customer_id='CUST-6FA90D6C',
    months=3
)

print(f"License已延长至: {new_expires}")
```

### 8. 生成并发送配置文件

```python
# 生成配置文件
config = workflow.generate_license_config(
    customer_id='CUST-6FA90D6C',
    output_file='CUST-6FA90D6C_license_config.txt'
)

print("配置文件已生成，请发送给客户")
```

发送邮件：

```
邮件主题: License已延期 - [客户公司名称]

邮件内容:
---
尊敬的 [客户名称]，

您好！

我们已确认收到您的付款，感谢您的支持！

您的License已延长至: 2026-03-31

【更新步骤】
1. 下载附件 license_config.txt
2. 放到指定位置（见下方说明）
3. 重启DESI软件
4. 验证更新成功

【文件位置】
Windows: C:\Users\用户名\.desi_analytics\license_config.txt
macOS/Linux: ~/.desi_analytics/license_config.txt

如有任何问题，请随时联系我们。

祝工作顺利！

---
DESI技术支持团队
---

附件: license_config.txt
```

---

## 批量处理（多个客户）

### 批量导入报告

```python
import os
from pathlib import Path

# 获取所有报告文件
report_dir = Path('quarterly_reports')
report_files = list(report_dir.glob('*.enc'))

results = []
for report_file in report_files:
    success, message, report = workflow.import_quarterly_report(
        str(report_file)
    )
    results.append({
        'file': report_file.name,
        'success': success,
        'message': message
    })

# 打印结果
for r in results:
    status = "✓" if r['success'] else "✗"
    print(f"{status} {r['file']}: {r['message']}")
```

### 批量生成账单

```python
# 获取所有需要生成账单的客户
customers = db.fetchall('''
    SELECT DISTINCT customer_id 
    FROM usage_records
    WHERE report_date >= '2025-10-01' 
    AND report_date <= '2025-12-31'
''')

for customer in customers:
    customer_id = customer['customer_id']
    
    try:
        invoice = workflow.generate_quarterly_invoice(
            customer_id=customer_id,
            quarter='2025-Q4'
        )
        print(f"✓ {customer_id}: ¥{invoice['total_amount']:.2f}")
    except Exception as e:
        print(f"✗ {customer_id}: {e}")
```

---

## 常见问题

### Q1: 报告导入失败，提示"无法解密"

**原因**: License密钥不匹配

**解决**:
1. 确认客户在License Manager中存在
2. 确认License密钥正确
3. 让客户重新导出报告

### Q2: 导入成功但显示"重复报告"

**原因**: 该季度报告已经导入过（基于License密钥、报告日期和机器ID的组合判断）

**解决方法**:

**方法1: 保留现有记录（推荐）**
- 这是正常的保护机制，防止重复导入
- 系统会自动跳过重复报告
- 现有数据已经在数据库中，无需重新导入

**方法2: 替换旧记录（如果数据有误需要更正）**
1. 在License Manager中找到该客户
2. 查看使用记录列表
3. 找到对应日期的记录并删除
4. 重新导入新报告

**方法3: 使用SQL直接删除（高级用户）**
```sql
-- 查看重复记录
SELECT * FROM usage_records 
WHERE license_key = 'DESI-XXXXXXXX-YYYYYYYY' 
AND report_date = '2025-12-11';

-- 删除重复记录
DELETE FROM usage_records 
WHERE license_key = 'DESI-XXXXXXXX-YYYYYYYY' 
AND report_date = '2025-12-11' 
AND machine_id = 'abc123...';
```

### Q3: 客户说配置文件不生效

**排查**:
1. 文件位置是否正确
2. 文件名是否为 `license_config.txt`
3. 是否重启了软件

### Q4: 如何修改单价？

**方法1**: 在客户信息中修改默认单价
```
编辑客户 → 修改"单价"字段 → 保存
```

**方法2**: 生成账单时指定单价
```python
invoice = workflow.generate_quarterly_invoice(
    customer_id='CUST-XXX',
    quarter='2025-Q4',
    unit_price=15.0  # 指定单价
)
```

### Q5: 如何查看历史账单？

```python
# 查询客户的所有账单
invoices = db.list_invoices(customer_id='CUST-6FA90D6C')

for inv in invoices:
    print(f"{inv['invoice_id']}: ¥{inv['total_amount']} - {inv['status']}")
```

---

## 数据安全

### 报告加密

- 使用客户的License密钥加密
- 采用Fernet对称加密（AES-128）
- 管理员只能解密自己客户的报告

### 完整性验证

- 每条使用记录都有SHA256校验和
- 防止数据篡改
- 导入时自动验证

### 隐私保护

- 样本名称加密存储
- 机器ID哈希处理
- 只统计数量，不泄露具体内容

---

## 总结

季度计费流程的关键点：

1. ✅ **自动记录** - 客户无需手动操作
2. ✅ **季度导出** - 客户导出加密报告
3. ✅ **管理员导入** - 自动解密和识别
4. ✅ **生成账单** - 自动计算费用
5. ✅ **付费延期** - 付费后延长License
6. ✅ **配置更新** - 发送配置文件给客户

整个流程简单、安全、高效！
