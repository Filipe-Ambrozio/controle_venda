import streamlit as st
import pandas as pd
from datetime import datetime
import os
import gspread

# Configuração da página
st.set_page_config(page_title="Sistema de Vendas", layout="wide")

# --- Configurações do Google Sheets ---
# ID da sua planilha Google Sheets (extraído do URL que você forneceu)
GSHEET_ID = "1u5zQ5H61_clP-9Cihw_JhfQQ4M2DrESp"
# Nome da aba (worksheet) onde os dados de vendas/despesas serão registrados
GSHEET_WORKSHEET_NAME = "vendas_registradas"

# Funções auxiliares
def autenticar(usuario, senha):
    """
    Função para autenticar usuários no aplicativo.
    Retorna True se as credenciais forem válidas, False caso contrário.
    """
    credenciais = {
        "junior": "123456",
        "filipe": "7777"
    }
    return credenciais.get(usuario) == senha

def get_gsheets_client():
    """
    Obtém um cliente gspread autenticado usando as credenciais do Streamlit Secrets.
    """
    try:
        # st.secrets["gcp_service_account"] deve conter o conteúdo do JSON da conta de serviço
        return gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    except Exception as e:
        st.error(f"Erro ao autenticar com o Google Sheets. Verifique suas credenciais em .streamlit/secrets.toml e as permissões da conta de serviço. Detalhes: {e}")
        st.stop() # Interrompe a execução do app se a autenticação falhar

def carregar_dados_excel_lookup():
    """
    Carrega os dados de lookup (itens de venda, nomes de pessoas, e áreas/congregações)
    do arquivo 'vendas.xlsx' local. Este arquivo é usado para preencher os selectboxes da UI.
    """
    try:
        df_venda = pd.read_excel("vendas.xlsx", sheet_name="venda")
        df_nomes = pd.read_excel("vendas.xlsx", sheet_name="nomes")
        df_area = pd.read_excel("vendas.xlsx", sheet_name="area")
        return df_venda, df_nomes, df_area
    except FileNotFoundError:
        st.error("Erro: O arquivo 'vendas.xlsx' (com as abas 'venda', 'nomes', 'area') não foi encontrado no diretório do script.")
        st.stop() # Parar a execução se o arquivo essencial não for encontrado
    except Exception as e:
        st.error(f"Erro ao carregar dados de lookup do 'vendas.xlsx': {e}")
        st.stop() # Parar a execução em caso de outros erros de leitura

def salvar_lancamento_gsheets(dados):
    """
    Salva os dados de um novo lançamento (venda ou despesa) na planilha do Google Sheets.
    Cria a aba e os cabeçalhos se não existirem.
    """
    client = get_gsheets_client()
    try:
        spreadsheet = client.open_by_key(GSHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Erro: Planilha Google Sheets com ID '{GSHEET_ID}' não encontrada ou sem permissão de acesso.")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao abrir a planilha Google Sheets: {e}")
        st.stop()

    try:
        worksheet = spreadsheet.worksheet(GSHEET_WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # Se a aba não existir, cria uma nova com os cabeçalhos
        st.warning(f"Aba '{GSHEET_WORKSHEET_NAME}' não encontrada. Criando uma nova aba na planilha...")
        worksheet = spreadsheet.add_worksheet(title=GSHEET_WORKSHEET_NAME, rows="1", cols="1")
        
        # Define os cabeçalhos que serão usados no Google Sheet
        headers = [
            "Data da Compra", "Área", "Congregação", "Nome", "Cargo",
            "Produto", "Tipo", "Valor Unitário", "Quantidade", "Total",
            "Status", "Data do Pagamento", "Vendedor"
        ]
        worksheet.append_row(headers) # Adiciona os cabeçalhos na primeira linha
        st.success(f"Aba '{GSHEET_WORKSHEET_NAME}' criada com sucesso e cabeçalhos adicionados.")
        
    except Exception as e:
        st.error(f"Erro ao acessar ou criar a aba '{GSHEET_WORKSHEET_NAME}': {e}")
        st.stop()

    try:
        # Converte o dicionário de dados em uma lista de valores na ordem dos cabeçalhos
        # É CRUCIAL que a ordem aqui corresponda à ordem dos cabeçalhos na sua planilha!
        row_values = [
            dados.get("Data da Compra", ""),
            dados.get("Área", ""),
            dados.get("Congregação", ""),
            dados.get("Nome", ""),
            dados.get("Cargo", ""),
            dados.get("Produto", ""),
            dados.get("Tipo", ""),
            dados.get("Valor Unitário", 0.0),
            dados.get("Quantidade", 0),
            dados.get("Total", 0.0),
            dados.get("Status", ""),
            dados.get("Data do Pagamento", ""),
            dados.get("Vendedor", "")
        ]
        worksheet.append_row(row_values)
    except Exception as e:
        st.error(f"Erro ao adicionar os dados à planilha Google Sheets: {e}")

def carregar_lancamentos_gsheets():
    """
    Carrega todos os lançamentos da planilha do Google Sheets para um DataFrame do Pandas.
    """
    client = get_gsheets_client()
    try:
        spreadsheet = client.open_by_key(GSHEET_ID)
        worksheet = spreadsheet.worksheet(GSHEET_WORKSHEET_NAME)
        # Pega todos os registros como uma lista de dicionários (onde as chaves são os cabeçalhos)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"Aba '{GSHEET_WORKSHEET_NAME}' não encontrada na planilha. Retornando DataFrame vazio.")
        return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Planilha Google Sheets com ID '{GSHEET_ID}' não encontrada ou sem permissão de acesso.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar lançamentos do Google Sheets: {e}")
        return pd.DataFrame()

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
    df_venda_lookup, df_nomes_lookup, df_area_lookup = carregar_dados_excel_lookup()

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
                salvar_lancamento_gsheets(dados_lancamento) # Salva no Google Sheets
                gerar_recibo_txt(dados_lancamento)
                st.success("Lançamento registrado e recibo gerado.")
                st.session_state.reset_form = True # Sinaliza para resetar os campos no próximo rerun
                st.rerun() # Reinicia a página para efetivar a limpeza dos campos

    elif aba == "Consultar Lançamentos":
        st.title("Consulta de Lançamentos") # Título atualizado para refletir vendas e despesas
        df_lancamentos = carregar_lancamentos_gsheets() # Carrega do Google Sheets

        if not df_lancamentos.empty:
            col1, col2 = st.columns(2)
            with col1:
                data_ini = st.date_input("Data inicial do lançamento", value=datetime.today(), key='data_ini_consulta')
                all_recorded_areas = list(df_lancamentos['Área'].unique())
                area_filtro = st.multiselect("Área", all_recorded_areas, key='area_filtro_consulta')
            with col2:
                data_fim = st.date_input("Data final do lançamento", value=datetime.today(), key='data_fim_consulta')
                congregacao_filtro = st.multiselect("Congregação", df_lancamentos['Congregação'].unique(), key='congregacao_filtro_consulta')

            # Converte as colunas de data para o tipo datetime, assumindo formato DD/MM/YYYY
            # 'dayfirst=True' é crucial para interpretar "DD/MM/YYYY" corretamente
            df_lancamentos['Data da Compra'] = pd.to_datetime(df_lancamentos['Data da Compra'], dayfirst=True, errors='coerce')
            df_lancamentos['Data do Pagamento'] = pd.to_datetime(df_lancamentos['Data do Pagamento'], dayfirst=True, errors='coerce')

            # Aplica os filtros com base nas datas e seleções
            filtro = (df_lancamentos['Data da Compra'] >= pd.to_datetime(data_ini)) & \
                     (df_lancamentos['Data da Compra'] <= pd.to_datetime(data_fim))
            if area_filtro:
                filtro &= df_lancamentos['Área'].isin(area_filtro)
            if congregacao_filtro:
                filtro &= df_lancamentos['Congregação'].isin(congregacao_filtro)

            df_filtrado = df_lancamentos[filtro].copy()
            
            # Formata as colunas de data de volta para DD/MM/YYYY para exibição no dataframe do Streamlit
            df_filtrado['Data da Compra'] = df_filtrado['Data da Compra'].dt.strftime("%d/%m/%Y")
            # Lida com valores NaT (Not a Time) para Data do Pagamento (se o status for "Pendente")
            df_filtrado['Data do Pagamento'] = df_filtrado['Data do Pagamento'].apply(
                lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else ""
            )

            st.dataframe(df_filtrado)

            # Resumo por mês e ano
            # Garante que as colunas 'Ano' e 'Mês' são criadas a partir das datas válidas
            df_lancamentos['Ano'] = df_lancamentos['Data da Compra'].dt.year.fillna(0).astype(int)
            df_lancamentos['Mês'] = df_lancamentos['Data da Compra'].dt.month.fillna(0).astype(int)

            resumo = df_lancamentos.groupby(['Ano', 'Mês'])['Total'].sum().reset_index()
            # Filtra anos e meses que não são 0 (ou seja, onde a data da compra era válida e não NaT)
            resumo = resumo[(resumo['Ano'] != 0) & (resumo['Mês'] != 0)] 
            st.subheader("Resumo por mês e ano")
            st.dataframe(resumo)
            st.success(f"Total filtrado: R$ {df_filtrado['Total'].astype(float).sum():.2f}")
        else:
            st.warning("Nenhum lançamento registrado ainda.")

    elif aba == "Imprimir Recibo":
        st.title("Impressão de Recibo")
        df_lancamentos = carregar_lancamentos_gsheets() # Carrega do Google Sheets

        if not df_lancamentos.empty:
            # Garante que o valor máximo do number_input seja válido
            max_lancamento_id = len(df_lancamentos) - 1
            if max_lancamento_id < 0: # Caso não haja lançamentos, ajusta para 0 para evitar erro
                max_lancamento_id = 0
            
            lancamento_id = st.number_input("Número do lançamento (linha no arquivo)", min_value=0, max_value=max_lancamento_id, step=1, key='lancamento_id_recibo')
            
            # Garante que o índice selecionado é válido antes de tentar acessar o DataFrame
            if len(df_lancamentos) > lancamento_id >= 0: 
                dados = df_lancamentos.iloc[lancamento_id].to_dict()
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
