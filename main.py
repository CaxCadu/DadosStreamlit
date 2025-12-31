import streamlit as st
import os
import json
import pandas as pd
from groq import Groq
import plotly.express as px

PASTA = "uploads"
os.makedirs(PASTA, exist_ok=True)

st.set_page_config(layout="wide")
st.title("Assistente de Análise de Dados")
st.write("Insights automáticos e gráficos gerados por IA")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.sidebar.title("📁 Upload de dados")

arquivo = st.sidebar.file_uploader(
    "Envie um CSV ou XLSX",
    type=["csv", "xlsx"]
)

df = None

if arquivo:
    caminho = os.path.join(PASTA, arquivo.name)
    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())

    if arquivo.name.endswith(".csv"):
        df = pd.read_csv(caminho)
    else:
        df = pd.read_excel(caminho)

    st.sidebar.success(f"Arquivo carregado: {arquivo.name}")

if df is not None:
    st.subheader("📄 Pré-visualização do Dataset")
    st.dataframe(df.head())

st.divider()
st.subheader("💬 Assistente de Análise")

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

prompt = st.chat_input("Pergunte algo ou peça análises/gráficos")

if prompt and df is not None:

    contexto_dados = f"""
Você é um analista de dados experiente.

RESPONDA EXCLUSIVAMENTE EM JSON, sem texto fora do JSON.

Formato obrigatório:

{{
  "insights": [
    "Insight 1",
    "Insight 2"
  ],
  "graficos": [
    {{
      "tipo": "line | bar | pie | scatter | hist",
      "x": "nome_da_coluna",
      "y": "nome_da_coluna_ou_null",
      "titulo": "Título do gráfico"
    }}
  ]
}}

REGRAS:
- Use apenas colunas existentes.
- Gere no máximo 5 gráficos.
- Se não fizer sentido gráfico, retorne lista vazia.

Dataset:
Linhas: {df.shape[0]}
Colunas: {df.shape[1]}

Tipos das colunas:
{df.dtypes}

Amostra:
{df.head(50).to_string()}
"""

    mensagens = [
        {"role": "system", "content": contexto_dados},
        *st.session_state["messages"],
        {"role": "user", "content": prompt}
    ]

    st.session_state["messages"].append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        resposta = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=mensagens,
            temperature=0.2
        )

        conteudo = resposta.choices[0].message.content

        try:
            plano = json.loads(conteudo)
        except:
            st.error("Erro ao interpretar a resposta da IA")
            st.code(conteudo)
            st.stop()

        if plano.get("insights"):
            st.subheader("📌 Insights")
            for i in plano["insights"]:
                st.markdown(f"- {i}")

        if plano.get("graficos"):
            st.subheader("📈 Gráficos Gerados")

            for g in plano["graficos"]:
                tipo = g["tipo"]
                x = g.get("x")
                y = g.get("y")
                titulo = g.get("titulo", "")

                try:
                    if tipo == "line":
                        fig = px.line(df, x=x, y=y, title=titulo)
                    elif tipo == "bar":
                        fig = px.bar(df, x=x, y=y, title=titulo)
                    elif tipo == "pie":
                        fig = px.pie(df, names=x, values=y, title=titulo)
                    elif tipo == "scatter":
                        fig = px.scatter(df, x=x, y=y, title=titulo)
                    elif tipo == "hist":
                        fig = px.histogram(df, x=x, title=titulo)
                    else:
                        continue

                    st.plotly_chart(fig, use_container_width=True)

                except:
                    st.warning(f"Erro ao gerar gráfico: {titulo}")

        st.session_state["messages"].append(
            {"role": "assistant", "content": conteudo}
        )

elif prompt and df is None:
    st.warning("Faça upload de um arquivo antes de usar o assistente.")
