from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.prompts import StringPromptTemplate
from langchain.chains import LLMChain
from typing import List, Union
from langchain.schema import AgentAction, AgentFinish
from langchain.memory import ConversationSummaryBufferMemory
import re
import streamlit as st
from chatbot.llm import ChatbotLLM
from chatbot.prompts import chatbot_few_shots_manager, chatbot_few_shots_employee, chatbot_prompt
from chatbot.agent_tools import get_cypher_qa_chain, get_personal_data_chain, get_personal_receipts_chain
from chatbot.chatbot_data.graph_manager import employees_graph
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import warnings

warnings.filterwarnings("ignore", message="Importing llm_cache from langchain root module is no longer supported. ")

class CallbackHandler(StreamingStdOutCallbackHandler):
    def __init__(self):
        self.content: str = ""

    def on_llm_new_token(self, token: str, **kwargs: any) -> None:
        self.content += token
        if "Finalizar:" in self.content:
            # now we're in the final answer section, but don't print yet
            st.session_state.stream = True
            self.content = ""
        if st.session_state.stream == True:
            st.session_state.container.markdown(self.content.replace("$", "\$"))

class CustomPromptTemplate(StringPromptTemplate):
    # The template to use
    template: str
    # The list of tools available
    tools: List[Tool]
    # User name
    user_name: str
    is_manager: bool

    def format(self, **kwargs) -> str:

        # Get the intermediate steps (AgentAction, Observation tuples)
        # Format them in a particular way
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservação: {observation}\nPensamento: "

        kwargs["agent_scratchpad"] = thoughts
        kwargs["user"] = self.user_name
        if self.is_manager:
            kwargs["few_shots"] = chatbot_few_shots_manager.format(user=self.user_name)
        else:
            kwargs["few_shots"] = chatbot_few_shots_employee.format(user=self.user_name)
        kwargs["domain"] = "bases de dados de recursos humanos da MRKL"
        kwargs["contact"] = "o supervisor de RH"
        kwargs["recommendation"] = "checar manualmente as bases de dados da MRKL"

        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])

        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])

        return self.template.format(**kwargs)

class CustomOutputParser(AgentOutputParser):

    llm: ChatbotLLM
    allowed_tools: List[str]

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:

        # Parse out the action and action input
        regex = r"Ação\s*\d*\s*:(.*?)\nTexto da Ação\s*\d*\s*:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            if "Finalizar:" in llm_output:
                return AgentFinish(
                    # Return values is generally always a dictionary with a single `output` key
                    # It is not recommended to try anything else at the moment :)
                    return_values={"output": llm_output.split("Finalizar:")[-1].strip()},
                    log=llm_output,
                )
            answer = self.llm.manually_generate_answer(llm_output)
            return AgentFinish(
                return_values={"output": answer},
                log=f"Could not parse LLM output: `{llm_output}`. Manually generated answer: `{answer}`"
            )
        action = match.group(1).strip()
        if action not in self.allowed_tools:
            disclaimer = f"A ação {action} não existe, use obrigatoriamente uma dentre {self.allowed_tools}."
            llm_output += f"\n{disclaimer}"
            action = self.llm.manually_generate_action(llm_output) 
        action_input = match.group(2)
        # Return the action and action input
        return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)

class ChatBot():

    def __init__(self, user_name: str):

        if user_name is None:
            self._user_name = "Usuário"
        else:
            self._user_name = user_name
            self.start_agent()

    def start_agent(self):

        #Initialize LLM:
        llm = ChatbotLLM(temperature=0, verbose=True, streaming=True, callbacks=[CallbackHandler()], max_tokens=1024)
        
        #Initialize memory:
        self.memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=1000, memory_key="chat_history")

        #Check if user is a manager:
        is_manager = employees_graph.check_if_is_manager(self._user_name)

        #Agent tools:
        self.tools = self.get_tools(self._user_name, is_manager)

        #Chatbot prompt:
        self.prompt = CustomPromptTemplate(
            template=chatbot_prompt,
            tools=self.tools,
            user_name=self._user_name,
            is_manager=is_manager,
            input_variables=["input", "chat_history", "intermediate_steps"]
        )

        # LLM chain consisting of the LLM and a prompt
        llm_chain = LLMChain(llm=llm, prompt=self.prompt)

        #Chatbot output parser:
        output_parser = CustomOutputParser(llm=llm, allowed_tools=[tool.name for tool in self.tools])

        #Initialize agent:
        self.agent = LLMSingleActionAgent(
            llm_chain=llm_chain,
            output_parser=output_parser,
            stop=["\nObservação: "],
            allowed_tools=[tool.name for tool in self.tools]
        )

    def get_tools(self, new_name, is_manager):
        tools = []
        if is_manager:
            cypher_qa_chain = get_cypher_qa_chain(user_name=new_name)
            tools.append(Tool(
                name="Assistente_Dados_Pessoais_E_Subordinados",
                func=cypher_qa_chain.run,
                description="""Assistente capaz de consultar simultaneamente múltiplos dados pessoais/cadastrais de 
            {new_name} e dos seus subordinados, além de recibos. Permite obter estatísticas e valores relacionados aos funcionários e seus recibos."""
            ))
        else:
            personal_data_chain = get_personal_data_chain(user_name=new_name)
            if personal_data_chain is not None:
                tools.append(Tool(
                    name="Assistente_Dados_Pessoais",
                    func=personal_data_chain.run,
                    description="""Assistente capaz de consultar dados pessoais/cadastrais do usuário, com exceção de recibos. Não é capaz de consultar dados gerais de funcionários da MRKL ou dados de subordinados, uma vez que o usuário não é um gestor e, portanto, não possui subordinados."""
                ))
            personal_recepits_chain = get_personal_receipts_chain(user_name=new_name)
            if personal_recepits_chain is not None:
                tools.append(Tool(
                    name="Assistente_Recibos",
                    func=personal_recepits_chain.run,
                    description="""Assistente capaz de consultar recibos de pagamento do usuário."""
                ))        
        
        return tools
    
    @property
    def user_name(self):
        return self._user_name
    
    @user_name.setter
    def user_name(self, new_name):
        self._user_name = new_name
        self.start_agent()

    def __call__(self, input):
        agent_executor = AgentExecutor.from_agent_and_tools(agent=self.agent, tools=self.tools, memory=self.memory, verbose=True)
        response = agent_executor.run(input)
        return response