import streamlit as st
import pandas as pd
from datetime import datetime
import os
import requests
from io import BytesIO
import gspread # Import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe # Import gspread_dataframe

# --- Google Sheets Configuration ---
# ID da sua planilha do Google Sheets
# Você pode encontrar isso na URL da sua planilha:
# https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID_HERE/edit
GOOGLE_SHEET_ID = "1u5zQ5H61_clP-9Cihw_JhfQQ4M2DrESp" # Substitua pelo ID da sua planilha

# Nome da aba onde os lançamentos (vendas e despesas) serão salvos
SALES_SHEET_NAME = "VendasRegistradas"

# --- Configuração da página ---
st.set_page_config(page_title="Sistema de Vendas", layout="wide")

# Funções auxiliares

def autenticar(usuario, senha):
    """
    Função para autenticar usuários.
    Retorna True se as credenciais forem válidas, False caso contrário.
    """
    credenciais = {
        "junior": "123456",
        "filipe": "7777"
    }
    return credenciais.get(usuario) == senha

@st.cache_resource(ttl=3600) # Cache the connection for 1 hour
def get_gspread_client():
    """Authenticates with Google Sheets using Streamlit Secrets."""
    try:
        # Use st.secrets para autenticação
        gc = gspread.service_account_from_dict(st.secrets["gspread"])
        return gc
    except Exception as e:
        st.error(f"Erro ao autenticar com o Google Sheets: {e}")
        st.stop()

def carregar_dados_google_sheets_lookup():
    """
    Carrega os dados de lookup (venda, nomes, area) diretamente de Google Sheets publicados como CSV.
    VOCÊ PRECISA PUBLICAR CADA ABA DO SEU GOOGLE SHEET COMO CSV E INSERIR AS URLS ABAIXO.
    """
    # URLs dos seus Google Sheets publicados como CSV.
    # Exemplo: https://docs.google.com/spreadsheets/d/e/2PACX-1vR.../pub?gid=123456789&single=true&output=csv
    # Use o link que você me deu para a aba 'area', se for a aba correta
    URL_AREA_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNt8E9Q7Nby2b22C-NPXCzqnREIE95ZEp6YOXq6j801R_NX6RQ5GW1h9TwPbovuw/pub?gid=1705390164&single=true&output=csv"
    
    # ATENÇÃO: SUBSTITUA ESTES PLACEHOLDERS PELAS SUAS PRÓPRIAS URLs CSV PUBLICADAS
    URL_VENDA_CSV = "SUA_URL_CSV_DA_ABA_VENDA_AQUI" # Exemplo: Cole aqui a URL para a aba 'venda'
    URL_NOMES_CSV = "SUA_URL_CSV_DA_ABA_NOMES_AQUI" # Exemplo: Cole aqui a URL para a aba 'nomes'

    try:
        st.info("Carregando dados de lookup do Google Sheets...")
        
        # Carrega df_venda
        response_venda = requests.get(URL_VENDA_CSV)
        response_venda.raise_for_status() # Lança erro para status HTTP ruins
        df_venda = pd.read_csv(BytesIO(response_venda.content))

        # Carrega df_nomes
        response_nomes = requests.get(URL_NOMES_CSV)
        response_nomes.raise_for_status()
        df_nomes = pd.read_csv(BytesIO(response_nomes.content))

        # Carrega df_area
        response_area = requests.get(URL_AREA_CSV)
        response_area.raise_for_status()
        df_area = pd.read_csv(BytesIO(response_area.content))
        
        st.success("Dados de lookup carregados com sucesso!")
        return df_venda, df_nomes, df_area
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar os dados do Google Sheets. Verifique se as URLs CSV estão corretas e acessíveis: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao carregar dados dos arquivos CSV do Google Sheets: {e}")
        st.stop()

def salvar_lancamento_google_sheets(dados):
    """
    Salva os dados de um novo lançamento (venda ou despesa) na aba de vendas do Google Sheets.
    """
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_id(GOOGLE_SHEET_ID)
        worksheet = spreadsheet.worksheet(SALES_SHEET_NAME)

        # Carrega os dados existentes
        df_existente = get_as_dataframe(worksheet, header=1, parse_dates=True)
        
        # Cria um DataFrame temporário com os novos dados
        df_novo = pd.DataFrame([dados])

        # Se o DataFrame existente não estiver vazio, concatena. Caso contrário, usa apenas o novo.
        if not df_existente.empty:
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        else:
            df_final = df_novo
        
        # Salva o DataFrame final de volta na planilha
        set_with_dataframe(worksheet, df_final, include_index=False, row_as_header=False)
        st.success("Lançamento salvo com sucesso no Google Sheets!")
    except Exception as e:
        st.error(f"Erro ao salvar o lançamento no Google Sheets: {e}")

def carregar_lancamentos_google_sheets():
    """
    Carrega os lançamentos registrados da aba de vendas do Google Sheets.
    """
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_id(GOOGLE_SHEET_ID)
        worksheet = spreadsheet.worksheet(SALES_SHEET_NAME)
        df_lancamentos = get_as_dataframe(worksheet, header=1, parse_dates=True)
        return df_lancamentos
    except Exception as e:
        st.error(f"Erro ao carregar lançamentos do Google Sheets: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

def gerar_recibo_txt(dados, caminho="recibo.txt"):
    """
    Gera um recibo de lançamento em formato de texto.
    """
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("RECIBO DE LANÇAMENTO\n")
        f.write("-" * 50 + "\n")
        for chave, valor in dados.items():
            f.write(f"{chave}: {valor}\n")
        f.write("-" * 50 + "\n")

# --- Lógica principal da aplicação Streamlit ---

# Autenticação do usuário
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if autenticar(usuario, senha):
            st.session_state.autenticado = True
            st.session_state.vendedor = usuario
            st.rerun() # Recarregar a página após autenticação bem-sucedida
        else:
            st.error("Credenciais inválidas")
else:
    st.sidebar.title(f"Bem-vindo, {st.session_state.vendedor}")
    aba = st.sidebar.radio("Escolha a aba", ["Registrar Lançamento", "Consultar Lançamentos", "Imprimir Recibo"])

    # Adicionar o botão Sair na sidebar
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.pop('vendedor', None) # Limpa o nome do vendedor
        st.rerun() # Volta para a tela de login

    # Carregar dados de lookup (produtos, nomes, áreas) uma vez ao iniciar a sessão autenticada
    # As URLs para as abas 'venda' e 'nomes' ainda precisam ser inseridas pelo usuário
    df_venda_lookup, df_nomes_lookup, df_area_lookup = carregar_dados_google_sheets_lookup()

    # Inicializa estados de sessão para controle da limpeza de campos no formulário de registro
    if 'reset_form' not in st.session_state:
        st.session_state.reset_form = False
    if 'produto_index' not in st.session_state:
        st.session_state.produto_index = 0
    if 'tipo_index' not in st.session_state:
        st.session_state.tipo_index = 0
    if 'qnt_value' not in st.session_state:
        st.session_state.qnt_value = 1
    if 'status_index' not in st.session_state:
        st.session_state.status_index = 0
    if 'data_compra_value' not in st.session_state:
        st.session_state.data_compra_value = datetime.today()
    if 'data_pagamento_value' not in st.session_state:
        st.session_state.data_pagamento_value = datetime.today()
    if 'expense_value_manual' not in st.session_state: # Estado para o valor da despesa manual
        st.session_state.expense_value_manual = 0.0
    if 'expense_type_index' not in st.session_state: # Novo estado para o índice do tipo de despesa
        st.session_state.expense_type_index = 0

    if aba == "Registrar Lançamento":
        st.title("Registrar Lançamento") # Título atualizado para refletir venda/despesa

        # Tipos de despesas disponíveis
        TIPOS_DESPESA = ["Aluguel", "Material de Escritório", "Transporte", "Alimentação", "Outros"]

        # Se o flag reset_form estiver True, reinicia os valores dos campos que devem ser limpos
        if st.session_state.reset_form:
            st.session_state.produto_index = 0
            st.session_state.tipo_index = 0
            st.session_state.qnt_value = 1
            st.session_state.status_index = 0
            st.session_state.data_compra_value = datetime.today()
            st.session_state.data_pagamento_value = datetime.today()
            st.session_state.expense_value_manual = 0.0 # Reseta o valor da despesa manual
            st.session_state.expense_type_index = 0 # Reseta o tipo de despesa
            st.session_state.reset_form = False # Reseta o flag após reinicializar os valores

        # Campos de Área, Congregação e Nome sempre visíveis e não limpos
        area = st.selectbox("Área", df_area_lookup['area'].unique(), key='area_reg')
        congregacao = st.selectbox("Congregação", df_area_lookup[df_area_lookup['area'] == area]['congregacao'].unique(), key='congregacao_reg')
        nome = st.selectbox("Nome", df_nomes_lookup['nome'].unique(), key='nome_reg')

        # Obtém o cargo do nome selecionado
        cargo = df_nomes_lookup[df_nomes_lookup['nome'] == nome]['cargo'].values[0]
        
        # Adiciona 'Despesa' às opções de produtos disponíveis
        all_products = list(df_venda_lookup['item'].unique())
        if "Despesa" not in all_products:
            all_products.append("Despesa")
        
        # Selectbox de Produto
        produto = st.selectbox("Produto", all_products, key='produto_reg', 
                                index=st.session_state.produto_index)

        # Lógica condicional para campos de valor/quantidade/tipo com base no produto selecionado
        if produto == "Despesa":
            st.subheader("Registro de Despesa")
            
            # Campo para tipo de despesa
            current_expense_type_index = st.session_state.expense_type_index
            if current_expense_type_index >= len(TIPOS_DESPESA):
                current_expense_type_index = 0
            tipo_despesa = st.selectbox("Tipo de Despesa", TIPOS_DESPESA, key='expense_type_reg', index=current_expense_type_index)

            # Campo para valor manual da despesa
            valor_manual_despesa = st.number_input(
                "Valor da Despesa", 
                min_value=0.0, 
                step=0.01, 
                format="%.2f", 
                key='expense_value_manual_input', 
                value=st.session_state.expense_value_manual
            )
            
            # Para despesas, definimos valores padrão para campos não aplicáveis ou simplificamos
            tipo = tipo_despesa # O tipo é o tipo de despesa selecionado
            valor_und = valor_manual_despesa
            qnt = 1
            total = valor_manual_despesa # O total é o valor manual inserido
            st.write(f"**Total da Despesa:** R$ {total:.2f}")

        else: # Lógica existente para registro de vendas de produtos
            st.subheader("Registro de Venda de Produto")
            tipos_disponiveis = df_venda_lookup[df_venda_lookup['item'] == produto]['tipo'].unique()
            
            current_tipo_index = st.session_state.tipo_index
            if current_tipo_index >= len(tipos_disponiveis):
                current_tipo_index = 0
            
            tipo = None # Inicializa tipo como None
            if len(tipos_disponiveis) > 0:
                tipo = st.selectbox("Tipo", tipos_disponiveis, key='tipo_reg', index=current_tipo_index)
            else:
                st.warning("Não há tipos disponíveis para o produto selecionado.")

            valor_und = 0.0
            if tipo is not None:
                valor_und_str = df_venda_lookup[(df_venda_lookup['item'] == produto) & (df_venda_lookup['tipo'] == tipo)]['valor_und'].values[0]
                valor_und = float(str(valor_und_str).replace("R$", "").replace(",", "."))
            else:
                st.write("Selecione um produto e tipo para ver o valor unitário.")

            qnt = st.number_input("Quantidade", min_value=1, step=1, key='qnt_reg', 
                                    value=st.session_state.qnt_value)
            total = valor_und * qnt
            st.write(f"**Valor Unitário:** R$ {valor_und:.2f}")
            st.write(f"**Total:** R$ {total:.2f}")
            
        status = st.selectbox("Status", ["Pago", "Pendente"], key='status_reg', 
                                index=st.session_state.status_index)
        
        data_compra = st.date_input("Data do Lançamento", 
                                    value=st.session_state.data_compra_value, 
                                    key='data_compra_reg')
        
        data_pagamento = "" # Inicializa como string vazia para o caso de status Pendente
        if status == "Pago":
            data_pagamento = st.date_input("Data do Pagamento", 
                                            value=st.session_state.data_pagamento_value, 
                                            key='data_pagamento_reg')


        if st.button("Registrar Lançamento"): # Botão universal para registrar venda ou despesa
            # Validação para despesas e vendas
            if produto == "Despesa" and valor_manual_despesa <= 0:
                st.error("Por favor, insira um valor de despesa válido (maior que zero).")
            elif produto != "Despesa" and tipo is None:
                st.error("Por favor, selecione um tipo de produto válido antes de registrar a venda.")
            else:
                dados_lancamento = { # Dicionário para 'lancamento' pois pode ser venda ou despesa
                    "Data da Compra": data_compra.strftime("%d/%m/%Y"), # Formata para DD/MM/YYYY
                    "Área": area,
                    "Congregação": congregacao,
                    "Nome": nome,
                    "Cargo": cargo,
                    "Produto": produto, # Será 'Despesa' ou o nome do produto
                    "Tipo": tipo, # Será o tipo de despesa ou o tipo de produto
                    "Valor Unitário": valor_und,
                    "Quantidade": qnt,
                    "Total": total,
                    "Status": status,
                    # Formata Data do Pagamento se status for Pago e a data for válida, senão vazia
                    "Data do Pagamento": data_pagamento.strftime("%d/%m/%Y") if status == "Pago" and data_pagamento else "",
                    "Vendedor": st.session_state.vendedor
                }
                salvar_lancamento_google_sheets(dados_lancamento) # Salva no Google Sheets
                gerar_recibo_txt(dados_lancamento)
                st.success("Lançamento registrado e recibo gerado.")
                st.session_state.reset_form = True # Sinaliza para resetar os campos no próximo rerun
                st.rerun() # Reinicia a página para efetivar a limpeza dos campos

    elif aba == "Consultar Lançamentos":
        st.title("Consulta de Lançamentos") # Título atualizado para refletir vendas e despesas
        df_vendas_registradas = carregar_lancamentos_google_sheets() # Carrega do Google Sheets

        if not df_vendas_registradas.empty:
            col1, col2 = st.columns(2)
            with col1:
                # Usar df_vendas_registradas['Data da Compra'].min() ou uma data padrão segura
                min_date_val = df_vendas_registradas['Data da Compra'].min() if not df_vendas_registradas['Data da Compra'].empty and pd.notna(df_vendas_registradas['Data da Compra'].min()) else datetime.today()
                data_ini = st.date_input("Data inicial do lançamento", value=min_date_val, key='data_ini_consulta')
                
                all_recorded_areas = list(df_vendas_registradas['Área'].unique())
                area_filtro = st.multiselect("Área", all_recorded_areas, key='area_filtro_consulta')
            with col2:
                # Usar df_vendas_registradas['Data da Compra'].max() ou uma data padrão segura
                max_date_val = df_vendas_registradas['Data da Compra'].max() if not df_vendas_registradas['Data da Compra'].empty and pd.notna(df_vendas_registradas['Data da Compra'].max()) else datetime.today()
                data_fim = st.date_input("Data final do lançamento", value=max_date_val, key='data_fim_consulta')
                
                congregacao_filtro = st.multiselect("Congregação", df_vendas_registradas['Congregação'].unique(), key='congregacao_filtro_consulta')

            # Certifica-se de que as colunas de data são datetime para comparação
            # errors='coerce' transformará datas inválidas em NaT (Not a Time)
            df_vendas_registradas['Data da Compra'] = pd.to_datetime(df_vendas_registradas['Data da Compra'], dayfirst=True, errors='coerce')
            df_vendas_registradas['Data do Pagamento'] = pd.to_datetime(df_vendas_registradas['Data do Pagamento'], dayfirst=True, errors='coerce')


            # Aplica os filtros com base nas datas e seleções
            filtro = (df_vendas_registradas['Data da Compra'] >= pd.to_datetime(data_ini)) & \
                     (df_vendas_registradas['Data da Compra'] <= pd.to_datetime(data_fim))
            if area_filtro:
                filtro &= df_vendas_registradas['Área'].isin(area_filtro)
            if congregacao_filtro:
                filtro &= df_vendas_registradas['Congregação'].isin(congregacao_filtro)

            df_filtrado = df_vendas_registradas[filtro].copy()
            
            # Formata as colunas de data de volta para DD/MM/YYYY para exibição no dataframe do Streamlit
            df_filtrado['Data da Compra'] = df_filtrado['Data da Compra'].dt.strftime("%d/%m/%Y")
            # Lida com valores NaT (Not a Time) para Data do Pagamento (se o status for "Pendente")
            df_filtrado['Data do Pagamento'] = df_filtrado['Data do Pagamento'].apply(
                lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else ""
            )

            st.dataframe(df_filtrado)

            # Resumo por mês e ano
            # Garante que as colunas 'Ano' e 'Mês' são criadas a partir das datas válidas
            df_vendas_registradas['Ano'] = df_vendas_registradas['Data da Compra'].dt.year.fillna(0).astype(int)
            df_vendas_registradas['Mês'] = df_vendas_registradas['Data da Compra'].dt.month.fillna(0).astype(int)

            resumo = df_vendas_registradas.groupby(['Ano', 'Mês'])['Total'].sum().reset_index()
            # Filtra anos e meses que não são 0 (ou seja, onde a data da compra era válida e não NaT)
            resumo = resumo[(resumo['Ano'] != 0) & (resumo['Mês'] != 0)]
            st.subheader("Resumo por mês e ano")
            st.dataframe(resumo)
            st.success(f"Total filtrado: R$ {df_filtrado['Total'].astype(float).sum():.2f}")
        else:
            st.warning("Nenhum lançamento registrado ainda.")

    elif aba == "Imprimir Recibo":
        st.title("Impressão de Recibo")
        df_vendas_registradas = carregar_lancamentos_google_sheets() # Carrega do Google Sheets

        if not df_vendas_registradas.empty:
            # Garante que o valor máximo do number_input seja válido
            max_venda_id = len(df_vendas_registradas) - 1
            if max_venda_id < 0: # Caso não haja lançamentos, ajusta para 0 para evitar erro
                max_venda_id = 0
            
            venda_id = st.number_input("Número do lançamento (linha no arquivo)", min_value=0, max_value=max_venda_id, step=1, key='venda_id_recibo')
            
            # Garante que o índice selecionado é válido antes de tentar acessar o DataFrame
            if len(df_vendas_registradas) > venda_id >= 0: 
                dados = df_vendas_registradas.iloc[venda_id].to_dict()
                gerar_recibo_txt(dados)
                st.write("Recibo gerado:")
                with open("recibo.txt", "r", encoding="utf-8") as f:
                    st.text(f.read())
                with open("recibo.txt", "r", encoding="utf-8") as f:
                    st.download_button("📄 Baixar Recibo", f, file_name="recibo.txt")
            else:
                st.warning("Índice de lançamento inválido. Por favor, selecione um número de lançamento existente.")
        else:
            st.warning("Nenhum lançamento registrado ainda para imprimir recibo.")
