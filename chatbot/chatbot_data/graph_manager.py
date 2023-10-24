from neo4j import GraphDatabase
import pandas as pd

class EmployeesGraph():

    def __init__(self):

        # Configuração de conexão com o banco de dados Neo4j
        self.uri = "neo4j+s://82046d1f.databases.neo4j.io" 
        self.user = "neo4j"
        self.password = "LyvEFa1Eyf0VtMaELDfjqW6uyaF3pckSRDLY0z_koQU"

    # Função para importar dados de um DataFrame para o Neo4j
    def import_dataframe_to_neo4j(self, tx, df):
        query = """
        UNWIND $data AS row
        CREATE (p:Colaborador)
        SET p = row
        """
        data = df.to_dict(orient="records")
        tx.run(query, data=data)
    
    #Função para incluir as relações de gestor: 
    def set_relationships(self, tx):
        query = """
        MATCH (p1:Colaborador), (p2:Colaborador)
        WHERE p1.`NOME` = p2.GESTOR   
        CREATE (p1)-[:Gere]->(p2)
        """
        tx.run(query)

    def create_graph(self, excel_file_path):

        """Creates the graph in the Neo4J database using the provided URI and auth"""

        # Caminho para o arquivo Excel
        excel_file_path = "chatbot/chatbot_data/colaboradores.xlsx"

        # Leia o Excel usando Pandas
        df = pd.read_excel(excel_file_path)

        for column in df.columns:
            if " " in column:
                new_name = column.replace(" ", "_")
                df.rename(columns={column: new_name}, inplace=True)

        # Crie uma instância do driver
        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        # Execute a importação para o Neo4j
        with driver.session() as session:
            session.execute_write(self.import_dataframe_to_neo4j, df)
            session.execute_write(self.set_relationships)

        # Feche a conexão com o driver
        driver.close()

employees_graph = EmployeesGraph()

if __name__ == "__main__":
    employees_graph.create_graph("chatbot/chatbot_data/colaboradores.xlsx")