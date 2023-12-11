from anthropic import AuthenticationError
import openai
import streamlit as st
from chatbot.chatbot_implementation import ChatBot
from PIL import Image
from utils import extract_table, markdown_table_to_excel, chat_to_word
from chatbot.chatbot_data.graph_manager import employees_graph

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

if "user_name" not in st.session_state:
    st.session_state["user_name"] = None

#Table counter counts the index of the table to be downloaded:
if "table_counter" not in st.session_state:
    st.session_state["table_counter"] = 0

#If there are no messages, start new conversation and chatbot
if "messages" not in st.session_state:

    st.session_state["messages"] = [
        {"role": "assistant",
         "content": """Olá, sou um assistente virtual inteligente capaz de navegar nas bases de dados do departamento de recursos humanos da MRKL. Sinta-se livre para tirar as suas dúvidas relacionadas a dados cadastrais ou recibos de colaboradores. Como posso te ajudar?"""}
    ]

    st.session_state.stream = False
    st.session_state.disable_input = False
    st.session_state.chatbot = ChatBot(st.session_state.user_name)

with st.sidebar:
    st.write("ℹ️ Antes de iniciar uma conversa, forneca o seu nome completo para obter uma experiência personalizada.")
    user_name = st.text_input("Seu nome completo", key="chatbot_user_name", disabled=st.session_state.disable_input)
    st.write("ℹ️ As informações retornadas ao longo da conversa fazem referência a dados de uma empresa fictícia chamada MRKL, criada apenas para fins de demonstração.")
    
st.title("💬 ChatBot RH - Versão de Testes")
st.caption("Desenvolvido por NeuralMind 🧠")

for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        st.chat_message(msg["role"]).write(msg["content"])
    elif msg["role"] == "user":
        st.chat_message(msg["role"]).write(msg["content"])
    elif msg["role"] == "button":
        st.download_button("Baixar tabela como arquivo Excel", msg["content"]["file"], file_name=msg["content"]["name"])

def disable_input() -> None:
    st.session_state.disable_input = True

def end_processing() -> None:
    st.session_state.disable_input = False
    st.rerun()

def process_message(prompt: str) -> None:

    '''Processes the provided message and write the response to the session state.'''

    st.session_state.messages.append({"role": "user", "content": prompt})

    if not user_name:
        st.session_state.messages.append({"role": "assistant",
                                   "content": "Por favor, adicione o seu nome completo para continuar."})
        end_processing()

    if user_name != st.session_state.user_name:
        st.session_state.user_name = user_name
        st.session_state.chatbot.user_name = user_name.upper()

    if not employees_graph.user_exists(user_name):
        st.session_state.messages.append({"role": "assistant",
                 "content": f"Não consegui processar a sua mensagem porque o nome de usuário '{user_name}' não foi encontrado na minha base de dados. Por favor, verifique o nome digitado e tente novamente."})
        end_processing()

    st.chat_message("user").write(prompt)
    with st.spinner("Aguarde enquanto sua mensagem é processada..."):
        with st.chat_message("assistant"):
            st.session_state["container"] = st.empty()
            container = st.session_state.container #stores the streaming response

            try:
                response = st.session_state.chatbot(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})
                container.write(response.replace("$", "\$")) #For avoiding LaTeX rendering

                extracted_table = extract_table(response)
                if extracted_table:
                    file = markdown_table_to_excel(extracted_table)
                    st.session_state.messages.append({"role": "button", "content": {"file": file, "name": f"tabela_{st.session_state.table_counter}.xlsx"}})
                    st.download_button("Baixar tabela como arquivo Excel", file, file_name=f"tabela_{st.session_state.table_counter}.xlsx")
                    st.session_state.table_counter += 1

            except Exception as e:
                st.session_state.messages.append({"role": "assistant",
                    "content": f"Ocorreu um erro no processamento da mensagem. Tente novamente."})
            
            st.session_state.stream = False
            end_processing()

if prompt := st.chat_input(disabled=st.session_state.disable_input, on_submit=disable_input, placeholder="Digite sua mensagem aqui..."):
    process_message(prompt)

with st.sidebar:
    st.write("👇 Você pode baixar a conversa atual como um documento Word clicando no botão abaixo.")
    conversation_docx = chat_to_word(st.session_state.messages, st.session_state.user_name)
    st.download_button("Baixar conversa como arquivo Word", conversation_docx, file_name=f"historico_conversa.docx")
