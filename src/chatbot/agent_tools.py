
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
from neo4j import GraphDatabase
import re


from chatbot.prompts import receipts_chain_prompt, personal_data_prompt_template, cypher_query_prompt_template, cypher_qa_prompt_template, cypher_correction_prompt_template

from chatbot.llm import CustomLLM
import streamlit as st
from chatbot.chatbot_data.graph_manager import employees_graph
from langchain.schema import StrOutputParser, BaseOutputParser

llm = CustomLLM()
llm_gpt4 = CustomLLM(model_name="gpt-4-1106-preview")

class CypherQueryPrompt(StringPromptTemplate):

    template: str
    user_name: str

    def format(self, **kwargs) -> str:
        kwargs['user_name'] = self.user_name
        return self.template.format(**kwargs)
    
class CypherCorrectionPrompt(StringPromptTemplate):

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
    
class CustomGraphCypherQAChain(GraphCypherQAChain):
    
    cypher_correction_chain: LLMChain

    def extract_cypher(self, text: str) -> str:
        """Extract Cypher code from a text.

        Args:
            text: Text to extract Cypher code from.

        Returns:
            Cypher code extracted from the text.
        """
        # The pattern to find Cypher code enclosed in triple backticks
        pattern = r"```(.*?)```"

        # Find all matches in the input text
        matches = re.findall(pattern, text, re.DOTALL)

        return matches[0] if matches else text

    def _call(
        self,
        inputs,
    ):
        question = inputs[self.input_key]

        print("Question: ", question)

        generated_cypher = self.cypher_generation_chain.run(
            {"question": question}
        )

        generated_cypher = self.extract_cypher(generated_cypher)

        print("Generated cypher: ", generated_cypher)

        if generated_cypher:
            try:
                context = self.graph.query(generated_cypher)[: self.top_k]
            except ValueError as e:
                print("Error: ", e.message)
                new_query = self.cypher_correction_chain.run(
                    {"problematic_query": generated_cypher, "error_message": str(e)}
                )
                new_query = self.extract_cypher(new_query)
                print("New query: ", new_query)
                context = self.graph.query(new_query)[: self.top_k]
        else:
            context = []

        print("Context: ", context)

        result = self.qa_chain(
            {"question": question, "context": context},
        )
        
        final_result = result[self.qa_chain.output_key]

        print("Final result: ", final_result)

        output = {"result": final_result}

        return output

def get_cypher_qa_chain(user_name: str):

    url = "neo4j+s://82046d1f.databases.neo4j.io"
    username = "neo4j"
    password = "LyvEFa1Eyf0VtMaELDfjqW6uyaF3pckSRDLY0z_koQU"

    graph = Neo4jGraph(
        url=url, 
        username=username,
        password=password,
    )

    cypher_generation_prompt = CypherQueryPrompt(
        input_variables=["question"], user_name=user_name, template=cypher_query_prompt_template)

    cypher_generation_chain = LLMChain(
        llm=llm_gpt4,
        prompt=cypher_generation_prompt
    )

    cypher_qa_prompt = PromptTemplate(
        input_variables=['context', 'question'], template=cypher_qa_prompt_template)
    
    qa_chain = LLMChain(llm=llm, prompt=cypher_qa_prompt)

    cypher_correction_prompt = CypherCorrectionPrompt(
        input_variables=["problematic_query", "error_message"],
        user_name=user_name,
        template=cypher_correction_prompt_template
    )

    cypher_correction_chain = LLMChain(
        llm=llm_gpt4,
        prompt=cypher_correction_prompt
    )

    cypher_qa_chain = CustomGraphCypherQAChain(
        graph=graph,
        graph_schema=graph.get_schema,
        verbose=True,
        cypher_generation_chain=cypher_generation_chain,
        cypher_correction_chain=cypher_correction_chain,
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