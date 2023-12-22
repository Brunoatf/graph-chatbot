from neo4j import GraphDatabase
import pandas as pd

class CompanyGraph():

    def __init__(self):

        '''Configures the connection to the Neo4j database'''

        self.uri = "neo4j+s://82046d1f.databases.neo4j.io" 
        self.user = "neo4j"
        self.password = "LyvEFa1Eyf0VtMaELDfjqW6uyaF3pckSRDLY0z_koQU"
        self.receipts_path = "chatbot/chatbot_data/data_files/recibos_estruturado.xlsx"
        self.employees_path = "chatbot/chatbot_data/data_files/colaboradores.xlsx"

    def import_employee_dataframe_to_neo4j(self, tx, df: pd.DataFrame) -> None:

        """Imports the employee dataframe to the Neo4J database"""

        query = """
        UNWIND $data AS row
        CREATE (p:Colaborador)
        SET p = row
        """
        data = df.to_dict(orient="records")
        tx.run(query, data=data)

    def import_receipts_dataframe_to_neo4j(self, tx, df: pd.DataFrame) -> None:

        """Imports the receipts dataframe to the Neo4J database"""

        query = """
        UNWIND $data AS row
        CREATE (p:RecibosMensais)
        SET p = row
        """
        data = df.to_dict(orient="records")
        tx.run(query, data=data)

    def set_receipts_relationships(self, tx) -> None:

        """Creates the relationships between the employees and their receipts"""

        query = """
        MATCH (p1:Colaborador), (p2:RecibosMensais)
        WHERE p1.`NOME` = p2.`NOME`
        CREATE (p1)-[:Recebeu]->(p2)"""
        tx.run(query)
    
    def set_employer_relationships(self, tx) -> None:

        """Creates the relationships between the employees and their employers"""

        query = """
        MATCH (p1:Colaborador), (p2:Colaborador)
        WHERE p1.`NOME` = p2.GESTOR   
        CREATE (p1)-[:Gere]->(p2)
        """
        tx.run(query)

    def create_graph(self):

        """Creates the graph in the Neo4J database using the provided URI and auth"""

        df_employees = pd.read_excel(self.employees_path)
        df_receipts = pd.read_excel(self.receipts_path)

        for column in df_employees.columns:
            if " " in column:
                new_name = column.replace(" ", "_")
                df_employees.rename(columns={column: new_name}, inplace=True)

        for column in df_receipts.columns:
            if " " in column:
                new_name = (column.replace(" ", "_")).replace("-", "_")
                df_receipts.rename(columns={column: new_name}, inplace=True)

        #For every employee, year and month, if there is no receipt, create a new receipt with 0s:
        for employee_name in df_employees["NOME"].unique():
            for year in df_receipts["ANO"].unique():
                for month in df_receipts["MÊS"].unique():
                    if not ((df_receipts["NOME"] == employee_name) & (df_receipts["ANO"] == year) & (df_receipts["MÊS"] == month)).any():
                        new_line = {coluna: [0] for coluna in df_receipts.columns}
                        new_line["NOME"] = employee_name
                        new_line["ANO"] = year
                        new_line["MÊS"] = month
                        df_receipts = pd.concat([df_receipts, pd.DataFrame(new_line)], ignore_index=True)
            
        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        with driver.session() as session:
            session.execute_write(self.import_employee_dataframe_to_neo4j, df_employees)
            session.execute_write(self.import_receipts_dataframe_to_neo4j, df_receipts)
            session.execute_write(self.set_employer_relationships)
            session.execute_write(self.set_receipts_relationships)

        driver.close()

    def check_if_is_manager(self, name: str) -> bool:

        """Checks if the provided name is a manager to someone in the graph"""

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        with driver.session() as session:
            result = session.run("""MATCH (c:Colaborador {NOME: $name})-[:Gere*]->(subordinado)
                                    RETURN COUNT(DISTINCT subordinado) AS NumeroDeSubordinados""", name=name)
            subordinates = result.single()

            if subordinates is not None:
                subordinates = subordinates[0]
            else: 
                subordinates = 0
        
        driver.close()

        if subordinates > 0:
            return True
        else:
            return False
        
    def user_exists(self, name:str) -> bool:

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
        
    def get_personal_data(self, name: str) -> dict:

        """Gets the personal data of the provided name"""

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        with driver.session() as session:
            result = session.run("""MATCH (c:Colaborador {NOME: $name})
                                    RETURN properties(c) as properties""", name=name)
            personal_data = result.single()
            if personal_data is not None:
                personal_data = personal_data[0]
            else: 
                personal_data = None
        
        driver.close()

        return personal_data

employees_graph = CompanyGraph()

if __name__ == "__main__":
    employees_graph.create_graph()