from typing import Any, List, Mapping, Optional
import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.schema import AIMessage, HumanMessage
import os

class CustomLLM(LLM):

    model_name: str = "gpt-3.5-turbo-16k"

    @property
    def _llm_type(self) -> str:
        return "custom" 
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:

        encapsuled_model = ChatOpenAI(
            model_name=self.model_name,
            openai_api_key=os.getenv('openai_api_key'),
            streaming=True,
            **kwargs
        )
                        
        messages = [
            HumanMessage(
                content=prompt
            )
        ]
        
        response = encapsuled_model(messages, stop, run_manager, **kwargs)

        return(response.content)
    
class ChatbotLLM(CustomLLM):

    current_prompt: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def manually_generate_answer(self, failed_answer: str):
        prompt = self.current_prompt + failed_answer + "\nResposta: "
        print('manually generated answer prompt: ', prompt)
        answer = super()._call(prompt)
        return answer
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:

        self.current_prompt = prompt

        response = super()._call(prompt, stop, run_manager, **kwargs)

        return(response)