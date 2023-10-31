from anthropic import AuthenticationError
import openai
import streamlit as st
from chatbot.chatbot_implementation import ChatBot
from PIL import Image

#Set page title
im = Image.open('./images/neuralmind.png')
st.set_page_config(page_title="Chatbot RH", page_icon = im)

#Hide default Streamlit footer and menu
hide_default_format = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       </style>
       """
st.markdown(hide_default_format, unsafe_allow_html=True)

with st.sidebar:
    st.write("ℹ️ Antes de iniciar uma conversa, preencha os campos abaixo para obter uma experiência personalizada.")
    user_name = st.text_input("Seu nome completo", key="chatbot_user_name")
    st.write("ℹ️ As informações retornadas ao longo da conversa fazem referência a dados de uma empresa fictícia chamada MRKL, criada apenas para fins de demonstração.")
    
st.title("💬 ChatBot RH - Versão de Testes")
st.caption("Desenvolvido por NeuralMind 🧠")

if "user_name" not in st.session_state:
    st.session_state["user_name"] = None

if "messages" not in st.session_state:

    st.session_state["messages"] = [
        {"role": "assistant",
         "content": """Olá, sou um assistente virtual inteligente capaz de navegar nas bases de dados do departamento de recursos humanos da MRKL. Sinta-se livre para tirar as suas dúvidas relacionadas a dados cadastrais ou recibos de colaboradores. Como posso te ajudar?"""}
    ]

    st.session_state.stream = False
    st.session_state.chatbot = ChatBot(st.session_state.user_name)

for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        st.chat_message(msg["role"]).write(msg["content"])
    else:
        st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    
    if not user_name:
        st.info("Por favor adicione o seu nome completo para continuar.")
        st.stop()
        
    if user_name != st.session_state.user_name:
        st.session_state.user_name = user_name
        st.session_state.chatbot.user_name = user_name.upper()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        st.session_state["container"] = st.empty()
        container = st.session_state.container
        st.session_state.container = container
        try:
            response = st.session_state.chatbot(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response})
            container.write(response)
        except Exception as e:
            st.error(f"Ocorreu um erro no processamento da mensagem. Tente novamente.")
        st.session_state.stream = False
