
from langchain.prompts import PromptTemplate
from langchain.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.chains import LLMChain
from langchain.chains import GraphCypherQAChain
from langchain.graphs import Neo4jGraph
from langchain.prompts import StringPromptTemplate
import pandas as pd

from chatbot.prompts import sql_chain_prompt, personal_data_prompt_template, cypher_query_prompt_template, cypher_qa_prompt_template

from chatbot.llm import CustomLLM
import streamlit as st
from chatbot.chatbot_data.graph_manager import employees_graph
from langchain.schema import StrOutputParser

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


class CypherQueryPrompt(StringPromptTemplate):

    template: str
    user_name: str

    def format(self, **kwargs) -> str:
        kwargs['user_name'] = self.user_name
        return self.template.format(**kwargs)
    
class PersonalDataPrompt(StringPromptTemplate):

    template: str
    user_name: str
    personal_data: str

    def format(self, **kwargs) -> str:
        kwargs['user_name'] = self.user_name
        kwargs['personal_data'] = self.personal_data
        return self.template.format(**kwargs)

def get_cypher_qa_chain(user_name: str):

    graph = Neo4jGraph(
        url="neo4j+s://82046d1f.databases.neo4j.io", username="neo4j", password="LyvEFa1Eyf0VtMaELDfjqW6uyaF3pckSRDLY0z_koQU"
    )

    cypher_generation_prompt = CypherQueryPrompt(
        input_variables=["question"], user_name=user_name, template=cypher_query_prompt_template)

    cypher_qa_prompt = PromptTemplate(
        input_variables=['context', 'question'], template=cypher_qa_prompt_template)
    
    cypher_qa_chain = GraphCypherQAChain.from_llm(
        llm,
        graph=graph,
        verbose=True,
        cypher_prompt=cypher_generation_prompt,
        qa_prompt=cypher_qa_prompt,
        top_k=20,
    )

    return cypher_qa_chain

def get_personal_data_chain(user_name: str):

    personal_data_dict = employees_graph.get_personal_data(user_name)
    if personal_data_dict is None:
        return None

    personal_data = ""
    for key, value in personal_data_dict.items():
        personal_data += f"{key}: {value}\n"

    personal_data_prompt = PersonalDataPrompt(
        input_variables=["query"], template=personal_data_prompt_template, personal_data=personal_data, user_name=user_name)
    
    runnable = LLMChain(llm=llm, prompt=personal_data_prompt)

    return runnable