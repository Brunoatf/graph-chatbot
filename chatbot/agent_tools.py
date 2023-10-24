
from langchain.prompts import PromptTemplate
from langchain.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.chains import LLMChain
from langchain.chains import GraphCypherQAChain
from langchain.graphs import Neo4jGraph
import pandas as pd

from chatbot.prompts import sql_chain_prompt
from chatbot.prompts import cypher_query_prompt, cypher_qa_prompt

from chatbot.llm import CustomLLM

db_recibos_funcionarios = SQLDatabase.from_uri("sqlite:///./chatbot/chatbot_data/recibos_funcionarios.db")

llm = CustomLLM()

prompt_template_sql = PromptTemplate(
    input_variables=['input', 'table_info', 'top_k'],
    template=sql_chain_prompt
)

db_chain_recibos_funcionarios = SQLDatabaseChain(
    database=db_recibos_funcionarios,
    llm_chain=LLMChain(prompt=prompt_template_sql, llm=llm),
    top_k=20,
    verbose=True,
    use_query_checker=True)

graph = Neo4jGraph(
    url="neo4j+s://82046d1f.databases.neo4j.io", username="neo4j", password="LyvEFa1Eyf0VtMaELDfjqW6uyaF3pckSRDLY0z_koQU"
)

cypher_generation_prompt = PromptTemplate(
    input_variables=["question"], template=cypher_query_prompt)

cypher_qa_prompt = PromptTemplate(
    input_variables=['context', 'question'], template=cypher_qa_prompt)

cypher_qa_chain = GraphCypherQAChain.from_llm(
    llm,
    graph=graph,
    verbose=True,
    cypher_prompt=cypher_generation_prompt,
    qa_prompt=cypher_qa_prompt,
    top_k=20,
)