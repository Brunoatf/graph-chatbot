from typing import Any, List, Mapping, Optional
import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.schema import AIMessage, HumanMessage

class CustomLLM(LLM):

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
            model_name="gpt-3.5-turbo-16k",
            openai_api_key=st.session_state.openai_api_key,
            streaming=True
        )
                        
        messages = [
            HumanMessage(
                content=prompt
            )
        ]
        
        
        response = encapsuled_model(messages, stop, run_manager, **kwargs)

        return(response.content)