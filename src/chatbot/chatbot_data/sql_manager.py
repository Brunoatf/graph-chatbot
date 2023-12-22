import sqlite3
import csv
import openpyxl

class SqlManager():

    def __init__(self):
    
        #Dict containing databases and their tables
        self.databases = {
            'recibos_funcionarios.db': {
                "recibos_funcionarios": "chatbot/chatbot_data/data_files/recibos.xlsx",
            }
        }

    def create_databases(self):

        """Creates the databases and their tables"""

        for database in self.databases:

            print("Creating database: ", database)

            conection = sqlite3.connect(database)
            cursor = conection.cursor()

            for table, path in database.items():

                workbook = openpyxl.load_workbook(path)
                sheet = workbook.active
                columns_names = [cell.value for cell in sheet[1]]

                print("Creating table ", table)
                print("Columns: ", columns_names)

                for i, column_name in enumerate(columns_names):
                    if column_name == None:
                        columns_names[i] = f"None_{i}"
                    elif columns_names.count(column_name) > 1:
                        columns_names[i] = f"{column_name}_{i}"

                columns_names = [cell.value for cell in sheet[1]]

                #Create table:
                table_sql = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join([f'col_{nome} TEXT' for nome in columns_names])})"
                cursor.execute(table_sql)

                #Insert data:
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    cursor.execute(f"INSERT INTO {table} VALUES ({', '.join(['?'] * len(row))})", row)

        conection.commit()
        conection.close()

sql_manager = SqlManager()

if __name__ == "__main__":
    sql_manager.create_databases()