import os
import sys
import json
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from src.db.neo4j_conn import Neo4jConnection

conn = Neo4jConnection()

ENTITIES_ROOT = os.path.join(os.path.dirname(__file__), "..", "entities")
RELATIONS_ROOT = os.path.join(os.path.dirname(__file__), "..", "relationships")

with conn.get_session() as session:
    session.run("MATCH (n) DETACH DELETE n")

for root_dir in [ENTITIES_ROOT, RELATIONS_ROOT]:
    file_list = os.listdir(root_dir)

    for file in file_list:
        file_path = os.path.join(root_dir, file)
        print(file_path)

        if file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                datas = json.load(f)

            with conn.get_session() as session:
                for model_info in tqdm(datas, desc="model.json", colour="green"):
                    insert_language = "CREATE (a:车型 {"
                    for label, value in model_info.items():
                        key = f"`{label}`" if "(" in label or label[0].isdigit() else label
                        val = value.replace("'", r"\'") if "'" in value else value
                        insert_language += f"{key}: '{val}', "
                    insert_language = insert_language[:-2] + "})"
                    session.run(insert_language)

        else:
            with open(file_path, "r", encoding="utf-8") as f:
                datas = [i.strip() for i in f.readlines()]

            if root_dir == ENTITIES_ROOT:
                with conn.get_session() as session:
                    for data in tqdm(datas[1:], desc="实体:", colour="green"):
                        insert_language = "CREATE (a:" + datas[0] + " {name: '" + data + "'})"
                        session.run(insert_language)

            elif file == "brand_and_model_series_relationships.txt":
                with conn.get_session() as session:
                    for data in tqdm(datas[1:], desc="品牌", colour="green"):
                        series_index = data.find("车系")
                        relationships = data.find("HAS_SERIES")
                        a = data[:2]
                        b = data[3: series_index - 1]
                        c = data[series_index: series_index + 2]
                        d = data[series_index + 3: relationships - 1]
                        e = data[relationships:]
                        insert_language = (
                            "MATCH (a:" + a + " {name: '" + b + "'})\n"
                            + "MATCH (b:" + c + " {name: '" + d + "'})\n"
                            + "CREATE (a)-[:" + e + "]->(b)"
                        )
                        session.run(insert_language)

            else:
                with conn.get_session() as session:
                    for data in tqdm(datas[1:], desc="车系", colour="green"):
                        if "'" in data:
                            data = data.replace("'", r"\'")
                        series_index = data.find("车型")
                        relationships = data.find("HAS_MODEL")
                        a = data[:2]
                        b = data[3: series_index - 1]
                        c = data[series_index: series_index + 2]
                        d = data[series_index + 3: relationships - 1]
                        e = data[relationships:]
                        insert_language = (
                            "MATCH (a:" + a + " {name: '" + b + "'})\n"
                            + "MATCH (b:" + c + " {车名: '" + d + "'})\n"
                            + "CREATE (a)-[:" + e + "]->(b)"
                        )
                        session.run(insert_language)

conn.close()
