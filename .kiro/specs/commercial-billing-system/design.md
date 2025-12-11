# 商业化计费系统设计文档

## 概述

本设计文档描述了DESI空间代谢组学分析系统的商业化计费系统的完整架构和实现方案。系统包含三个主要组件：

1. **License Manager GUI** - 管理员使用的桌面应用程序
2. **Usage Tracker** - 集成在客户端软件中的追踪模块
3. **Customer Portal** - 客户自助服务Web门户（可选）

系统采用离线优先的设计理念，支持无网络环境下的完整功能，通过加密的使用报告文件进行数据交换。

## 架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     商业化计费系统架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  客户端软件       │         │  License Manager │             │
│  │  (DESI GUI)      │         │  (管理员工具)     │             │
│  │                  │         │                  │             │
│  │  ┌────────────┐  │         │  ┌────────────┐ │             │
│  │  │Usage       │  │  .enc   │  │Customer    │ │             │
│  │  │Tracker     │──┼────────▶│  │Management  │ │             │
│  │  └────────────┘  │  文件   │  └────────────┘ │             │
│  │                  │         │  ┌────────────┐ │             │
│  │  ┌────────────┐  │         │  │Invoice     │ │             │
│  │  │License     │  │         │  │Generator   │ │             │
│  │  │Validator   │  │         │  └────────────┘ │             │
│  │  └────────────┘  │         │  ┌────────────┐ │             │
│  │                  │         │  │Report      │ │             │
│  │  SQLite DB       │         │  │Analytics   │ │             │
│  │  (本地加密)       │         │  └────────────┘ │             │
│  └──────────────────┘         │                  │             │
│                               │  SQLite DB       │             │
│                               │  (管理数据库)     │             │
│                               └──────────────────┘             │
│                                                                 │
│  ┌──────────────────────────────────────────────┐              │
│  │  Customer Portal (可选Web界面)                │              │
│  │  • License验证登录                            │              │
│  │  • 使用统计查看                               │              │
│  │  • 账单历史下载                               │              │
│  │  • 在线续费支付                               │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流

1. **使用记录流程**:
   - 客户使用软件 → Usage Tracker记录 → 本地SQLite加密存储
   - 定期导出 → 生成.enc加密文件 → 发送给管理员

2. **账单生成流程**:
   - 管理员导入.enc文件 → 解密验证 → 更新使用记录
   - 选择客户 → 配置计费参数 → 生成账单 → 导出PDF/Excel

3. **License管理流程**:
   - 管理员创建客户 → 生成License → 发送给客户
   - 客户输入License → 软件验证 → 激活功能


## 组件和接口

### 1. License Manager GUI (管理员工具)

#### 主窗口组件
- **CustomerListWidget**: 客户列表，支持搜索、排序和筛选
- **CustomerDetailPanel**: 客户详情面板，显示基本信息和统计数据
- **UsageChartWidget**: 使用量图表，可视化展示趋势
- **InvoiceListWidget**: 账单列表，显示历史账单
- **ToolBar**: 工具栏，包含常用操作按钮
- **StatusBar**: 状态栏，显示系统状态和通知

#### 对话框组件
- **CreateCustomerDialog**: 创建客户对话框
- **EditCustomerDialog**: 编辑客户对话框
- **ImportReportDialog**: 导入使用报告对话框（支持拖拽）
- **GenerateInvoiceDialog**: 生成账单对话框
- **BillingConfigDialog**: 计费配置对话框
- **EmailTemplateDialog**: 邮件模板编辑对话框
- **BackupRestoreDialog**: 备份恢复对话框

#### 核心类

```python
class LicenseManagerGUI(QMainWindow):
    """License管理器主窗口"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.license_generator = LicenseGenerator()
        self.invoice_generator = InvoiceGenerator()
        self.email_service = EmailService()
        self.report_analyzer = ReportAnalyzer()
    
    def create_customer(self, customer_data: Dict) -> str:
        """创建新客户，返回customer_id"""
        pass
    
    def import_usage_report(self, report_file: str) -> Dict:
        """导入使用报告，返回导入结果"""
        pass
    
    def generate_invoice(self, customer_id: str, config: Dict) -> str:
        """生成账单，返回invoice_id"""
        pass
    
    def send_email(self, recipients: List[str], template: str, data: Dict):
        """发送邮件通知"""
        pass
```

### 2. Usage Tracker (客户端追踪模块)

#### 核心类

```python
class UsageTracker:
    """使用量追踪器"""
    
    def __init__(self, license_key: str = None):
        self.license_key = license_key or self._load_license()
        self.machine_id = self._get_machine_id()
        self.db = LocalDatabase()
        self.encryptor = DataEncryptor(self.machine_id)
    
    def record_usage(self, action_type: str, sample_name: str, 
                     details: Dict = None) -> str:
        """记录使用情况，返回record_id"""
        pass
    
    def get_usage_stats(self, days: int = 30) -> Dict:
        """获取使用统计"""
        pass
    
    def export_report(self, output_file: str, days: int = 30) -> bool:
        """导出加密的使用报告"""
        pass
    
    def verify_integrity(self) -> Dict:
        """验证数据完整性"""
        pass
```

#### License验证器

```python
class LicenseValidator:
    """License验证器"""
    
    def validate(self, license_key: str) -> Dict:
        """验证License，返回验证结果和到期信息"""
        pass
    
    def check_expiry(self, license_key: str) -> int:
        """检查到期时间，返回剩余天数"""
        pass
    
    def should_show_reminder(self, days_left: int) -> Tuple[bool, str]:
        """判断是否显示提醒，返回(是否显示, 提醒级别)"""
        pass
```

### 3. 数据库管理器

#### 管理员数据库Schema

```sql
-- 客户表
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    license_key TEXT UNIQUE NOT NULL,
    billing_mode TEXT DEFAULT 'per_sample',  -- per_sample, per_operation, subscription, hybrid
    unit_price REAL DEFAULT 10.0,
    subscription_fee REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- active, expired, suspended
    notes TEXT
);

-- 使用记录表
CREATE TABLE usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    license_key TEXT NOT NULL,
    machine_id TEXT,
    report_date TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    total_samples_loaded INTEGER DEFAULT 0,
    total_exports INTEGER DEFAULT 0,
    total_splits INTEGER DEFAULT 0,
    unique_samples INTEGER DEFAULT 0,
    imported_at TEXT NOT NULL,
    report_file TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 账单表
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT UNIQUE NOT NULL,
    customer_id TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    billing_mode TEXT NOT NULL,
    total_samples INTEGER DEFAULT 0,
    total_operations INTEGER DEFAULT 0,
    unit_price REAL DEFAULT 0.0,
    subscription_fee REAL DEFAULT 0.0,
    subtotal REAL DEFAULT 0.0,
    tax_rate REAL DEFAULT 0.0,
    tax_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, sent, paid, overdue
    created_at TEXT NOT NULL,
    sent_at TEXT,
    paid_at TEXT,
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 邮件日志表
CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT,
    email_type TEXT NOT NULL,  -- invoice, reminder, welcome, custom
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    status TEXT DEFAULT 'sent',  -- sent, failed, pending
    error_message TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 备份记录表
CREATE TABLE backup_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_file TEXT NOT NULL,
    backup_type TEXT NOT NULL,  -- full, incremental
    created_at TEXT NOT NULL,
    file_size INTEGER,
    checksum TEXT
);
```

#### 客户端数据库Schema

```sql
-- 使用记录表
CREATE TABLE usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    action_type TEXT NOT NULL,  -- load_sample, export_data, split_metabolites
    sample_name TEXT NOT NULL,
    sample_hash TEXT NOT NULL,
    details_encrypted TEXT,
    reported INTEGER DEFAULT 0,
    report_time TEXT,
    checksum TEXT NOT NULL
);

-- 统计表
CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    samples_loaded INTEGER DEFAULT 0,
    samples_exported INTEGER DEFAULT 0,
    samples_split INTEGER DEFAULT 0,
    total_operations INTEGER DEFAULT 0
);

-- License信息表
CREATE TABLE license_info (
    id INTEGER PRIMARY KEY,
    license_key TEXT NOT NULL,
    activated_at TEXT NOT NULL,
    expires_at TEXT,
    last_validated TEXT
);
```


## 数据模型

### Customer (客户)
```python
@dataclass
class Customer:
    customer_id: str
    name: str
    email: str
    company: str
    license_key: str
    billing_mode: str  # per_sample, per_operation, subscription, hybrid
    unit_price: float
    subscription_fee: float
    created_at: datetime
    expires_at: datetime
    status: str  # active, expired, suspended
    notes: str = ""
```

### UsageRecord (使用记录)
```python
@dataclass
class UsageRecord:
    customer_id: str
    license_key: str
    machine_id: str
    report_date: datetime
    period_start: datetime
    period_end: datetime
    total_samples_loaded: int
    total_exports: int
    total_splits: int
    unique_samples: int
    imported_at: datetime
    report_file: str
```

### Invoice (账单)
```python
@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    period_start: datetime
    period_end: datetime
    billing_mode: str
    total_samples: int
    total_operations: int
    unit_price: float
    subscription_fee: float
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    status: str  # pending, sent, paid, overdue
    created_at: datetime
    sent_at: Optional[datetime]
    paid_at: Optional[datetime]
    notes: str = ""
```

### UsageReport (使用报告)
```python
@dataclass
class UsageReport:
    report_generated: datetime
    license_key: str
    machine_id: str
    usage_stats: Dict
    integrity_check: Dict
    encrypted_data: str
```

## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1: License唯一性
*对于任意* 两个不同的客户创建操作，生成的License密钥应该是唯一的，不存在重复
**验证: 需求 1.3**

### 属性 2: 客户ID唯一性
*对于任意* 两个不同的客户创建操作，生成的客户ID应该是唯一的，不存在重复
**验证: 需求 1.3**

### 属性 3: 数据库更新一致性
*对于任意* 有效的客户信息修改，数据库中的记录应该被正确更新，且修改前后的customer_id保持不变
**验证: 需求 1.5**

### 属性 4: 报告解密成功性
*对于任意* 由系统生成的加密报告，使用正确的机器ID或License密钥应该能够成功解密
**验证: 需求 2.2, 2.3**

### 属性 5: 重复报告检测
*对于任意* 已导入的使用报告，再次导入相同的报告应该被系统检测并警告
**验证: 需求 2.5**

### 属性 6: 按样本数计费正确性
*对于任意* 客户和任意单价，使用"按样本数"模式计算的总金额应该等于唯一样本数乘以单价
**验证: 需求 3.2**

### 属性 7: 按操作次数计费正确性
*对于任意* 客户和任意单价，使用"按操作次数"模式计算的总金额应该等于总操作次数乘以单价
**验证: 需求 3.3**

### 属性 8: 固定订阅计费正确性
*对于任意* 使用"固定订阅"模式的客户，账单金额应该等于订阅费，与使用量无关
**验证: 需求 3.4**

### 属性 9: 账单导出完整性
*对于任意* 生成的账单，导出为PDF或Excel后，文件应该包含所有必要的账单信息且格式正确
**验证: 需求 3.5**

### 属性 10: 使用记录自动性
*对于任意* 用户操作（加载样本、导出数据、拆分代谢物），系统应该自动创建对应的使用记录
**验证: 需求 4.2**

### 属性 11: 报告导出加密性
*对于任意* 使用数据，导出的报告文件应该是加密的，且能够被管理员工具正确解密（round-trip属性）
**验证: 需求 4.4, 6.4**

### 属性 12: License验证正确性
*对于任意* License密钥，系统应该能够正确验证其有效性和到期时间
**验证: 需求 5.1**

### 属性 13: 到期提醒触发性
*对于任意* 剩余天数在30天以内的License，系统应该显示相应级别的续费提醒
**验证: 需求 5.2, 5.3**

### 属性 14: 过期License功能限制
*对于任意* 已过期的License，系统应该限制核心功能，只允许查看历史数据和导出报告
**验证: 需求 5.4**

### 属性 15: License更新生效性
*对于任意* 有效的新License密钥，系统应该验证并更新，立即恢复所有功能
**验证: 需求 5.5**

### 属性 16: 校验和存在性
*对于任意* 使用记录，系统应该计算并存储基于机器ID的校验和
**验证: 需求 6.1**

### 属性 17: 完整性验证全面性
*对于任意* 导入的使用报告，系统应该验证所有记录的完整性，检测任何篡改
**验证: 需求 6.2**

### 属性 18: 唯一样本统计正确性
*对于任意* 样本加载记录列表，"按样本数"模式应该只统计唯一的样本，忽略重复加载
**验证: 需求 7.2**

### 属性 19: 操作次数统计正确性
*对于任意* 操作记录列表，"按操作次数"模式应该统计所有操作，包括加载、导出和拆分
**验证: 需求 7.3**

### 属性 20: 订阅制计费固定性
*对于任意* 使用"订阅制"模式的客户，无论使用量多少，费用应该是固定的订阅费
**验证: 需求 7.4**

### 属性 21: 混合模式计费正确性
*对于任意* 使用量，"混合模式"计费应该正确计算基础订阅费加上超额使用费
**验证: 需求 7.5**

### 属性 22: 收入趋势计算正确性
*对于任意* 账单数据集，收入趋势图应该正确反映按时间段的收入总和
**验证: 需求 8.2**

### 属性 23: 客户活跃度统计正确性
*对于任意* 客户数据集和时间段，活跃客户数应该等于在该时间段内有使用记录的客户数
**验证: 需求 8.3**

### 属性 24: 使用模式统计正确性
*对于任意* 使用记录集，最常用功能应该是操作次数最多的功能类型
**验证: 需求 8.4**

### 属性 25: 报表导出格式正确性
*对于任意* 报表数据，导出为Excel、PDF或CSV后，文件应该格式正确且包含完整数据
**验证: 需求 8.5**

### 属性 26: 客户门户认证正确性
*对于任意* 有效的License密钥，客户应该能够成功登录自助门户并查看个人数据
**验证: 需求 9.2**

### 属性 27: 使用历史完整性
*对于任意* 客户，使用历史应该包含该客户的所有使用记录，按时间排序
**验证: 需求 9.3**

### 属性 28: 账单历史完整性
*对于任意* 客户，账单历史应该包含该客户的所有历史账单，无遗漏
**验证: 需求 9.4**

### 属性 29: 续费提示显示性
*对于任意* 即将到期的License（剩余天数≤30），客户门户应该显示续费按钮和提示
**验证: 需求 9.5**

### 属性 30: 批量操作正确性
*对于任意* 客户集合和批量操作类型，系统应该对集合中的每个客户正确执行操作
**验证: 需求 10.1**

### 属性 31: 自动账单生成准时性
*对于任意* 设置了自动账单生成的日期，系统应该在该日期为所有符合条件的客户生成账单
**验证: 需求 10.2**

### 属性 32: 到期提醒自动发送性
*对于任意* 即将到期的License，系统应该自动发送提醒邮件给对应客户
**验证: 需求 10.3**

### 属性 33: 批量导入处理正确性
*对于任意* 使用报告文件集合，批量导入应该正确处理每个文件，显示成功和失败的统计
**验证: 需求 10.4**

### 属性 34: 账单邮件自动发送性
*对于任意* 生成的账单，系统应该自动发送邮件给客户，附带PDF附件
**验证: 需求 11.1**

### 属性 35: License到期邮件发送性
*对于任意* 即将到期的License，系统应该发送提醒邮件，包含续费信息
**验证: 需求 11.2**

### 属性 36: 欢迎邮件发送性
*对于任意* 新创建的客户，系统应该发送欢迎邮件，包含License密钥和使用指南
**验证: 需求 11.3**

### 属性 37: 备份完整性
*对于任意* 数据库状态，备份操作应该创建包含所有表和记录的完整副本
**验证: 需求 12.1**

### 属性 38: 自动备份定时性
*对于任意* 系统运行时间超过7天的情况，系统应该自动创建增量备份
**验证: 需求 12.2**

### 属性 39: 备份验证正确性
*对于任意* 备份文件，恢复前的验证应该能够检测文件是否完整和有效
**验证: 需求 12.3**

### 属性 40: 恢复前备份保护性
*对于任意* 恢复操作，系统应该先备份当前数据，然后再执行恢复
**验证: 需求 12.4**


## 错误处理

### 1. License相关错误

#### 无效License
- **场景**: 用户输入的License密钥格式错误或不存在
- **处理**: 显示友好的错误消息，提示正确的License格式，提供联系支持的方式
- **恢复**: 允许用户重新输入或联系管理员

#### License过期
- **场景**: License已超过有效期
- **处理**: 限制核心功能，显示明显的过期提示和续费指引
- **恢复**: 用户输入新的License后立即恢复功能

#### License验证失败
- **场景**: 网络问题或服务器不可达导致验证失败
- **处理**: 使用本地缓存的验证结果，允许离线使用一定时间（如7天）
- **恢复**: 网络恢复后自动重新验证

### 2. 数据库相关错误

#### 数据库损坏
- **场景**: SQLite数据库文件损坏或无法打开
- **处理**: 尝试自动修复，如果失败则创建新数据库，保留原文件作为备份
- **恢复**: 提示用户从备份恢复或联系技术支持

#### 数据库锁定
- **场景**: 多个进程同时访问数据库导致锁定
- **处理**: 实现重试机制，最多重试3次，每次间隔1秒
- **恢复**: 如果重试失败，提示用户关闭其他可能占用数据库的程序

#### 磁盘空间不足
- **场景**: 写入数据库时磁盘空间不足
- **处理**: 捕获异常，显示清晰的错误消息，建议清理磁盘空间
- **恢复**: 用户清理空间后自动重试

### 3. 加密解密错误

#### 解密失败
- **场景**: 使用报告文件无法解密
- **处理**: 尝试多种解密方法（已知机器ID、License密钥），记录失败日志
- **恢复**: 提示管理员提供机器ID或联系客户

#### 加密密钥丢失
- **场景**: 客户端加密密钥丢失或损坏
- **处理**: 使用机器ID重新生成密钥，继续记录新数据
- **恢复**: 历史数据可能无法解密，但不影响新数据记录

### 4. 邮件发送错误

#### SMTP连接失败
- **场景**: 无法连接到邮件服务器
- **处理**: 将邮件加入待发送队列，定期重试
- **恢复**: 网络恢复后自动发送队列中的邮件

#### 邮件格式错误
- **场景**: 邮件地址格式错误或收件人不存在
- **处理**: 记录错误日志，标记邮件为失败状态
- **恢复**: 管理员更正邮件地址后可重新发送

#### 附件过大
- **场景**: 账单PDF文件过大，超过邮件服务器限制
- **处理**: 压缩PDF或提供下载链接代替附件
- **恢复**: 自动切换到下载链接模式

### 5. 文件操作错误

#### 文件不存在
- **场景**: 尝试导入不存在的使用报告文件
- **处理**: 显示文件选择对话框，提示用户选择正确的文件
- **恢复**: 用户选择正确文件后继续

#### 文件权限不足
- **场景**: 无法读取或写入文件
- **处理**: 显示权限错误消息，建议以管理员权限运行或更改文件权限
- **恢复**: 用户修改权限后重试

#### 文件格式错误
- **场景**: 导入的文件不是有效的使用报告格式
- **处理**: 验证文件格式，显示详细的错误信息
- **恢复**: 提示用户选择正确的.enc文件

### 6. 网络相关错误

#### 连接超时
- **场景**: 客户端上报使用数据时网络超时
- **处理**: 将数据保存到本地队列，稍后自动重试
- **恢复**: 网络恢复后自动上报队列中的数据

#### 服务器错误
- **场景**: 服务器返回5xx错误
- **处理**: 记录错误日志，使用指数退避策略重试
- **恢复**: 服务器恢复后自动重试

### 7. 数据完整性错误

#### 校验和不匹配
- **场景**: 使用记录的校验和验证失败，可能被篡改
- **处理**: 标记记录为可疑，在账单中注明，不计入计费
- **恢复**: 联系客户确认数据真实性

#### 重复记录
- **场景**: 检测到重复的使用记录或账单
- **处理**: 显示警告，询问用户是否继续或跳过
- **恢复**: 用户选择处理方式

## 测试策略

### 单元测试

单元测试覆盖各个独立组件的功能，确保每个函数和类方法按预期工作。

#### License管理器测试
- 测试客户创建功能，验证生成的ID和License唯一性
- 测试License验证逻辑，包括有效、过期、无效等情况
- 测试数据库CRUD操作的正确性

#### 使用追踪器测试
- 测试使用记录的创建和存储
- 测试校验和计算的正确性
- 测试报告导出和加密功能

#### 账单生成器测试
- 测试各种计费模式的计算逻辑
- 测试账单格式化和导出功能
- 测试税费计算的准确性

#### 加密解密测试
- 测试Fernet加密的正确性
- 测试round-trip加密解密
- 测试不同机器ID的加密兼容性

### 属性测试

属性测试使用Property-Based Testing框架（如Hypothesis for Python）验证系统的通用属性。

**测试框架**: Hypothesis (Python)
**配置**: 每个属性测试至少运行100次迭代

#### 测试示例

```python
from hypothesis import given, strategies as st
import hypothesis

# 属性1: License唯一性
@given(st.lists(st.tuples(st.text(), st.emails(), st.text()), min_size=2, max_size=100))
def test_license_uniqueness(customer_data_list):
    """
    **Feature: commercial-billing-system, Property 1: License唯一性**
    对于任意两个不同的客户创建操作，生成的License密钥应该是唯一的
    """
    manager = LicenseManager()
    licenses = []
    
    for name, email, company in customer_data_list:
        result = manager.create_customer(name, email, company)
        licenses.append(result['license_key'])
    
    # 验证所有License都是唯一的
    assert len(licenses) == len(set(licenses))

# 属性11: 报告导出加密性 (Round-trip)
@given(st.dictionaries(
    st.text(min_size=1), 
    st.integers(min_value=0, max_value=1000),
    min_size=1
))
def test_report_encryption_roundtrip(usage_data):
    """
    **Feature: commercial-billing-system, Property 11: 报告导出加密性**
    对于任意使用数据，导出的报告应该能够被正确解密
    """
    tracker = UsageTracker()
    
    # 导出加密报告
    report_file = "/tmp/test_report.enc"
    tracker.export_report(report_file, usage_data)
    
    # 导入并解密
    manager = LicenseManager()
    result = manager.import_usage_report(report_file, tracker.machine_id)
    
    # 验证解密成功且数据一致
    assert result['success'] == True
    assert result['usage_stats'] == usage_data

# 属性6: 按样本数计费正确性
@given(
    st.integers(min_value=1, max_value=1000),  # unique_samples
    st.floats(min_value=0.01, max_value=1000.0)  # unit_price
)
def test_per_sample_billing_correctness(unique_samples, unit_price):
    """
    **Feature: commercial-billing-system, Property 6: 按样本数计费正确性**
    对于任意客户和单价，按样本数计费应该等于样本数乘以单价
    """
    invoice_gen = InvoiceGenerator()
    
    usage_data = {'unique_samples': unique_samples}
    invoice = invoice_gen.calculate_amount(
        billing_mode='per_sample',
        usage_data=usage_data,
        unit_price=unit_price
    )
    
    expected_amount = unique_samples * unit_price
    assert abs(invoice['total_amount'] - expected_amount) < 0.01  # 浮点数比较容差
```

### 集成测试

集成测试验证多个组件协同工作的场景。

#### 端到端工作流测试
1. 创建客户 → 生成License → 客户端激活
2. 客户使用软件 → 记录使用 → 导出报告
3. 管理员导入报告 → 生成账单 → 发送邮件

#### GUI集成测试
- 使用PyQt测试框架模拟用户交互
- 验证UI组件之间的数据流
- 测试拖拽、点击等用户操作

#### 数据库集成测试
- 测试并发访问场景
- 测试事务的原子性和一致性
- 测试数据迁移和升级

### 性能测试

#### 负载测试
- 测试1000+客户的管理性能
- 测试大量使用记录的导入速度
- 测试报表生成的响应时间

#### 压力测试
- 测试数据库在高并发下的表现
- 测试大文件（100MB+）的加密解密性能
- 测试批量操作的内存使用

### 安全测试

#### 加密强度测试
- 验证Fernet加密的安全性
- 测试密钥派生的随机性
- 测试防暴力破解能力

#### SQL注入测试
- 测试所有数据库查询的参数化
- 验证用户输入的清理和验证

#### 权限测试
- 测试文件权限的正确设置
- 验证敏感数据的访问控制
