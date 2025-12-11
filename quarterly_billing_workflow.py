#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
季度计费工作流程
按季度样本处理次数收费的完整流程
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from database_manager import DatabaseManager
from data_encryptor import DataEncryptor
from invoice_generator import InvoiceGenerator


class QuarterlyBillingWorkflow:
    """季度计费工作流程管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.encryptor = DataEncryptor()
        self.invoice_gen = InvoiceGenerator(db_manager)
    
    def get_current_quarter(self) -> Tuple[str, str, str]:
        """
        获取当前季度信息
        
        返回:
            (季度名称, 开始日期, 结束日期)
        """
        now = datetime.now()
        year = now.year
        month = now.month
        
        # 确定季度
        if month <= 3:
            quarter = "Q1"
            start = f"{year}-01-01"
            end = f"{year}-03-31"
        elif month <= 6:
            quarter = "Q2"
            start = f"{year}-04-01"
            end = f"{year}-06-30"
        elif month <= 9:
            quarter = "Q3"
            start = f"{year}-07-01"
            end = f"{year}-09-30"
        else:
            quarter = "Q4"
            start = f"{year}-10-01"
            end = f"{year}-12-31"
        
        return (f"{year}-{quarter}", start, end)
    
    def get_quarter_info(self, quarter_str: str) -> Tuple[str, str]:
        """
        解析季度字符串
        
        参数:
            quarter_str: 格式 "2025-Q1"
        
        返回:
            (开始日期, 结束日期)
        """
        year, quarter = quarter_str.split('-')
        year = int(year)
        
        if quarter == "Q1":
            return (f"{year}-01-01", f"{year}-03-31")
        elif quarter == "Q2":
            return (f"{year}-04-01", f"{year}-06-30")
        elif quarter == "Q3":
            return (f"{year}-07-01", f"{year}-09-30")
        else:  # Q4
            return (f"{year}-10-01", f"{year}-12-31")
    
    # ==================== 客户端操作 ====================
    
    def export_quarterly_report(self, customer_id: str, 
                                quarter: str = None,
                                output_file: str = None) -> Dict:
        """
        导出季度使用报告（客户端操作）
        
        参数:
            customer_id: 客户ID
            quarter: 季度（如"2025-Q1"），None表示当前季度
            output_file: 输出文件路径
        
        返回:
            报告数据
        """
        # 确定季度
        if quarter is None:
            quarter, start_date, end_date = self.get_current_quarter()
        else:
            start_date, end_date = self.get_quarter_info(quarter)
        
        # 查询该季度的使用记录
        usage_records = self.db.fetchall('''
            SELECT * FROM usage_records
            WHERE customer_id = ?
            AND report_date >= ? AND report_date <= ?
            ORDER BY report_date
        ''', (customer_id, start_date, end_date))
        
        # 统计数据
        total_samples = sum(r['total_samples_loaded'] for r in usage_records)
        total_exports = sum(r['total_exports'] for r in usage_records)
        total_splits = sum(r['total_splits'] for r in usage_records)
        unique_samples = sum(r['unique_samples'] for r in usage_records)
        
        # 获取客户信息
        customer = self.db.get_customer(customer_id)
        
        # 生成报告
        report = {
            'report_type': 'quarterly_usage',
            'report_version': '1.0',
            'generated_at': datetime.now().isoformat(),
            
            # 客户信息
            'customer_id': customer_id,
            'customer_name': customer.get('name', ''),
            'company': customer.get('company', ''),
            'license_key': customer.get('license_key', ''),
            
            # 季度信息
            'quarter': quarter,
            'period_start': start_date,
            'period_end': end_date,
            
            # 使用统计
            'usage_summary': {
                'total_samples_loaded': total_samples,
                'total_exports': total_exports,
                'total_splits': total_splits,
                'unique_samples': unique_samples,
                'total_operations': total_samples + total_exports + total_splits,
                'report_count': len(usage_records)
            },
            
            # 详细记录
            'usage_details': [
                {
                    'date': r['report_date'],
                    'samples_loaded': r['total_samples_loaded'],
                    'exports': r['total_exports'],
                    'splits': r['total_splits'],
                    'unique_samples': r['unique_samples']
                }
                for r in usage_records
            ],
            
            # 完整性验证
            'integrity': {
                'record_count': len(usage_records),
                'checksum': self._calculate_report_checksum(usage_records)
            }
        }
        
        # 保存到文件（加密）
        if output_file:
            self._save_encrypted_report(report, output_file)
        
        return report
    
    def _calculate_report_checksum(self, records: List) -> str:
        """计算报告校验和"""
        import hashlib
        
        data_str = json.dumps([dict(r) for r in records], sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _save_encrypted_report(self, report: Dict, output_file: str):
        """保存加密报告"""
        report_json = json.dumps(report, indent=2, ensure_ascii=False)
        
        # 加密
        encrypted = self.encryptor.encrypt_with_license(
            report_json,
            report['license_key']
        )
        
        # 保存
        Path(output_file).write_text(encrypted)
        print(f"[成功] 季度报告已导出: {output_file}")
    
    # ==================== 管理员操作 ====================
    
    def import_quarterly_report(self, report_file: str) -> Tuple[bool, str, Dict]:
        """
        导入季度使用报告（管理员操作）
        
        参数:
            report_file: 报告文件路径
        
        返回:
            (是否成功, 消息, 报告数据)
        """
        try:
            # 读取加密报告
            encrypted_content = Path(report_file).read_text()
            
            # 尝试解密
            decrypted = self.encryptor.decrypt_with_multiple_keys(encrypted_content)
            
            if not decrypted:
                return (False, "无法解密报告文件", None)
            
            # 解析JSON
            report = json.loads(decrypted)
            
            # 验证报告格式
            if report.get('report_type') != 'quarterly_usage':
                return (False, "报告格式不正确", None)
            
            # 验证完整性
            if not self._verify_report_integrity(report):
                return (False, "报告完整性验证失败", None)
            
            # 检查是否已导入
            customer_id = report['customer_id']
            quarter = report['quarter']
            
            existing = self.db.fetchone('''
                SELECT id FROM usage_records
                WHERE customer_id = ? AND report_date LIKE ?
                LIMIT 1
            ''', (customer_id, f"{quarter.split('-')[0]}%"))
            
            if existing:
                return (False, f"该季度报告已导入: {quarter}", report)
            
            return (True, "报告验证成功", report)
        
        except Exception as e:
            return (False, f"导入失败: {str(e)}", None)
    
    def _verify_report_integrity(self, report: Dict) -> bool:
        """验证报告完整性"""
        # 这里可以添加更多验证逻辑
        required_fields = [
            'customer_id', 'quarter', 'period_start', 'period_end',
            'usage_summary', 'integrity'
        ]
        
        for field in required_fields:
            if field not in report:
                return False
        
        return True
    
    def generate_quarterly_invoice(self, customer_id: str, 
                                   quarter: str,
                                   unit_price: float = None) -> Dict:
        """
        生成季度账单（管理员操作）
        
        参数:
            customer_id: 客户ID
            quarter: 季度（如"2025-Q1"）
            unit_price: 单价（元/样本），None则使用客户默认单价
        
        返回:
            账单数据
        """
        # 获取客户信息
        customer = self.db.get_customer(customer_id)
        if not customer:
            raise ValueError(f"客户不存在: {customer_id}")
        
        # 获取单价
        if unit_price is None:
            unit_price = customer.get('unit_price', 10.0)
        
        # 获取季度使用数据
        start_date, end_date = self.get_quarter_info(quarter)
        
        usage_records = self.db.fetchall('''
            SELECT * FROM usage_records
            WHERE customer_id = ?
            AND report_date >= ? AND report_date <= ?
        ''', (customer_id, start_date, end_date))
        
        # 计算总样本数
        total_samples = sum(r['total_samples_loaded'] for r in usage_records)
        
        # 计算金额
        subtotal = total_samples * unit_price
        tax_rate = 0.06  # 6%税率
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        # 生成账单ID
        invoice_id = f"INV-{quarter}-{customer_id}"
        
        # 创建账单
        invoice_data = {
            'invoice_id': invoice_id,
            'customer_id': customer_id,
            'period_start': start_date,
            'period_end': end_date,
            'billing_mode': 'per_sample',
            'total_samples': total_samples,
            'total_operations': 0,
            'unit_price': unit_price,
            'subscription_fee': 0.0,
            'subtotal': subtotal,
            'tax_rate': tax_rate,
            'tax_amount': tax_amount,
            'total_amount': total_amount,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'notes': f'{quarter}季度账单'
        }
        
        # 保存到数据库
        self.db.create_invoice(invoice_data)
        
        return invoice_data
    
    def mark_invoice_paid(self, invoice_id: str, 
                         payment_date: str = None) -> bool:
        """
        标记账单已付款
        
        参数:
            invoice_id: 账单ID
            payment_date: 付款日期
        
        返回:
            是否成功
        """
        if payment_date is None:
            payment_date = datetime.now().isoformat()
        
        count = self.db.update(
            'invoices',
            {
                'status': 'paid',
                'paid_at': payment_date
            },
            'invoice_id = ?',
            (invoice_id,)
        )
        
        return count > 0
    
    def extend_license_after_payment(self, customer_id: str, 
                                    months: int = 3) -> Tuple[bool, str]:
        """
        付款后延长License（管理员操作）
        
        参数:
            customer_id: 客户ID
            months: 延长月数（默认3个月，即一个季度）
        
        返回:
            (是否成功, 新到期时间)
        """
        customer = self.db.get_customer(customer_id)
        if not customer:
            return (False, "客户不存在")
        
        # 计算新到期时间
        current_expires = datetime.fromisoformat(customer['expires_at'])
        
        # 如果已过期，从当前时间开始计算
        if current_expires < datetime.now():
            new_expires = datetime.now() + timedelta(days=months * 30)
        else:
            # 否则在原到期时间基础上延长
            new_expires = current_expires + timedelta(days=months * 30)
        
        new_expires_str = new_expires.strftime('%Y-%m-%d')
        
        # 更新数据库
        self.db.update_customer(customer_id, {
            'expires_at': new_expires_str,
            'status': 'active'
        })
        
        return (True, new_expires_str)
    
    def generate_license_config(self, customer_id: str, 
                               output_file: str = None) -> str:
        """
        生成License配置文件（管理员操作）
        
        参数:
            customer_id: 客户ID
            output_file: 输出文件路径
        
        返回:
            配置文件内容
        """
        customer = self.db.get_customer(customer_id)
        if not customer:
            raise ValueError(f"客户不存在: {customer_id}")
        
        config_content = f"""license_key={customer['license_key']}
expires_at={customer['expires_at']}T23:59:59
customer_id={customer['customer_id']}
status={customer['status']}
billing_mode={customer['billing_mode']}
updated_at={datetime.now().isoformat()}
"""
        
        if output_file:
            Path(output_file).write_text(config_content)
            print(f"[成功] 配置文件已生成: {output_file}")
        
        return config_content
    
    # ==================== 工作流程 ====================
    
    def complete_quarterly_billing_cycle(self, customer_id: str, 
                                        quarter: str,
                                        report_file: str,
                                        unit_price: float = None) -> Dict:
        """
        完成一个完整的季度计费周期
        
        参数:
            customer_id: 客户ID
            quarter: 季度
            report_file: 报告文件
            unit_price: 单价
        
        返回:
            处理结果
        """
        result = {
            'success': False,
            'steps': [],
            'invoice': None,
            'new_expires': None,
            'config_file': None
        }
        
        # 步骤1: 导入报告
        success, message, report = self.import_quarterly_report(report_file)
        result['steps'].append({
            'step': '导入报告',
            'success': success,
            'message': message
        })
        
        if not success:
            return result
        
        # 步骤2: 生成账单
        try:
            invoice = self.generate_quarterly_invoice(
                customer_id, quarter, unit_price
            )
            result['invoice'] = invoice
            result['steps'].append({
                'step': '生成账单',
                'success': True,
                'message': f"账单金额: ¥{invoice['total_amount']:.2f}"
            })
        except Exception as e:
            result['steps'].append({
                'step': '生成账单',
                'success': False,
                'message': str(e)
            })
            return result
        
        # 步骤3: 标记已付款（实际应该等待付款）
        # 这里假设已付款
        paid = self.mark_invoice_paid(invoice['invoice_id'])
        result['steps'].append({
            'step': '标记付款',
            'success': paid,
            'message': '已付款' if paid else '付款失败'
        })
        
        if not paid:
            return result
        
        # 步骤4: 延长License
        success, new_expires = self.extend_license_after_payment(customer_id)
        result['new_expires'] = new_expires
        result['steps'].append({
            'step': '延长License',
            'success': success,
            'message': f'新到期时间: {new_expires}'
        })
        
        if not success:
            return result
        
        # 步骤5: 生成配置文件
        config_file = f"{customer_id}_license_config.txt"
        self.generate_license_config(customer_id, config_file)
        result['config_file'] = config_file
        result['steps'].append({
            'step': '生成配置文件',
            'success': True,
            'message': f'配置文件: {config_file}'
        })
        
        result['success'] = True
        return result


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("季度计费工作流程测试")
    print("=" * 60)
    
    # 初始化
    db = DatabaseManager('license_manager.db', mode='admin')
    workflow = QuarterlyBillingWorkflow(db)
    
    # 测试1: 获取当前季度
    print("\n[TEST 1] 获取当前季度...")
    quarter, start, end = workflow.get_current_quarter()
    print(f"当前季度: {quarter}")
    print(f"开始日期: {start}")
    print(f"结束日期: {end}")
    
    # 测试2: 导出季度报告（模拟）
    print("\n[TEST 2] 导出季度报告...")
    customer_id = 'CUST-6FA90D6C'
    
    try:
        report = workflow.export_quarterly_report(
            customer_id=customer_id,
            quarter=quarter,
            output_file=f'{customer_id}_{quarter}_report.enc'
        )
        print(f"报告已生成:")
        print(f"  样本数: {report['usage_summary']['total_samples_loaded']}")
        print(f"  导出次数: {report['usage_summary']['total_exports']}")
        print(f"  拆分次数: {report['usage_summary']['total_splits']}")
    except Exception as e:
        print(f"导出失败: {e}")
    
    print("\n[成功] 测试完成")
