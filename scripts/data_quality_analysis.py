"""
数据质量分析脚本
分析Neo4j中车型数据的质量问题：缺失值、异常值、数据分布
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.neo4j_conn import Neo4jConnection
import pandas as pd
from collections import Counter


class DataQualityAnalyzer:
    def __init__(self):
        self.conn = Neo4jConnection()

    def analyze_all(self):
        """执行完整的数据质量分析"""
        print("\n" + "="*60)
        print("Car Helper 数据质量分析报告")
        print("="*60)

        # 1. 基础统计
        print("\n【1. 数据规模统计】")
        self.analyze_scale()

        # 2. 缺失值分析
        print("\n【2. 缺失值分析】")
        self.analyze_missing_values()

        # 3. 数据分布
        print("\n【3. 数据分布分析】")
        self.analyze_distribution()

        # 4. 异常值检测
        print("\n【4. 异常值检测】")
        self.analyze_anomalies()

        # 5. 数据新鲜度
        print("\n【5. 数据新鲜度分析】")
        self.analyze_freshness()

        print("\n" + "="*60)
        print("分析完成")
        print("="*60)

    def analyze_scale(self):
        """数据规模统计"""
        with self.conn.get_session() as session:
            # 车型总数
            result = session.run("MATCH (m:车型) RETURN count(m) as count")
            model_count = result.single()['count']

            # 品牌总数
            result = session.run("MATCH (b:品牌) RETURN count(b) as count")
            brand_count = result.single()['count']

            # 车系总数
            result = session.run("MATCH (s:车系) RETURN count(s) as count")
            series_count = result.single()['count']

            # 能源类型
            result = session.run("MATCH (e:能源类型) RETURN count(e) as count")
            energy_count = result.single()['count']

            # 价格区间
            result = session.run("MATCH (p:价格区间) RETURN count(p) as count")
            price_count = result.single()['count']

            print(f"  车型总数: {model_count:,}")
            print(f"  品牌总数: {brand_count:,}")
            print(f"  车系总数: {series_count:,}")
            print(f"  能源类型: {energy_count}")
            print(f"  价格区间: {price_count}")

    def analyze_missing_values(self):
        """缺失值分析"""
        with self.conn.get_session() as session:
            # 获取所有车型数据
            query = """
            MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
            OPTIONAL MATCH (m)-[:IN_PRICE_RANGE]->(p:价格区间)
            RETURN
                m.车名 as 车名,
                m.官方指导价 as 指导价,
                m.能源类型 as 能源类型,
                m.级别 as 级别,
                m.上市时间 as 上市时间,
                b.name as 品牌,
                s.name as 车系,
                p.name as 价格区间
            LIMIT 10000
            """
            result = session.run(query)
            data = result.data()

        df = pd.DataFrame(data)
        total = len(df)

        print(f"  样本数量: {total:,}")
        print(f"\n  字段缺失率:")

        fields = ['车名', '指导价', '能源类型', '级别', '上市时间', '品牌', '车系', '价格区间']
        missing_stats = []

        for field in fields:
            # 统计None、空字符串、"暂无"、"NONE"等
            missing_count = df[field].isna().sum()
            missing_count += (df[field] == '').sum()
            missing_count += (df[field] == '暂无').sum()
            missing_count += (df[field] == 'NONE').sum()
            missing_count += (df[field] == '暂无报价').sum()

            missing_rate = (missing_count / total) * 100
            missing_stats.append({
                'field': field,
                'missing_count': missing_count,
                'missing_rate': missing_rate
            })

            status = "OK" if missing_rate < 5 else "WARNING" if missing_rate < 20 else "ERROR"
            print(f"    [{status:<7}] {field:<10}: {missing_rate:>6.2f}% ({missing_count}/{total})")

        # 总体质量评分
        avg_missing_rate = sum(s['missing_rate'] for s in missing_stats) / len(missing_stats)
        print(f"\n  平均缺失率: {avg_missing_rate:.2f}%")

        if avg_missing_rate < 10:
            print("  数据质量评级: [5/5] 优秀")
        elif avg_missing_rate < 20:
            print("  数据质量评级: [4/5] 良好")
        elif avg_missing_rate < 30:
            print("  数据质量评级: [3/5] 一般")
        else:
            print("  数据质量评级: [2/5] 较差")

    def analyze_distribution(self):
        """数据分布分析"""
        with self.conn.get_session() as session:
            # 品牌分布（Top 10）
            query = """
            MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
            RETURN b.name as brand, count(m) as count
            ORDER BY count DESC
            LIMIT 10
            """
            result = session.run(query)
            brands = result.data()

            print(f"  品牌分布 (Top 10):")
            for i, brand in enumerate(brands, 1):
                print(f"    {i}. {brand['brand']:<15}: {brand['count']:>5} 款")

            # 能源类型分布
            query = """
            MATCH (m:车型)
            RETURN m.能源类型 as energy, count(m) as count
            ORDER BY count DESC
            """
            result = session.run(query)
            energies = result.data()

            print(f"\n  能源类型分布:")
            total_energy = sum(e['count'] for e in energies)
            for energy in energies:
                rate = (energy['count'] / total_energy) * 100
                print(f"    {energy['energy']:<15}: {energy['count']:>6} 款 ({rate:.1f}%)")

            # 价格区间分布
            query = """
            MATCH (m:车型)-[:IN_PRICE_RANGE]->(p:价格区间)
            RETURN p.name as range, count(m) as count
            ORDER BY
                CASE p.name
                    WHEN '0-10万' THEN 1
                    WHEN '10-20万' THEN 2
                    WHEN '20-30万' THEN 3
                    WHEN '30-40万' THEN 4
                    WHEN '40-50万' THEN 5
                    WHEN '50万以上' THEN 6
                END
            """
            result = session.run(query)
            prices = result.data()

            print(f"\n  价格区间分布:")
            for price in prices:
                print(f"    {price['range']:<15}: {price['count']:>6} 款")

    def analyze_anomalies(self):
        """异常值检测"""
        with self.conn.get_session() as session:
            # 检测指导价异常（如"暂无报价"占比）
            query = """
            MATCH (m:车型)
            WHERE m.官方指导价 = '暂无报价' OR m.官方指导价 IS NULL OR m.官方指导价 = ''
            RETURN count(m) as count
            """
            result = session.run(query)
            no_price_count = result.single()['count']

            query = "MATCH (m:车型) RETURN count(m) as total"
            result = session.run(query)
            total = result.single()['total']

            no_price_rate = (no_price_count / total) * 100
            print(f"  无价格信息车型: {no_price_count}/{total} ({no_price_rate:.2f}%)")

            # 检测上市时间异常
            query = """
            MATCH (m:车型)
            WHERE m.上市时间 IS NULL OR m.上市时间 = '' OR m.上市时间 = '暂无'
            RETURN count(m) as count
            """
            result = session.run(query)
            no_date_count = result.single()['count']
            no_date_rate = (no_date_count / total) * 100
            print(f"  无上市时间车型: {no_date_count}/{total} ({no_date_rate:.2f}%)")

            # 检测能源类型异常
            query = """
            MATCH (m:车型)
            WHERE m.能源类型 IS NULL OR m.能源类型 = '' OR m.能源类型 = '暂无'
            RETURN count(m) as count
            """
            result = session.run(query)
            no_energy_count = result.single()['count']
            no_energy_rate = (no_energy_count / total) * 100
            print(f"  无能源类型车型: {no_energy_count}/{total} ({no_energy_rate:.2f}%)")

    def analyze_freshness(self):
        """数据新鲜度分析"""
        with self.conn.get_session() as session:
            # 统计各年份上市车型数量
            query = """
            MATCH (m:车型)
            WHERE m.上市时间 IS NOT NULL AND m.上市时间 <> '' AND m.上市时间 <> '暂无'
            RETURN m.上市时间 as date
            """
            result = session.run(query)
            dates = [r['date'] for r in result]

            # 提取年份（假设格式为 "2024.01" 或 "2024-01"）
            years = []
            for date in dates:
                if date and len(date) >= 4:
                    try:
                        year = date[:4]
                        if year.isdigit():
                            years.append(int(year))
                    except:
                        pass

            if years:
                year_counter = Counter(years)
                sorted_years = sorted(year_counter.items(), reverse=True)

                print(f"  近年上市车型统计:")
                for year, count in sorted_years[:5]:
                    print(f"    {year}年: {count:>5} 款")

                # 数据新鲜度评估
                recent_count = sum(count for year, count in sorted_years if year >= 2024)
                total_with_date = len(years)
                recent_rate = (recent_count / total_with_date) * 100 if total_with_date > 0 else 0

                print(f"\n  2024年及以后车型占比: {recent_rate:.2f}%")

                if recent_rate > 30:
                    print("  数据新鲜度: [5/5] 优秀")
                elif recent_rate > 20:
                    print("  数据新鲜度: [4/5] 良好")
                elif recent_rate > 10:
                    print("  数据新鲜度: [3/5] 一般")
                else:
                    print("  数据新鲜度: [2/5] 较旧")
            else:
                print("  无法分析数据新鲜度（日期格式异常）")


def main():
    analyzer = DataQualityAnalyzer()
    analyzer.analyze_all()


if __name__ == '__main__':
    main()
