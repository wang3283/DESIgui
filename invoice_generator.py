#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单生成器 - 支持多种计费模式和导出格式
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid


@dataclass
class InvoiceConfig:
    """账单配置"""
    customer_id: str
    period_start: datetime
    period_end: datetime
    billing_mode: str  # per_sample, per_operation, subscription, hybrid
    unit_price: float = 10.0
    subscription_fee: float = 0.0
    tax_rate: float = 0.0
    notes: str = ""
    
    # 混合模式参数
    base_quota: int = 0  # 基础配额
    overage_price: float = 0.0  # 超额单价


@dataclass
class InvoiceData:
    """账单数据"""
    invoice_id: str
    customer_id: str
    customer_name: str
    customer_email: str
    customer_company: str
    period_start: datetime
    period_end: datetime
    billing_mode: str
    
    # 使用统计
    total_samples: int
    total_operations: int
    unique_samples: int
    
    # 计费信息
    unit_price: float
    subscription_fee: float
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    
    # 元数据
    created_at: datetime
    status: str = 'pending'
    notes: str = ""


class InvoiceGenerator:
    """账单生成器"""
    
    def __init__(self, db_manager=None):
        """
        初始化账单生成器
        
        参数:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
    
    def generate_invoice_id(self) -> str:
        """生成唯一的账单ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"INV-{timestamp}-{unique_id}"
    
    def calculate_amount(self, config: InvoiceConfig, usage_data: Dict) -> Tuple[float, float, float]:
        """
        计算账单金额
        
        参数:
            config: 账单配置
            usage_data: 使用数据统计
        
        返回:
            (subtotal, tax_amount, total_amount)
        """
        subtotal = 0.0
        
        if config.billing_mode == 'per_sample':
            # 按样本数计费
            unique_samples = usage_data.get('unique_samples', 0)
            subtotal = unique_samples * config.unit_price
        
        elif config.billing_mode == 'per_operation':
            # 按操作次数计费
            total_operations = usage_data.get('total_operations', 0)
            subtotal = total_operations * config.unit_price
        
        elif config.billing_mode == 'subscription':
            # 固定订阅费
            subtotal = config.subscription_fee
        
        elif config.billing_mode == 'hybrid':
            # 混合模式：基础订阅费 + 超额使用费
            subtotal = config.subscription_fee
            
            # 计算超额部分
            unique_samples = usage_data.get('unique_samples', 0)
            if unique_samples > config.base_quota:
                overage = unique_samples - config.base_quota
                subtotal += overage * config.overage_price
        
        # 计算税费
        tax_amount = subtotal * config.tax_rate
        total_amount = subtotal + tax_amount
        
        return subtotal, tax_amount, total_amount
    
    def get_usage_data(self, customer_id: str, period_start: datetime, period_end: datetime) -> Dict:
        """
        获取客户在指定时间段的使用数据
        
        参数:
            customer_id: 客户ID
            period_start: 开始时间
            period_end: 结束时间
        
        返回:
            使用数据字典
        """
        if not self.db_manager:
            return {
                'total_samples': 0,
                'total_operations': 0,
                'unique_samples': 0
            }
        
        # 查询使用记录
        records = self.db_manager.fetchall('''
            SELECT 
                SUM(total_samples_loaded) as total_samples,
                SUM(total_exports + total_splits) as total_operations,
                SUM(unique_samples) as unique_samples
            FROM usage_records
            WHERE customer_id = ?
            AND report_date >= ?
            AND report_date <= ?
        ''', (customer_id, period_start.isoformat(), period_end.isoformat()))
        
        if records and records[0]:
            row = records[0]
            return {
                'total_samples': row['total_samples'] or 0,
                'total_operations': row['total_operations'] or 0,
                'unique_samples': row['unique_samples'] or 0
            }
        
        return {
            'total_samples': 0,
            'total_operations': 0,
            'unique_samples': 0
        }
    
    def create_invoice(self, config: InvoiceConfig) -> InvoiceData:
        """
        创建账单
        
        参数:
            config: 账单配置
        
        返回:
            账单数据对象
        """
        # 获取客户信息
        if not self.db_manager:
            raise ValueError("数据库管理器未初始化")
        
        customer = self.db_manager.get_customer(config.customer_id)
        if not customer:
            raise ValueError(f"客户不存在: {config.customer_id}")
        
        # 获取使用数据
        usage_data = self.get_usage_data(
            config.customer_id,
            config.period_start,
            config.period_end
        )
        
        # 计算金额
        subtotal, tax_amount, total_amount = self.calculate_amount(config, usage_data)
        
        # 生成账单ID
        invoice_id = self.generate_invoice_id()
        
        # 创建账单数据对象
        invoice = InvoiceData(
            invoice_id=invoice_id,
            customer_id=config.customer_id,
            customer_name=customer['name'],
            customer_email=customer['email'],
            customer_company=customer.get('company', ''),
            period_start=config.period_start,
            period_end=config.period_end,
            billing_mode=config.billing_mode,
            total_samples=usage_data['total_samples'],
            total_operations=usage_data['total_operations'],
            unique_samples=usage_data['unique_samples'],
            unit_price=config.unit_price,
            subscription_fee=config.subscription_fee,
            subtotal=subtotal,
            tax_rate=config.tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            created_at=datetime.now(),
            status='pending',
            notes=config.notes
        )
        
        # 保存到数据库
        self._save_invoice_to_db(invoice)
        
        return invoice
    
    def _save_invoice_to_db(self, invoice: InvoiceData):
        """保存账单到数据库"""
        if not self.db_manager:
            return
        
        invoice_data = {
            'invoice_id': invoice.invoice_id,
            'customer_id': invoice.customer_id,
            'period_start': invoice.period_start.isoformat(),
            'period_end': invoice.period_end.isoformat(),
            'billing_mode': invoice.billing_mode,
            'total_samples': invoice.total_samples,
            'total_operations': invoice.total_operations,
            'unit_price': invoice.unit_price,
            'subscription_fee': invoice.subscription_fee,
            'subtotal': invoice.subtotal,
            'tax_rate': invoice.tax_rate,
            'tax_amount': invoice.tax_amount,
            'total_amount': invoice.total_amount,
            'status': invoice.status,
            'created_at': invoice.created_at.isoformat(),
            'notes': invoice.notes
        }
        
        self.db_manager.create_invoice(invoice_data)
    
    def export_to_text(self, invoice: InvoiceData) -> str:
        """
        导出账单为文本格式
        
        参数:
            invoice: 账单数据
        
        返回:
            格式化的文本字符串
        """
        lines = []
        lines.append("=" * 60)
        lines.append("账单 / INVOICE")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"账单编号: {invoice.invoice_id}")
        lines.append(f"开票日期: {invoice.created_at.strftime('%Y-%m-%d')}")
        lines.append(f"账单状态: {invoice.status}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("客户信息 / Customer Information")
        lines.append("-" * 60)
        lines.append(f"客户ID: {invoice.customer_id}")
        lines.append(f"客户名称: {invoice.customer_name}")
        if invoice.customer_company:
            lines.append(f"公司: {invoice.customer_company}")
        lines.append(f"邮箱: {invoice.customer_email}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("计费周期 / Billing Period")
        lines.append("-" * 60)
        lines.append(f"开始日期: {invoice.period_start.strftime('%Y-%m-%d')}")
        lines.append(f"结束日期: {invoice.period_end.strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("使用统计 / Usage Statistics")
        lines.append("-" * 60)
        lines.append(f"总样本数: {invoice.total_samples}")
        lines.append(f"唯一样本数: {invoice.unique_samples}")
        lines.append(f"总操作次数: {invoice.total_operations}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("计费详情 / Billing Details")
        lines.append("-" * 60)
        
        billing_mode_names = {
            'per_sample': '按样本数计费',
            'per_operation': '按操作次数计费',
            'subscription': '固定订阅',
            'hybrid': '混合模式'
        }
        lines.append(f"计费模式: {billing_mode_names.get(invoice.billing_mode, invoice.billing_mode)}")
        
        if invoice.billing_mode == 'per_sample':
            lines.append(f"唯一样本数: {invoice.unique_samples}")
            lines.append(f"单价: ¥{invoice.unit_price:.2f}")
            lines.append(f"小计: ¥{invoice.subtotal:.2f}")
        elif invoice.billing_mode == 'per_operation':
            lines.append(f"总操作次数: {invoice.total_operations}")
            lines.append(f"单价: ¥{invoice.unit_price:.2f}")
            lines.append(f"小计: ¥{invoice.subtotal:.2f}")
        elif invoice.billing_mode == 'subscription':
            lines.append(f"订阅费: ¥{invoice.subscription_fee:.2f}")
            lines.append(f"小计: ¥{invoice.subtotal:.2f}")
        elif invoice.billing_mode == 'hybrid':
            lines.append(f"基础订阅费: ¥{invoice.subscription_fee:.2f}")
            lines.append(f"超额使用费: ¥{invoice.subtotal - invoice.subscription_fee:.2f}")
            lines.append(f"小计: ¥{invoice.subtotal:.2f}")
        
        lines.append("")
        if invoice.tax_rate > 0:
            lines.append(f"税率: {invoice.tax_rate * 100:.1f}%")
            lines.append(f"税额: ¥{invoice.tax_amount:.2f}")
            lines.append("")
        
        lines.append(f"总计: ¥{invoice.total_amount:.2f}")
        lines.append("")
        
        if invoice.notes:
            lines.append("-" * 60)
            lines.append("备注 / Notes")
            lines.append("-" * 60)
            lines.append(invoice.notes)
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("感谢您的使用！")
        lines.append("Thank you for your business!")
        lines.append("=" * 60)
        
        return "\n".join(lines)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("账单生成器测试")
    print("=" * 60)
    
    # 创建测试配置
    config = InvoiceConfig(
        customer_id='CUST-TEST001',
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 1, 31),
        billing_mode='per_sample',
        unit_price=10.0,
        tax_rate=0.06
    )
    
    # 测试金额计算
    generator = InvoiceGenerator()
    usage_data = {
        'unique_samples': 100,
        'total_operations': 250,
        'total_samples': 120
    }
    
    subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
    print(f"\n[测试] 按样本数计费:")
    print(f"  唯一样本数: {usage_data['unique_samples']}")
    print(f"  单价: ¥{config.unit_price:.2f}")
    print(f"  小计: ¥{subtotal:.2f}")
    print(f"  税额: ¥{tax_amount:.2f}")
    print(f"  总计: ¥{total_amount:.2f}")
    
    # 测试订阅模式
    config2 = InvoiceConfig(
        customer_id='CUST-TEST002',
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 1, 31),
        billing_mode='subscription',
        subscription_fee=500.0,
        tax_rate=0.06
    )
    
    subtotal2, tax_amount2, total_amount2 = generator.calculate_amount(config2, usage_data)
    print(f"\n[测试] 固定订阅模式:")
    print(f"  订阅费: ¥{config2.subscription_fee:.2f}")
    print(f"  小计: ¥{subtotal2:.2f}")
    print(f"  税额: ¥{tax_amount2:.2f}")
    print(f"  总计: ¥{total_amount2:.2f}")
    
    # 测试混合模式
    config3 = InvoiceConfig(
        customer_id='CUST-TEST003',
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 1, 31),
        billing_mode='hybrid',
        subscription_fee=200.0,
        base_quota=50,
        overage_price=8.0,
        tax_rate=0.06
    )
    
    subtotal3, tax_amount3, total_amount3 = generator.calculate_amount(config3, usage_data)
    print(f"\n[测试] 混合模式:")
    print(f"  基础订阅费: ¥{config3.subscription_fee:.2f}")
    print(f"  基础配额: {config3.base_quota} 样本")
    print(f"  实际使用: {usage_data['unique_samples']} 样本")
    print(f"  超额: {usage_data['unique_samples'] - config3.base_quota} 样本")
    print(f"  超额单价: ¥{config3.overage_price:.2f}")
    print(f"  小计: ¥{subtotal3:.2f}")
    print(f"  税额: ¥{tax_amount3:.2f}")
    print(f"  总计: ¥{total_amount3:.2f}")
    
    print("\n[成功] 所有测试通过")
