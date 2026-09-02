"""
增量数据更新系统
定期检查和更新Neo4j中的车型数据
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.neo4j_conn import Neo4jConnection
import json


class IncrementalDataUpdater:
    """增量数据更新器"""

    def __init__(self):
        self.conn = Neo4jConnection()

    def check_data_freshness(self):
        """检查数据新鲜度"""
        print("\n[数据新鲜度检查]")

        with self.conn.get_session() as session:
            # 检查最新车型的上市时间
            query = """
            MATCH (m:车型)
            WHERE m.上市时间 IS NOT NULL AND m.上市时间 <> '' AND m.上市时间 <> 'None'
            RETURN m.上市时间 as date
            ORDER BY m.上市时间 DESC
            LIMIT 1
            """
            result = session.run(query)
            record = result.single()

            if record:
                latest_date = record['date']
                print(f"  最新车型上市时间: {latest_date}")

                # 计算数据年龄
                try:
                    # 尝试解析日期（假设格式为 "2026.01" 或 "2026-01"）
                    if '.' in latest_date:
                        year_str = latest_date.split('.')[0]
                        month_str = latest_date.split('.')[1] if '.' in latest_date else '01'
                    elif '-' in latest_date:
                        year_str = latest_date.split('-')[0]
                        month_str = latest_date.split('-')[1] if '-' in latest_date else '01'
                    else:
                        year_str = latest_date[:4] if len(latest_date) >= 4 else '2024'
                        month_str = '01'

                    year = int(year_str)
                    month = int(month_str) if month_str.isdigit() else 1

                    latest_dt = datetime(year, month, 1)
                    current_dt = datetime.now()
                    age_days = (current_dt - latest_dt).days

                    print(f"  数据年龄: {age_days} 天")

                    if age_days <= 7:
                        print("  状态: [OK] 数据新鲜")
                        return True
                    elif age_days <= 30:
                        print("  状态: [WARNING] 数据较旧，建议更新")
                        return False
                    else:
                        print("  状态: [ERROR] 数据过期，需要更新")
                        return False
                except Exception as e:
                    print(f"  状态: [WARNING] 无法解析日期 - {e}")
                    return False
            else:
                print("  状态: [ERROR] 无法获取最新日期")
                return False

    def find_missing_price_models(self, limit=100):
        """查找缺失价格信息的车型"""
        print(f"\n[查找缺失价格的车型（Top {limit}）]")

        with self.conn.get_session() as session:
            query = """
            MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
            WHERE m.官方指导价 = '暂无报价' OR m.官方指导价 IS NULL OR m.官方指导价 = ''
            RETURN b.name as brand, s.name as series, m.车名 as model, m.上市时间 as date
            ORDER BY m.上市时间 DESC
            LIMIT $limit
            """
            result = session.run(query, limit=limit)
            models = result.data()

            print(f"  找到 {len(models)} 款缺失价格的车型")

            if models:
                print("\n  最新的10款:")
                for i, model in enumerate(models[:10], 1):
                    print(f"    {i}. {model['brand']} {model['series']} - {model['model']}")

            return models

    def identify_new_models_needed(self):
        """识别需要添加的新车型（基于时间判断）"""
        print("\n[识别需要更新的车型]")

        with self.conn.get_session() as session:
            # 统计各年份车型数量
            query = """
            MATCH (m:车型)
            WHERE m.上市时间 IS NOT NULL AND m.上市时间 <> ''
            WITH substring(m.上市时间, 0, 4) as year, count(m) as count
            RETURN year, count
            ORDER BY year DESC
            LIMIT 5
            """
            result = session.run(query)
            years = result.data()

            print("\n  近年车型统计:")
            for year_data in years:
                print(f"    {year_data['year']}年: {year_data['count']} 款")

            # 建议
            current_year = datetime.now().year
            current_year_count = next((y['count'] for y in years if y['year'] == str(current_year)), 0)

            print(f"\n  {current_year}年车型数量: {current_year_count}")

            if current_year_count < 1000:
                print(f"  建议: 需要补充更多{current_year}年车型")
                return True
            else:
                print(f"  建议: {current_year}年车型数据充足")
                return False

    def generate_update_plan(self):
        """生成更新计划"""
        print("\n" + "="*60)
        print("增量数据更新计划")
        print("="*60)

        # 1. 检查数据新鲜度
        is_fresh = self.check_data_freshness()

        # 2. 查找缺失价格的车型
        missing_price_models = self.find_missing_price_models()

        # 3. 识别需要的新车型
        need_new_models = self.identify_new_models_needed()

        # 生成计划
        print("\n" + "="*60)
        print("更新建议")
        print("="*60)

        tasks = []

        if not is_fresh:
            tasks.append({
                'priority': 'HIGH',
                'task': '爬取最新车型数据',
                'description': '数据不够新鲜，需要获取最新上市车型'
            })

        if len(missing_price_models) > 0:
            tasks.append({
                'priority': 'MEDIUM',
                'task': f'补充 {len(missing_price_models)} 款车型的价格信息',
                'description': '部分车型缺失价格，影响查询效果'
            })

        if need_new_models:
            tasks.append({
                'priority': 'HIGH',
                'task': '补充当前年份车型',
                'description': f'{datetime.now().year}年车型数据不足'
            })

        if not tasks:
            print("  [OK] 数据质量良好，暂无紧急更新任务")
        else:
            print("\n  待执行任务:")
            for i, task in enumerate(tasks, 1):
                print(f"\n  {i}. [{task['priority']}] {task['task']}")
                print(f"     {task['description']}")

        # 保存计划
        plan = {
            'generated_at': datetime.now().isoformat(),
            'data_fresh': is_fresh,
            'missing_price_count': len(missing_price_models),
            'need_new_models': need_new_models,
            'tasks': tasks
        }

        with open('data_update_plan.json', 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

        print("\n更新计划已保存到 data_update_plan.json")

        return plan


def main():
    print("\n" + "="*60)
    print("增量数据更新系统")
    print("="*60)

    updater = IncrementalDataUpdater()
    updater.generate_update_plan()


if __name__ == '__main__':
    main()
