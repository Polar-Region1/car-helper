import os
import sys
from tqdm import tqdm
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from src.db.neo4j_conn import Neo4jConnection

conn = Neo4jConnection()

SRC_ROOT = os.path.join(os.path.dirname(__file__), "..")

energy_type = pd.read_csv(os.path.join(SRC_ROOT, "energy_type.csv"))
price_range = pd.read_csv(os.path.join(SRC_ROOT, "price_range.csv"))
energy_type_relationships = pd.read_csv(os.path.join(SRC_ROOT, "relationships.csv"))
price_range_relationships = pd.read_csv(os.path.join(SRC_ROOT, "price_range_relationships.csv"))

energy_type_columns = energy_type.columns.tolist()
price_range_columns = price_range.columns.tolist()

with conn.get_session() as session:
    for energy in tqdm(energy_type.values, desc="能源类型实体"):
        insert_language = "CREATE (e:" + energy_type_columns[0] + " {name: '" + energy[0] + "'})"
        session.run(insert_language)

with conn.get_session() as session:
    for price in tqdm(price_range.values, desc="价格区间实体"):
        insert_language = "CREATE (e:" + price_range_columns[0] + " {name: '" + price[0] + "'})"
        session.run(insert_language)

with conn.get_session() as session:
    for i in tqdm(range(32180, len(energy_type_relationships)), desc="能源类型关系"):
        model_name = energy_type_relationships.iloc[i, 1]
        if "'" in model_name:
            model_name = model_name.replace("'", r"\'")
        insert_language = (
            "MATCH (a:" + energy_type_relationships.iloc[i, 3] + " {车名: '" + model_name + "'})\n"
            + "MATCH (b:" + energy_type_relationships.iloc[i, 4] + " {name: '" + energy_type_relationships.iloc[i, 2] + "'})\n"
            + "CREATE (a)-[:" + energy_type_relationships.iloc[i, 0] + "]->(b)"
        )
        session.run(insert_language)

with conn.get_session() as session:
    for i in tqdm(range(len(price_range_relationships)), desc="价格区间关系"):
        insert_language = (
            "MATCH (a:" + price_range_relationships.iloc[i, 0] + " {车名: '" + price_range_relationships.iloc[i, 1] + "'})\n"
            + "MATCH (b:" + price_range_relationships.iloc[i, 2] + " {name: '" + price_range_relationships.iloc[i, 3] + "'})\n"
            + "CREATE (a)-[:" + price_range_relationships.iloc[i, 4] + "]->(b)"
        )
        session.run(insert_language)

conn.close()
