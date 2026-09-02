

import logging
import threading
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jConnectionError(Exception):
    pass


class Neo4jConnection:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, url="bolt://localhost", username="neo4j", password="12345678"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    try:
                        instance.driver = GraphDatabase.driver(url, auth=(username, password))
                        instance.driver.verify_connectivity()
                    except Exception as e:
                        logger.error("Neo4j 连接失败: %s", e)
                        raise Neo4jConnectionError(
                            f"无法连接 Neo4j ({url})，请检查数据库是否启动。详情: {e}"
                        )
                    cls._instance = instance
        return cls._instance

    def ensure_indexes(self):
        indexes = [
            "CREATE INDEX index_brand_name IF NOT EXISTS FOR (b:品牌) ON (b.name)",
            "CREATE INDEX index_price_name IF NOT EXISTS FOR (p:价格区间) ON (p.name)",
            "CREATE INDEX index_energy_name IF NOT EXISTS FOR (e:能源类型) ON (e.name)",
        ]
        try:
            with self.get_session() as session:
                for cypher in indexes:
                    session.run(cypher)
        except Exception as e:
            logger.warning("索引创建失败(非致命): %s", e)

    def get_session(self):
        try:
            return self.driver.session()
        except Exception as e:
            logger.error("获取 Neo4j session 失败: %s", e)
            raise Neo4jConnectionError(f"数据库会话不可用，请稍后重试。详情: {e}")

    def close(self):
        try:
            self.driver.close()
        except Exception:
            pass
        finally:
            Neo4jConnection._instance = None
