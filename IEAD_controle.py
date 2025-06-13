import streamlit as st
import pandas as pd
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === AUTENTICAÇÃO via st.secrets ===
creds_dict = json.loads(st.secrets["gcp_service_account"])
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

# === CONFIGURAÇÃO DA PLANILHA ===
SPREADSHEET_ID = "1u5zQ5H61_clP-9Cihw_JhfQQ4M2DrESp"
RANGE_NAME = "Sheet1!A:I"

# === FUNÇÕES ===
def ler_dados():
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])
    if not values:
        return pd.DataFrame()
    headers = values[0]
    data = values[1:]
    return pd.DataFrame(data, columns=headers)

def adicionar_dado(novo_registro):
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME,
        valueInputOption="RAW",
        body={"values": [novo_registro]},
    ).execute()

# === INTERFACE ===
st.set_page_config("📊 Controle de Vendas", layout="wide")
st.title("📊 Sistema de Gestão de Vendas")

df = ler_dados()

if not df.empty and 'Data do Pagamento' in df.columns:
    df['Data do Pagamento'] = pd.to_datetime(df['Data do Pagamento'], errors='coerce')

# FILTROS
st.sidebar.header("🔎 Filtros")
vendedor = st.sidebar.selectbox("Vendedor", ['Todos'] + sorted(df['Vendedor'].dropna().unique().tolist()))
status = st.sidebar.selectbox("Status", ['Todos'] + sorted(df['Status'].dropna().unique().tolist()))
produto = st.sidebar.text_input("Produto contém...")
data_ini = st.sidebar.date_input("Data Inicial", datetime(2024, 1, 1))
data_fim = st.sidebar.date_input("Data Final", datetime.today())

if vendedor != 'Todos':
    df = df[df['Vendedor'] == vendedor]
if status != 'Todos':
    df = df[df['Status'] == status]
if produto:
    df = df[df['Produto'].str.contains(produto, case=False, na=False)]
df = df[(df['Data do Pagamento'] >= pd.to_datetime(data_ini)) & (df['Data do Pagamento'] <= pd.to_datetime(data_fim))]

st.subheader("📋 Registros")
st.dataframe(df, use_container_width=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Baixar CSV", csv, "vendas.csv", "text/csv")

# FORMULÁRIO
st.subheader("➕ Novo Registro")
with st.form("formulario", clear_on_submit=True):
    col1, col2 = st.columns(2)
    cargo = col1.text_input("Cargo")
    produto = col2.text_input("Produto")
    tipo = st.selectbox("Tipo", ["Venda", "Serviço", "Outro"])
    valor_unitario = st.number_input("Valor Unitário", min_value=0.0, format="%.2f")
    quantidade = st.number_input("Quantidade", min_value=1)
    total = valor_unitario * quantidade
    status = st.selectbox("Status", ["Pago", "Pendente", "Cancelado"])
    data_pagamento = st.date_input("Data do Pagamento", value=datetime.today())
    vendedor = st.text_input("Vendedor")
    
    st.markdown(f"**Total Calculado: R$ {total:.2f}**")
    
    if st.form_submit_button("Salvar Registro"):
        novo = [
            cargo, produto, tipo, f"{valor_unitario:.2f}", str(int(quantidade)),
            f"{total:.2f}", status, str(data_pagamento), vendedor
        ]
        adicionar_dado(novo)
        st.success("✅ Registro salvo com sucesso!")
        st.experimental_rerun()