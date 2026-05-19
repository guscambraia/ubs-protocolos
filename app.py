import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import uuid

# ------------------------------------------------
# 1. CONFIGURAÇÃO DA INTERFACE E CONEXÃO
# ------------------------------------------------
st.title("Gerenciador de Protocolos - UBS")

# Cria a conexão com o Google Sheets usando a biblioteca oficial
conn = st.connection("gsheets", type=GSheetsConnection)

# Lê os dados da aba chamada "Dados" (ttl=0 garante que os dados estejam sempre atualizados)
df = conn.read(worksheet="Dados", ttl=0)
df = df.dropna(how="all") # Limpa eventuais linhas vazias da planilha

# ------------------------------------------------
# 2. SEÇÃO DE CADASTRO
# ------------------------------------------------
st.header("📋 Novo Protocolo")
with st.form("form_novo_protocolo"):
    col1, col2 = st.columns(2)
    
    numero = col1.text_input("Número do Protocolo/SISREG")
    paciente = col2.text_input("Primeiro Nome do Paciente")
    servico = st.text_input("Tipo de Serviço (Ex: Tomografia, Alto Custo)")
    
    submit = st.form_submit_button("Salvar")
    
    if submit and numero and paciente and servico:
        data_atual = datetime.now().strftime("%Y-%m-%d")
        # Gera um ID único e curto para cada paciente para não misturar os registros
        novo_id = str(uuid.uuid4())[:8] 
        
        # Cria a nova linha que será enviada para a planilha
        nova_linha = pd.DataFrame([{
            "ID": novo_id,
            "Protocolo": numero,
            "Servico": servico,
            "Paciente": paciente,
            "Data": data_atual,
            "Status": "Pendente"
        }])
        
        # Junta os dados antigos com o novo e atualiza a planilha no Google Drive
        df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
        conn.update(worksheet="Dados", data=df_atualizado)
        
        st.success(f"Protocolo do(a) {paciente} salvo com sucesso!")
        st.rerun()

st.divider()

# ------------------------------------------------
# 3. VERIFICAÇÕES DO DIA (DASHBOARD)
# ------------------------------------------------
st.header("🔔 Verificações do Dia")

# Calcula a data de 15 dias atrás
data_limite_dt = datetime.now() - timedelta(days=15)

if df.empty:
    st.info("Nenhum protocolo cadastrado ainda. Comece preenchendo o formulário acima!")
else:
    # Converte a coluna de datas da planilha para um formato que o Python consegue calcular
    df['Data_Convertida'] = pd.to_datetime(df['Data'])
    
    # Filtra: Pendentes com 15 dias ou mais OU qualquer um que foi Adiado
    filtro_pendentes = (df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_limite_dt)
    filtro_adiados = (df['Status'] == 'Adiado')
    
    df_lembretes = df[filtro_pendentes | filtro_adiados]

    if df_lembretes.empty:
        st.info("🎉 Nenhuma pendência para hoje! Tudo sob controle.")
    else:
        for index, row in df_lembretes.iterrows():
            # Formata a data para o padrão BR na hora de exibir
            data_br = row['Data_Convertida'].strftime("%d/%m/%Y")
            
            with st.expander(f"⚠️ {row['Paciente']} | Protocolo: {row['Protocolo']}"):
                st.write(f"**Serviço:** {row['Servico']}")
                st.write(f"**Solicitado em:** {data_br}")
                st.write(f"**Status Atual:** {row['Status']}")
                
                c1, c2 = st.columns(2)
                
                if c1.button("✅ Marcar como Concluído", key=f"ok_{row['ID']}"):
                    df.at[index, 'Status'] = 'Concluido'
                    # Removemos a coluna auxiliar de data antes de mandar de volta pra planilha
                    df_salvar = df.drop(columns=['Data_Convertida'])
                    conn.update(worksheet="Dados", data=df_salvar)
                    st.rerun()
                    
                if c2.button("⏳ Adiar (Verificar amanhã)", key=f"adiar_{row['ID']}"):
                    df.at[index, 'Status'] = 'Adiado'
                    df_salvar = df.drop(columns=['Data_Convertida'])
                    conn.update(worksheet="Dados", data=df_salvar)
                    st.rerun()