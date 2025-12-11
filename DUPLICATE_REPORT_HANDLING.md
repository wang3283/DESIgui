# 重复报告处理说明

## 概述

系统会自动检测并阻止重复报告的导入，这是一个**保护机制**，防止数据重复和账单错误。

---

## 重复判断标准

报告被认为是重复的，当且仅当以下三个字段**完全匹配**：

1. **License密钥** (`license_key`)
2. **报告日期** (`report_date`)
3. **机器ID** (`machine_id`)

### 示例

```
报告A: License=DESI-12345678, 日期=2025-12-11, 机器=machine-001
报告B: License=DESI-12345678, 日期=2025-12-11, 机器=machine-001
结果: 重复 ✗

报告C: License=DESI-12345678, 日期=2025-12-11, 机器=machine-002
结果: 不重复 ✓ (不同机器)

报告D: License=DESI-12345678, 日期=2025-12-12, 机器=machine-001
结果: 不重复 ✓ (不同日期)
```

---

## 为什么需要重复检测？

### 1. 防止数据重复
- 避免同一份报告被多次导入
- 保持数据库数据的唯一性和准确性

### 2. 防止账单错误
- 防止同一期间的使用量被重复计费
- 确保客户只为实际使用量付费

### 3. 数据完整性
- 维护使用记录的时间线完整性
- 避免统计数据失真

---

## 遇到重复报告时的处理方法

### 场景1: 正常情况（推荐做法）

**情况**: 客户不小心重复发送了同一份报告

**处理**: 
- 系统自动跳过，无需任何操作
- 现有数据已经在数据库中
- 这是**正确的行为**，保护了数据完整性

**错误信息示例**:
```
[ERROR] 导入失败

原因: 重复的报告，已跳过

[INFO] 这是一个重复的报告
客户: 测试客户
报告日期: 2025-12-11
机器ID: abc123...

报告内容:
  - 样本加载: 100
  - 数据导出: 50
  - 代谢物拆分: 25
  - 唯一样本数: 80

[提示] 如需重新导入，请先在数据库中删除旧记录
```

---

### 场景2: 需要更正数据

**情况**: 客户发现之前导出的报告有误，重新导出了正确的报告

**处理步骤**:

#### 方法A: 使用GUI（推荐）

1. 打开License Manager
2. 选择对应的客户
3. 在右侧面板查看"使用记录"
4. 找到需要替换的记录（根据日期和机器ID）
5. 右键点击 → 删除记录
6. 重新导入新报告

#### 方法B: 使用SQL（高级用户）

```sql
-- 1. 连接到数据库
sqlite3 license_manager.db

-- 2. 查看重复记录
SELECT * FROM usage_records 
WHERE license_key = 'DESI-12345678-ABCDEFGH' 
AND report_date = '2025-12-11'
AND machine_id = 'abc123...';

-- 3. 确认后删除
DELETE FROM usage_records 
WHERE license_key = 'DESI-12345678-ABCDEFGH' 
AND report_date = '2025-12-11'
AND machine_id = 'abc123...';

-- 4. 退出
.quit
```

#### 方法C: 使用Python脚本

```python
from database_manager import DatabaseManager

# 连接数据库
db = DatabaseManager('license_manager.db', mode='admin')

# 删除重复记录
db.execute('''
    DELETE FROM usage_records 
    WHERE license_key = ? 
    AND report_date = ? 
    AND machine_id = ?
''', ('DESI-12345678-ABCDEFGH', '2025-12-11', 'abc123...'))

print("[SUCCESS] 旧记录已删除，可以重新导入")
db.close()
```

---

### 场景3: 同一客户多台机器

**情况**: 客户在多台机器上使用软件，每台机器都导出报告

**处理**: 
- 这**不是重复**，系统会正常导入
- 每台机器的`machine_id`不同
- 系统会分别记录每台机器的使用量

**示例**:
```
机器A报告: License=DESI-XXX, 日期=2025-12-11, 机器=machine-001
机器B报告: License=DESI-XXX, 日期=2025-12-11, 机器=machine-002
结果: 两份报告都会成功导入 ✓
```

---

## 技术细节

### 数据库查询

```sql
SELECT id FROM usage_records 
WHERE license_key = ? 
AND report_date = ? 
AND machine_id = ?
```

如果查询返回结果，说明已存在相同的记录，判定为重复。

### 代码实现

```python
def _check_duplicate(self, report_data: Dict) -> bool:
    """检查是否为重复报告"""
    license_key = report_data['license_key']
    report_date = report_data['report_date']
    machine_id = report_data['machine_id']
    
    existing = self.db_manager.fetchone('''
        SELECT id FROM usage_records 
        WHERE license_key = ? AND report_date = ? AND machine_id = ?
    ''', (license_key, report_date, machine_id))
    
    return existing is not None
```

---

## 常见问题

### Q1: 为什么不能自动覆盖旧记录？

**答**: 
- 自动覆盖可能导致数据丢失
- 可能掩盖真正的问题（为什么会有两份报告？）
- 需要管理员明确确认才能替换数据

### Q2: 能否修改重复判断标准？

**答**: 
- 当前标准是最合理的
- `license_key + report_date + machine_id` 唯一标识一份报告
- 修改标准可能导致真正的重复无法检测

### Q3: 如何批量删除重复记录？

**答**:
```python
from database_manager import DatabaseManager

db = DatabaseManager('license_manager.db', mode='admin')

# 删除某个客户的所有记录
db.execute('''
    DELETE FROM usage_records 
    WHERE customer_id = ?
''', ('CUST-12345',))

# 删除某个日期范围的记录
db.execute('''
    DELETE FROM usage_records 
    WHERE report_date >= ? AND report_date <= ?
''', ('2025-10-01', '2025-12-31'))

db.close()
```

### Q4: 重复检测会影响性能吗？

**答**: 
- 不会，查询使用了索引
- 检测速度非常快（毫秒级）
- 对导入流程几乎无影响

---

## 最佳实践

### 客户端

1. **季度结束后只导出一次报告**
2. **确认报告内容正确后再发送**
3. **保留导出的报告文件作为备份**
4. **如需重新导出，联系管理员删除旧记录**

### 管理员

1. **收到重复报告提示时，先确认是否真的重复**
2. **如需替换，先备份数据库**
3. **删除旧记录前，记录下原始数据**
4. **重新导入后，验证数据正确性**

---

## 总结

重复报告检测是一个**重要的保护机制**，它：

✅ 防止数据重复
✅ 防止账单错误
✅ 维护数据完整性
✅ 提供清晰的错误提示
✅ 支持手动替换旧记录

在绝大多数情况下，遇到重复报告提示意味着**系统正常工作**，无需任何操作。只有在确实需要更正数据时，才需要手动删除旧记录后重新导入。
