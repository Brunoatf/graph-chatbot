import langchain
from langchain.utilities import SQLDatabase
from langchain.llms import OpenAI
from langchain_experimental.sql import SQLDatabaseChain
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.prompts import StringPromptTemplate
from langchain.llms import OpenAI
from langchain.utilities import SerpAPIWrapper
from langchain.chains import LLMChain
from typing import List, Union
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
import re
import streamlit as st
import os
from langchain.callbacks.streaming_stdout_final_only import (
    FinalStreamingStdOutCallbackHandler,
)
from chatbot.llm import CustomLLM

from chatbot.prompts import chatbot_few_shots, chatbot_prompt
from chatbot.agent_tools import cypher_qa_chain, db_chain_recibos_funcionarios

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

class CallbackHandler(StreamingStdOutCallbackHandler):
    def __init__(self):
        self.content: str = ""

    def on_llm_new_token(self, token: str, **kwargs: any) -> None:
        self.content += token
        if "Resposta:" in self.content:
            # now we're in the final answer section, but don't print yet
            st.session_state.stream = True
            self.content = ""
        if st.session_state.stream == True:
            st.session_state.container.markdown(self.content)

llm = CustomLLM(temperature=0, verbose=True, streaming=True, callbacks=[CallbackHandler()],openai_api_key="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", max_tokens=1024)

tools = [
    Tool(
        name="Assistente_Cadastro_Funcionarios",
        func=cypher_qa_chain.run,
        description="""Assistente capaz de consultar dados de cadastro de funcionários, como estatísticas da equipe, informações pessoais e dados relacionadas a cargos.
        Permite consultar dados relacionados a estrutura hierárquica da empresa. Leve em consideração que o termo 'equipe' se refere aos
        subordinados diretos de um gestor, enquanto termos como 'departamento' e 'subordinados' se referem a todos os funcionários que estão abaixo de um gestor."""
    ),
    Tool(
        name="Assistente_Recibos_Funcionarios",
        func=db_chain_recibos_funcionarios.run,
        description="""Assistente capaz consultar dados relacionados a recibos e pagamentos de funcionários.
        Útil para solicitar a geração/consulta de recibos."""
    )
]

# Set up a prompt template
class CustomPromptTemplate(StringPromptTemplate):
    # The template to use
    template: str
    # The list of tools available
    tools: List[Tool]

    def format(self, **kwargs) -> str:

        # Get the intermediate steps (AgentAction, Observation tuples)
        # Format them in a particular way
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservação: {observation}\nPensamento: "

        kwargs["agent_scratchpad"] = thoughts
        kwargs["user"] = (st.session_state.user_name).upper()
        kwargs["few_shots"] = chatbot_few_shots.format(user=st.session_state.user_name)
        kwargs["domain"] = "bases de dados de recursos humanos da Vtal"
        kwargs["contact"] = "o supervisor de RH"
        kwargs["recommendation"] = "checar manualmente as bases de dados da Vtal"

        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])

        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])

        return self.template.format(**kwargs)

prompt = CustomPromptTemplate(
    template=chatbot_prompt,
    tools=tools,
    input_variables=["input", "chat_history", "intermediate_steps"]
)

class CustomOutputParser(AgentOutputParser):

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:

        print("llm output", llm_output)

        # Parse out the action and action input
        regex = r"Ação\s*\d*\s*:(.*?)\nTexto da Ação\s*\d*\s*:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            if "Resposta:" in llm_output:
                return AgentFinish(
                    # Return values is generally always a dictionary with a single `output` key
                    # It is not recommended to try anything else at the moment :)
                    return_values={"output": llm_output.split("Resposta:")[-1].strip()},
                    log=llm_output,
                )
            raise OutputParserException(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        # Return the action and action input
        return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)

output_parser = CustomOutputParser()

# LLM chain consisting of the LLM and a prompt
llm_chain = LLMChain(llm=llm, prompt=prompt)

tool_names = [tool.name for tool in tools]

class ChatBot():

    def __init__(self):
        
        #Initialize memory:
        memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=1000, memory_key="chat_history")

        #Initialize agent:
        agent = LLMSingleActionAgent(
            llm_chain=llm_chain,
            output_parser=output_parser,
            stop=["\nObservação: "],
            allowed_tools=tool_names
        )

        #Initialize agent executor:
        self.agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, memory=memory, verbose=True, handle_parsing_errors=True)

    def __call__(self, input):
        response = self.agent_executor.run(input)
        return response