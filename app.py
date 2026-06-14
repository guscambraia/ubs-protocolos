import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import uuid
import io

# Configuração da página (deve ser sempre o primeiro comando)
st.set_page_config(page_title="Regulação UBS", layout="wide", page_icon="🏥")

# ------------------------------------------------
# FUNÇÃO DO SISTEMA DE LOGIN
# ------------------------------------------------
def check_password():
    def password_entered():
        if st.session_state["senha_digitada"] == st.secrets["senha_app"]:
            st.session_state["senha_correta"] = True
            del st.session_state["senha_digitada"]
        else:
            st.session_state["senha_correta"] = False

    if "senha_correta" not in st.session_state:
        st.markdown("### 🔒 Acesso Restrito - UBS")
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="senha_digitada")
        return False
    elif not st.session_state["senha_correta"]:
        st.markdown("### 🔒 Acesso Restrito - UBS")
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="senha_digitada")
        st.error("❌ Senha incorreta. Tente novamente.")
        return False
    else:
        return True

# ------------------------------------------------
# APLICAÇÃO PRINCIPAL
# ------------------------------------------------
if check_password():
    
    # Barra lateral
    st.sidebar.title("🏥 Menu UBS")
    if st.sidebar.button("🔒 Sair (Logout)", use_container_width=True):
        st.session_state["senha_correta"] = False
        st.rerun()

    st.title("Gerenciador de Protocolos e Regulação")

    # Conexão com Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Dados", ttl=0).dropna(how="all")

    # Garantir colunas necessárias e corrigir formatação de números
    if not df.empty:
        colunas_necessarias = ['Interno', 'Observacoes', 'Data_Retorno', 'Prioridade_Regulacao']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = ""
        
        # Corrige o problema do ".0" nos protocolos lidos como float
        df['Protocolo'] = df['Protocolo'].astype(str).apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)
        df['Data_Convertida'] = pd.to_datetime(df['Data'], errors='coerce')

    # Navegação por Abas (Melhora muito a Interface)
    aba_dashboard, aba_cadastro, aba_busca = st.tabs(["🔔 Dashboard & Lembretes", "📋 Novo Protocolo", "🔍 Busca & Relatórios"])

    # ==========================================
    # ABA 1: DASHBOARD E LEMBRETES
    # ==========================================
    with aba_dashboard:
        if not df.empty:
            data_hoje = datetime.now()
            data_15_dias_atras = data_hoje - timedelta(days=15)
            
            # Cálculo das Métricas
            total_cadastrados = len(df)
            total_concluidos = len(df[df['Status'] == 'Concluido'])
            total_adiados = len(df[df['Status'] == 'Adiado'])
            
            # Filtros de visualização
            filtro_15_dias = (df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_15_dias_atras)
            
            # Verifica se o prazo do adiamento já venceu para voltar ao painel
            df['Data_Retorno_DT'] = pd.to_datetime(df['Data_Retorno'], errors='coerce')
            filtro_retornou = (df['Status'] == 'Adiado') & (df['Data_Retorno_DT'] <= data_hoje)
            
            total_pendentes = len(df[filtro_15_dias | filtro_retornou])

            # Exibição de Métricas (Nova versão)
            st.markdown("### 📊 Visão Geral de Eficiência")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric(label="📋 Total Cadastrados", value=total_cadastrados)
            col_m2.metric(label="✅ Concluídos/Aprovados", value=total_concluidos)
            col_m3.metric(label="⚠️ Em Pendência (>15d)", value=total_pendentes)
            col_m4.metric(label="⏳ Aguardando Regulação (Adiados)", value=total_adiados)
            st.divider()

            # Área de Lembretes do Dia
            st.markdown("### 🚨 Necessitam de Atenção Hoje")
            df_lembretes = df[filtro_15_dias | filtro_retornou]

            if df_lembretes.empty:
                st.success("🎉 Nenhuma pendência para a data de hoje! Tudo em dia.")
            else:
                for index, row in df_lembretes.iterrows():
                    dias_espera = (data_hoje - row['Data_Convertida']).days
                    alerta_visual = "🔴 [URGENTE]" if dias_espera > 30 else "🟡"
                    
                    data_br = row['Data_Convertida'].strftime("%d/%m/%Y") if pd.notna(row['Data_Convertida']) else "N/A"
                    info_interno = f" | Interno: {row['Interno']}" if pd.notna(row['Interno']) and str(row['Interno']).strip() != "" else ""
                    
                    with st.expander(f"{alerta_visual} {row['Paciente']} | Espera: {dias_espera} dias{info_interno}"):
                        c_info, c_acoes = st.columns([1.5, 2])
                        
                        with c_info:
                            st.write("**Nº Protocolo:**")
                            # st.code exibe o número e cria um botão de copiar automaticamente!
                            st.code(row['Protocolo'], language=None) 
                            st.write(f"**Serviço:** {row['Servico']}")
                            st.write(f"**Solicitado:** {data_br}")
                            
                        with c_acoes:
                            # 1. Campo de Observação (Salva na mesma hora)
                            obs_atual = row['Observacoes'] if pd.notna(row['Observacoes']) else ""
                            nova_obs = st.text_area("Observações (Ex: Ligado pra regulação):", value=obs_atual, key=f"obs_{row['ID']}", height=68)
                            if st.button("💾 Salvar Obs", key=f"btn_obs_{row['ID']}"):
                                df.at[index, 'Observacoes'] = nova_obs
                                df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                conn.update(worksheet="Dados", data=df_salvar)
                                st.rerun()

                            st.divider()

                            # 2. Área de Ações: Concluir ou Adiar
                            col_acao1, col_acao2 = st.columns(2)
                            
                            with col_acao1:
                                st.markdown("**Dar Baixa**")
                                prioridade = st.selectbox("Prioridade (Opcional):", ["", "A", "B", "C", "D"], key=f"prio_{row['ID']}")
                                if st.button("✅ Concluir", key=f"ok_{row['ID']}", use_container_width=True):
                                    df.at[index, 'Status'] = 'Concluido'
                                    df.at[index, 'Prioridade_Regulacao'] = prioridade
                                    df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                    conn.update(worksheet="Dados", data=df_salvar)
                                    st.rerun()
                                    
                            with col_acao2:
                                st.markdown("**Pausar Alerta**")
                                dias_adiar = st.number_input("Adiar por quantos dias?", min_value=1, value=7, step=1, key=f"dias_{row['ID']}")
                                if st.button("⏳ Adiar", key=f"adiar_{row['ID']}", use_container_width=True):
                                    nova_data_retorno = (data_hoje + timedelta(days=dias_adiar)).strftime("%Y-%m-%d")
                                    df.at[index, 'Status'] = 'Adiado'
                                    df.at[index, 'Data_Retorno'] = nova_data_retorno
                                    df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                    conn.update(worksheet="Dados", data=df_salvar)
                                    st.rerun()

    # ==========================================
    # ABA 2: NOVO PROTOCOLO
    # ==========================================
    with aba_cadastro:
        st.header("📋 Cadastrar Novo Protocolo")
        with st.form("form_novo_protocolo", clear_on_submit=True):
            col1, col2 = st.columns(2)
            numero = col1.text_input("Número do Protocolo/SISREG *")
            paciente = col2.text_input("Primeiro Nome do Paciente *")
            
            col3, col4 = st.columns(2)
            servico = col3.text_input("Tipo de Serviço (Ex: Tomografia) *")
            interno = col4.text_input("Interno Responsável (Opcional)")
            
            submit = st.form_submit_button("Salvar Registro", use_container_width=True)
            
            if submit and numero and paciente and servico:
                numero_limpo = str(numero).strip()
                protocolo_existe = False
                
                if not df.empty:
                    protocolo_existe = numero_limpo in df['Protocolo'].astype(str).values
                    
                if protocolo_existe:
                    st.error(f"❌ O protocolo {numero_limpo} já foi cadastrado anteriormente!")
                else:
                    data_atual = datetime.now().strftime("%Y-%m-%d")
                    novo_id = str(uuid.uuid4())[:8] 
                    
                    nova_linha = pd.DataFrame([{
                        "ID": novo_id, "Protocolo": numero_limpo, "Servico": servico.upper(),
                        "Paciente": paciente.upper(), "Data": data_atual, "Status": "Pendente",
                        "Interno": interno, "Observacoes": "", "Data_Retorno": "", "Prioridade_Regulacao": ""
                    }])
                    
                    df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
                    df_atualizado = df_atualizado.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                        
                    conn.update(worksheet="Dados", data=df_atualizado)
                    st.success("✅ Protocolo salvo com sucesso!")
                    st.rerun()

    # ==========================================
    # ABA 3: BUSCA E RELATÓRIOS
    # ==========================================
    with aba_busca:
        st.header("🔍 Buscar e Exportar Dados")
        
        if not df.empty:
            c_busca1, c_busca2, c_busca3 = st.columns(3)
            
            texto_busca = c_busca1.text_input("Buscar Nome, Protocolo ou Interno:")
            
            lista_servicos = ["Todos"] + sorted(df['Servico'].dropna().unique().tolist())
            servico_busca = c_busca2.selectbox("Filtrar por Serviço:", lista_servicos)
            
            # Criar lista de meses/anos disponíveis baseados na coluna de Data
            df['Mes_Ano'] = df['Data_Convertida'].dt.strftime('%m/%Y').fillna('Sem Data')
            lista_meses = ["Todos"] + sorted(df[df['Mes_Ano'] != 'Sem Data']['Mes_Ano'].unique().tolist(), reverse=True)
            mes_busca = c_busca3.selectbox("Filtrar por Mês/Ano:", lista_meses)

            # Aplicar filtros
            df_busca = df.copy()
            
            if texto_busca:
                df_busca = df_busca[
                    df_busca['Paciente'].str.contains(texto_busca, case=False, na=False) | 
                    df_busca['Protocolo'].astype(str).str.contains(texto_busca, case=False, na=False) |
                    df_busca['Interno'].astype(str).str.contains(texto_busca, case=False, na=False)
                ]
            
            if servico_busca != "Todos":
                df_busca = df_busca[df_busca['Servico'] == servico_busca]
                
            if mes_busca != "Todos":
                df_busca = df_busca[df_busca['Mes_Ano'] == mes_busca]

            st.write(f"**Registros encontrados:** {len(df_busca)}")
            
            if df_busca.empty:
                st.warning("Nenhum registro encontrado com estes filtros.")
            else:
                # Mostrar tabela na tela (limpando colunas de sistema)
                colunas_exibicao = ['Protocolo', 'Paciente', 'Servico', 'Data', 'Status', 'Interno', 'Prioridade_Regulacao', 'Observacoes']
                st.dataframe(df_busca[colunas_exibicao], use_container_width=True)

                # Gerar arquivo Excel em memória para download
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_busca[colunas_exibicao].to_excel(writer, index=False, sheet_name='Relatorio_UBS')
                
                st.download_button(
                    label="📥 Exportar Resultados para Excel",
                    data=buffer.getvalue(),
                    file_name=f"Relatorio_UBS_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
