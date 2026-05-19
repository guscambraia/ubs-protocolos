import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import uuid

# Configura a página para ocupar mais espaço na tela
st.set_page_config(page_title="Regulação UBS", layout="wide")

# ------------------------------------------------
# 1. CONFIGURAÇÃO E CONEXÃO
# ------------------------------------------------
st.title("Gerenciador de Protocolos - UBS")

conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Dados", ttl=0).dropna(how="all")

# ------------------------------------------------
# MELHORIA 2: MÉTRICAS RÁPIDAS (DASHBOARD)
# ------------------------------------------------
if not df.empty:
    df['Data_Convertida'] = pd.to_datetime(df['Data'])
    data_limite_dt = datetime.now() - timedelta(days=15)
    
    # Cálculos para os Cards
    total_pendentes = len(df[(df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_limite_dt)])
    total_adiados = len(df[df['Status'] == 'Adiado'])
    total_concluidos = len(df[df['Status'] == 'Concluido'])
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(label="⚠️ Venceram hoje (15 dias)", value=total_pendentes)
    col_m2.metric(label="⏳ Adiados", value=total_adiados)
    col_m3.metric(label="✅ Concluídos (Total)", value=total_concluidos)
    st.divider()

# ------------------------------------------------
# MELHORIA 1: BUSCA DE PACIENTES
# ------------------------------------------------
st.header("🔍 Buscar Histórico")
busca = st.text_input("Digite o nome do paciente ou o número do protocolo:")

if busca and not df.empty:
    # Filtra ignorando maiúsculas/minúsculas
    df_busca = df[df['Paciente'].str.contains(busca, case=False, na=False) | 
                  df['Protocolo'].astype(str).str.contains(busca, case=False, na=False)]
    
    if df_busca.empty:
        st.warning("Nenhum registro encontrado para esta busca.")
    else:
        st.dataframe(df_busca[['Protocolo', 'Paciente', 'Servico', 'Data', 'Status']], use_container_width=True)

st.divider()

# ------------------------------------------------
# SEÇÃO DE CADASTRO COM MELHORIA 4 (ANTIDUPLICIDADE)
# ------------------------------------------------
st.header("📋 Novo Protocolo")
with st.form("form_novo_protocolo", clear_on_submit=True):
    col1, col2 = st.columns(2)
    numero = col1.text_input("Número do Protocolo/SISREG")
    paciente = col2.text_input("Primeiro Nome do Paciente")
    servico = st.text_input("Tipo de Serviço (Ex: Tomografia, Alto Custo)")
    submit = st.form_submit_button("Salvar")
    
    if submit and numero and paciente and servico:
        # MELHORIA 4: Validação de Duplicidade
        protocolo_existe = False
        if not df.empty:
            # Verifica se o número já existe na base
            protocolo_existe = numero in df['Protocolo'].astype(str).values
            
        if protocolo_existe:
            st.error(f"❌ O protocolo {numero} já foi cadastrado anteriormente!")
        else:
            data_atual = datetime.now().strftime("%Y-%m-%d")
            novo_id = str(uuid.uuid4())[:8] 
            
            nova_linha = pd.DataFrame([{
                "ID": novo_id, "Protocolo": numero, "Servico": servico,
                "Paciente": paciente, "Data": data_atual, "Status": "Pendente"
            }])
            
            df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
            # Remove a coluna temporária antes de salvar se ela existir
            if 'Data_Convertida' in df_atualizado.columns:
                df_atualizado = df_atualizado.drop(columns=['Data_Convertida'])
                
            conn.update(worksheet="Dados", data=df_atualizado)
            st.success(f"Protocolo salvo com sucesso!")
            st.rerun()

st.divider()

# ------------------------------------------------
# VERIFICAÇÕES DO DIA COM MELHORIA 5 (ALERTA DE TEMPO)
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
            # MELHORIA 5: Cores de Alerta baseadas no tempo
            dias_espera = (datetime.now() - row['Data_Convertida']).days
            
            alerta_visual = "🟡" # Padrão para 15 a 30 dias
            if dias_espera > 30:
                alerta_visual = "🔴 [URGENTE]"
            
            data_br = row['Data_Convertida'].strftime("%d/%m/%Y")
            
            with st.expander(f"{alerta_visual} {row['Paciente']} | Aguardando há {dias_espera} dias (Protocolo: {row['Protocolo']})"):
                st.write(f"**Serviço:** {row['Servico']}")
                st.write(f"**Solicitado em:** {data_br}")
                st.write(f"**Status Atual:** {row['Status']}")
                
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
