# Chabot RH - Protótipo

Este projeto consiste no protótipo de demonstração de um chatbot capaz de interagir com bases de dados representando a hierarquia e os recibos de uma empresa. Os dados utilizados para esta implementação são fictícios e seguem o modelo e conveções da empresa V.tal. 

## Implementação

Para a implementação, utiliza-se:

- Neo4j Aura: Serviço de banco de dados em grafo na nuvem.
- Streamlit: Framework para construção de aplicações web em Python.
- Python 3: Linguagem de programação utilizada para a implementação do chatbot.
- LangChain: Biblioteca para implementação de agentes baseados em LLMs.
- OpenAI API: API para geração de texto baseada em LLMs.

## Execução

Para executar o projeto, é necessário ter o Python 3 instalado. Em seguida, instale as dependências do projeto com o comando:

```pip install -r requirements.txt```

Após a instalação das dependências, acesse a pasta do código fonte com:

```cd src```

Em seguida, execute a aplicação do Streamlit com o comando abaixo:

```python3 -m streamlit run App.py```

Uma instância do navegador será aberta com a aplicação em localhost:8501.

Para o funcionamento do Chatbot, é necessário que haja uma variável de ambiente chamada **OPENAI_API_KEY** com a chave de acesso à API da OpenAI.