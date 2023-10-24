from typing import Any, List, Mapping, Optional
import streamlit as st

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.llms import OpenAI

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
        
        encapsuled_model = OpenAI(temperature=0,
                          verbose=True,
                          openai_api_key=st.session_state.openai_api_key,
                          max_tokens=1024)
        
        response = encapsuled_model(prompt, stop, run_manager, **kwargs)

        return(response)