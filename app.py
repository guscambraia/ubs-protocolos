import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import uuid

# Configuração da página (deve ser sempre o primeiro comando do Streamlit)
st.set_page_config(page_title="Regulação UBS", layout="wide")

# ------------------------------------------------
# FUNÇÃO DO SISTEMA DE LOGIN
# ------------------------------------------------
def check_password():
    """Retorna True se o usuário digitar a senha correta."""
    def password_entered():
        # Verifica se a senha digitada bate com a chave criada nos Secrets
        if st.session_state["senha_digitada"] == st.secrets["senha_app"]:
            st.session_state["senha_correta"] = True
            del st.session_state["senha_digitada"]  # Limpa a senha da memória por segurança
        else:
            st.session_state["senha_correta"] = False

    if "senha_correta" not in st.session_state:
        # Tela inicial de login
        st.markdown("### 🔒 Acesso Restrito - UBS")
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="senha_digitada")
        return False
        
    elif not st.session_state["senha_correta"]:
        # Se errar a senha, mostra mensagem de erro
        st.markdown("### 🔒 Acesso Restrito - UBS")
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="senha_digitada")
        st.error("❌ Senha incorreta. Tente novamente.")
        return False
        
    else:
        # Senha correta, libera a aplicação
        return True

# ------------------------------------------------
# APLICAÇÃO PRINCIPAL (SÓ RODA SE LOGADO)
# ------------------------------------------------
if check_password():
    # Toda a sua aplicação agora fica dentro deste bloco "if"
    # e todas as linhas abaixo foram recuadas (4 espaços para a direita)
    
    # Botão opcional na barra lateral para encerrar a sessão
    if st.sidebar.button("🔒 Sair (Logout)"):
        st.session_state["senha_correta"] = False
        st.rerun()

    st.title("Gerenciador de Protocolos - UBS")

    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Dados", ttl=0).dropna(how="all")

    # Garantir que as novas colunas existem no DataFrame (caso a planilha ainda esteja vazia)
    if not df.empty:
        if 'Interno' not in df.columns:
            df['Interno'] = ""
        if 'Observacoes' not in df.columns:
            df['Observacoes'] = ""

    if not df.empty:
        df['Data_Convertida'] = pd.to_datetime(df['Data'])
        data_limite_dt = datetime.now() - timedelta(days=15)
        
        total_pendentes = len(df[(df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_limite_dt)])
        total_adiados = len(df[df['Status'] == 'Adiado'])
        total_concluidos = len(df[df['Status'] == 'Concluido'])
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric(label="⚠️ Venceram hoje (15 dias)", value=total_pendentes)
        col_m2.metric(label="⏳ Adiados", value=total_adiados)
        col_m3.metric(label="✅ Concluídos (Total)", value=total_concluidos)
        st.divider()

    st.header("🔍 Buscar Histórico")
    busca = st.text_input("Digite o nome do paciente, protocolo ou interno:")

    if busca and not df.empty:
        df_busca = df[
            df['Paciente'].str.contains(busca, case=False, na=False) | 
            df['Protocolo'].astype(str).str.contains(busca, case=False, na=False) |
            df['Interno'].astype(str).str.contains(busca, case=False, na=False)
        ]
        
        if df_busca.empty:
            st.warning("Nenhum registro encontrado.")
        else:
            st.dataframe(df_busca[['Protocolo', 'Paciente', 'Servico', 'Interno', 'Data', 'Status']], use_container_width=True)

    st.divider()

    # ------------------------------------------------
    # CADASTRO (AGORA COM CAMPO DO INTERNO)
    # ------------------------------------------------
    st.header("📋 Novo Protocolo")
    with st.form("form_novo_protocolo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        numero = col1.text_input("Número do Protocolo/SISREG *")
        paciente = col2.text_input("Primeiro Nome do Paciente *")
        
        col3, col4 = st.columns(2)
        servico = col3.text_input("Tipo de Serviço (Ex: Tomografia) *")
        interno = col4.text_input("Interno Responsável (Opcional)")
        
        submit = st.form_submit_button("Salvar")
        
        if submit and numero and paciente and servico:
            protocolo_existe = False
            if not df.empty:
                protocolo_existe = numero in df['Protocolo'].astype(str).values
                
            if protocolo_existe:
                st.error(f"❌ O protocolo {numero} já foi cadastrado anteriormente!")
            else:
                data_atual = datetime.now().strftime("%Y-%m-%d")
                novo_id = str(uuid.uuid4())[:8] 
                
                nova_linha = pd.DataFrame([{
                    "ID": novo_id, "Protocolo": numero, "Servico": servico,
                    "Paciente": paciente, "Data": data_atual, "Status": "Pendente",
                    "Interno": interno, "Observacoes": "" 
                }])
                
                df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
                if 'Data_Convertida' in df_atualizado.columns:
                    df_atualizado = df_atualizado.drop(columns=['Data_Convertida'])
                    
                conn.update(worksheet="Dados", data=df_atualizado)
                st.success(f"Protocolo salvo com sucesso!")
                st.rerun()

    st.divider()

    # ------------------------------------------------
    # VERIFICAÇÕES DO DIA (AGORA COM OBSERVAÇÕES)
    # ------------------------------------------------
    st.header("🔔 Verificações do Dia")

    if df.empty:
        st.info("Nenhum protocolo cadastrado ainda.")
    else:
        filtro_pendentes = (df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_limite_dt)
        filtro_adiados = (df['Status'] == 'Adiado')
        
        df_lembretes = df[filtro_pendentes | filtro_adiados]

        if df_lembretes.empty:
            st.info("🎉 Nenhuma pendência para hoje!")
        else:
            for index, row in df_lembretes.iterrows():
                dias_espera = (datetime.now() - row['Data_Convertida']).days
                alerta_visual = "🟡" 
                if dias_espera > 30:
                    alerta_visual = "🔴 [URGENTE]"
                
                data_br = row['Data_Convertida'].strftime("%d/%m/%Y")
                info_interno = f" | Interno: {row['Interno']}" if pd.notna(row['Interno']) and str(row['Interno']).strip() != "" else ""
                
                with st.expander(f"{alerta_visual} {row['Paciente']} | Aguardando há {dias_espera} dias{info_interno}"):
                    
                    col_info, col_obs = st.columns([1, 1])
                    
                    with col_info:
                        st.write(f"**Protocolo:** {row['Protocolo']}")
                        st.write(f"**Serviço:** {row['Servico']}")
                        st.write(f"**Solicitado em:** {data_br}")
                        st.write(f"**Status Atual:** {row['Status']}")
                    
                    with col_obs:
                        obs_atual = row['Observacoes'] if pd.notna(row['Observacoes']) else ""
                        nova_obs = st.text_area("Motivo da Pendência / Observações:", value=obs_atual, key=f"obs_{row['ID']}")
                        
                        if st.button("💾 Salvar Nota", key=f"btn_obs_{row['ID']}"):
                            df.at[index, 'Observacoes'] = nova_obs
                            df_salvar = df.drop(columns=['Data_Convertida'])
                            conn.update(worksheet="Dados", data=df_salvar)
                            st.success("Nota salva!")
                            st.rerun()

                    st.divider()
                    
                    c1, c2 = st.columns(2)
                    
                    if c1.button("✅ Concluir", key=f"ok_{row['ID']}"):
                        df.at[index, 'Status'] = 'Concluido'
                        df_salvar = df.drop(columns=['Data_Convertida'])
                        conn.update(worksheet="Dados", data=df_salvar)
                        st.rerun()
                        
                    if c2.button("⏳ Adiar", key=f"adiar_{row['ID']}"):
                        df.at[index, 'Status'] = 'Adiado'
                        df_salvar = df.drop(columns=['Data_Convertida'])
                        conn.update(worksheet="Dados", data=df_salvar)
                        st.rerun()
                        
