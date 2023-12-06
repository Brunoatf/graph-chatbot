from neo4j import GraphDatabase
import pandas as pd

class CompanyGraph():

    def __init__(self):

        # Configuração de conexão com o banco de dados Neo4j
        self.uri = "neo4j+s://82046d1f.databases.neo4j.io" 
        self.user = "neo4j"
        self.password = "LyvEFa1Eyf0VtMaELDfjqW6uyaF3pckSRDLY0z_koQU"

    # Função para importar dados de um DataFrame para o Neo4j
    def import_employee_dataframe_to_neo4j(self, tx, df):
        query = """
        UNWIND $data AS row
        CREATE (p:Colaborador)
        SET p = row
        """
        data = df.to_dict(orient="records")
        tx.run(query, data=data)

    def import_receipts_dataframe_to_neo4j(self, tx, df):
        query = """
        UNWIND $data AS row
        CREATE (p:RecibosMensais)
        SET p = row
        """
        data = df.to_dict(orient="records")
        tx.run(query, data=data)

    def set_receipts_relationships(self, tx):
        query = """
        MATCH (p1:Colaborador), (p2:RecibosMensais)
        WHERE p1.`NOME` = p2.`NOME`
        CREATE (p1)-[:Recebeu]->(p2)"""
        tx.run(query)
    
    #Função para incluir as relações de gestor: 
    def set_employer_relationships(self, tx):
        query = """
        MATCH (p1:Colaborador), (p2:Colaborador)
        WHERE p1.`NOME` = p2.GESTOR   
        CREATE (p1)-[:Gere]->(p2)
        """
        tx.run(query)

    def create_graph(self):

        """Creates the graph in the Neo4J database using the provided URI and auth"""

        #Path for excel files:
        employees = "chatbot/chatbot_data/colaboradores.xlsx"
        receipts = "chatbot/chatbot_data/recibos_estruturado.xlsx"

        df_employees = pd.read_excel(employees)
        df_receipts = pd.read_excel(receipts)

        for column in df_employees.columns:
            if " " in column:
                new_name = column.replace(" ", "_")
                df_employees.rename(columns={column: new_name}, inplace=True)

        for column in df_receipts.columns:
            if " " in column:
                new_name = (column.replace(" ", "_")).replace("-", "_")
                df_receipts.rename(columns={column: new_name}, inplace=True)

        for employee_name in df_employees["NOME"].unique():
            for year in df_receipts["ANO"].unique():
                for month in df_receipts["MÊS"].unique():
                    if not ((df_receipts["NOME"] == employee_name) & (df_receipts["ANO"] == year) & (df_receipts["MÊS"] == month)).any():
                        new_line = {coluna: [0] for coluna in df_receipts.columns}
                        new_line["NOME"] = employee_name
                        new_line["ANO"] = year
                        new_line["MÊS"] = month
                        df_receipts = pd.concat([df_receipts, pd.DataFrame(new_line)], ignore_index=True)
            
        # Crie uma instância do driver
        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        # Execute a importação para o Neo4j
        with driver.session() as session:
            session.execute_write(self.import_employee_dataframe_to_neo4j, df_employees)
            session.execute_write(self.import_receipts_dataframe_to_neo4j, df_receipts)
            session.execute_write(self.set_employer_relationships)
            session.execute_write(self.set_receipts_relationships)

        # Feche a conexão com o driver
        driver.close()

    def check_if_is_manager(self, name: str):

        """Checks if the provided name is a manager to someone in the graph"""

        # Crie uma instância do driver
        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        # Execute a importação para o Neo4j
        with driver.session() as session:
            result = session.run("""MATCH (c:Colaborador {NOME: $name})-[:Gere*]->(subordinado)
                                    RETURN COUNT(DISTINCT subordinado) AS NumeroDeSubordinados""", name=name)
            subordinates = result.single()

            if subordinates is not None:
                subordinates = subordinates[0]
            else: 
                subordinates = 0
        
        # Feche a conexão com o driver
        driver.close()

        if subordinates > 0:
            return True
        else:
            return False
        
    def user_exists(self, name:str):

        """Checks if user exists in the graph"""

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        name = name.upper()

        with driver.session() as session:
            result = session.run("""MATCH (c:Colaborador {NOME: $name})
                                    RETURN COUNT(c) AS NumeroDeColaboradores""", name=name)
            user = result.single()

            if user is not None:
                user = user[0]
            else: 
                user = 0
        
        driver.close()

        if user > 0:
            return True
        else:
            return False
        
    def get_personal_data(self, name: str):

        """Gets the personal data of the provided name"""

        # Crie uma instância do driver
        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        # Execute a importação para o Neo4j
        with driver.session() as session:
            result = session.run("""MATCH (c:Colaborador {NOME: $name})
                                    RETURN properties(c) as properties""", name=name)
            personal_data = result.single()
            print("Personal data", result)
            if personal_data is not None:
                personal_data = personal_data[0]
            else: 
                personal_data = None
        
        # Feche a conexão com o driver
        driver.close()

        return personal_data


employees_graph = CompanyGraph()

if __name__ == "__main__":
    employees_graph.create_graph()