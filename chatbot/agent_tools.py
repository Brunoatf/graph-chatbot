
from typing import Any, Union
from langchain.prompts import PromptTemplate
import sqlite3
from langchain.chains import LLMChain
from langchain.chains import GraphCypherQAChain
from langchain.callbacks.base import BaseCallbackHandler
from langchain.graphs import Neo4jGraph
from langchain.prompts import StringPromptTemplate
import pandas as pd
from neo4j import exceptions


from chatbot.prompts import receipts_chain_prompt, personal_data_prompt_template, cypher_query_prompt_template, cypher_qa_prompt_template

from chatbot.llm import CustomLLM
import streamlit as st
from chatbot.chatbot_data.graph_manager import employees_graph
from langchain.schema import StrOutputParser, BaseOutputParser

llm = CustomLLM()

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
    
class RecibosFuncionariosPrompt(StringPromptTemplate):

    template: str
    user_name: str
    receipt_data: str

    def format(self, **kwargs) -> str:
        kwargs['user_name'] = self.user_name
        kwargs['receipt_data'] = self.receipt_data
        return self.template.format(**kwargs)

def get_cypher_qa_chain(user_name: str):

    graph = Neo4jGraph(
        url="neo4j+s://82046d1f.databases.neo4j.io", username="neo4j", password="LyvEFa1Eyf0VtMaELDfjqW6uyaF3pckSRDLY0z_koQU"
    )

    cypher_generation_prompt = CypherQueryPrompt(
        input_variables=["question"], user_name=user_name, template=cypher_query_prompt_template)

    cypher_generation_chain = LLMChain(llm=llm, prompt=cypher_generation_prompt)

    cypher_qa_prompt = PromptTemplate(
        input_variables=['context', 'question'], template=cypher_qa_prompt_template)
    
    qa_chain = LLMChain(llm=llm, prompt=cypher_qa_prompt) 

    cypher_qa_chain = GraphCypherQAChain(
        graph=graph,
        graph_schema=graph.get_schema,
        verbose=True,
        cypher_generation_chain=cypher_generation_chain,
        qa_chain=qa_chain,
        top_k=20
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
    
    personal_data_chain = LLMChain(llm=llm, prompt=personal_data_prompt)

    return personal_data_chain

def get_personal_receipts_chain(user_name: str):

    file_path = './chatbot/chatbot_data/recibos.xlsx'

    df = pd.read_excel(file_path)

    filtered_data = df[df['NOME'] == user_name]
    df.drop("NOME", axis=1, inplace=True)

    prompt_template_receipts = RecibosFuncionariosPrompt(
        input_variables=['input', 'table_info', 'top_k'],
        template=receipts_chain_prompt,
        user_name=user_name,
        receipt_data=filtered_data.to_string(index=False)
    )

    personal_receipts_chain = LLMChain(llm=llm, prompt=prompt_template_receipts)

    return personal_receipts_chain