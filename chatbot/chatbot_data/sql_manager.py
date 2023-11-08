import sqlite3
import csv
import openpyxl

# Nome dos bancos de dados SQLite e suas respectivas tabelas
bancos_de_dados = {
    'recibos_funcionarios.db': {
        "recibos_funcionarios": "chatbot/chatbot_data/recibos.xlsx",
    }
}

for banco_de_dados in bancos_de_dados:

    print("Criando banco de dados: ", banco_de_dados)

    # Conectar ao banco de dados SQLite
    conexao = sqlite3.connect(banco_de_dados)
    cursor = conexao.cursor()

    for tabela, arquivo in bancos_de_dados[banco_de_dados].items():

        workbook = openpyxl.load_workbook(arquivo)
        sheet = workbook.active
        nomes_colunas = [cell.value for cell in sheet[1]]

        print("Criando tabela ", tabela)
        print("Colunas: ", nomes_colunas)

        for i, nome_coluna in enumerate(nomes_colunas):
            if nome_coluna == None:
                nomes_colunas[i] = f"None_{i}"
            elif nomes_colunas.count(nome_coluna) > 1:
                nomes_colunas[i] = f"{nome_coluna}_{i}"

        nomes_colunas = [cell.value for cell in sheet[1]]

        # Gerar uma string SQL para criar a tabela com base nos nomes das colunas
        tabela_sql = f"CREATE TABLE IF NOT EXISTS {tabela} ({', '.join([f'col_{nome} TEXT' for nome in nomes_colunas])})"

        print("SQL para criar table: ", tabela_sql)

        # Criar a tabela no banco de dados
        cursor.execute(tabela_sql)

        # Inserir os dados na tabela (ignorando a primeira linha)
        for row in sheet.iter_rows(min_row=2, values_only=True):
            cursor.execute(f"INSERT INTO {tabela} VALUES ({', '.join(['?'] * len(row))})", row)

    # Salvar as alterações e fechar a conexão
    conexao.commit()
    conexao.close()