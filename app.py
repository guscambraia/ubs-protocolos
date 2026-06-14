import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import uuid
import io

# Configuração da página (deve ser sempre o primeiro comando)
st.set_page_config(page_title="Regulação UBS", layout="wide", page_icon="🏥")

# Injeção de CSS customizado para manter o botão de copiar sempre visível
st.markdown("""
    <style>
    /* Força o botão de copiar do st.code a ficar sempre visível e opaco */
    [data-testid="stCodeBlock"] button {
        opacity: 1 !important;
        visibility: visible !important;
        transform: none !important;
    }
    </style>
""", unsafe_allow_html=True)

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

    # Tratamento e higienização inicial dos dados
    if not df.empty:
        colunas_necessarias = ['Interno', 'Observacoes', 'Data_Retorno', 'Prioridade_Regulacao']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = ""
        
        df['Protocolo'] = df['Protocolo'].astype(str).apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)
        df['Data_Convertida'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Data_Retorno_DT'] = pd.to_datetime(df['Data_Retorno'], errors='coerce')

    # Abas Principais
    aba_painel, aba_busca = st.tabs(["🏥 Painel de Controle", "🔍 Busca Avançada & Relatórios"])

    # ==========================================
    # ABA 1: PAINEL DE CONTROLE (DASHBOARD + CADASTRO ABERTO)
    # ==========================================
    with aba_painel:
        data_hoje = datetime.now()
        data_15_dias_atras = data_hoje - timedelta(days=15)

        if not df.empty:
            df_no_prazo = df[(df['Status'] == 'Pendente') & (df['Data_Convertida'] > data_15_dias_atras)]
            df_vencidos = df[(df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_15_dias_atras)]
            df_adiados = df[df['Status'] == 'Adiado']
            df_concluidos = df[df['Status'] == 'Concluido']
            df_total = df.copy()

            cant_no_prazo = len(df_no_prazo)
            cant_vencidos = len(df_vencidos)
            cant_adiados = len(df_adiados)
            cant_concluidos = len(df_concluidos)
            cant_total = len(df_total)
            
            # Cálculos de Porcentagem (Prevenção de divisão por zero)
            pct_no_prazo = (cant_no_prazo / cant_total * 100) if cant_total > 0 else 0
            pct_vencidos = (cant_vencidos / cant_total * 100) if cant_total > 0 else 0
            pct_adiados = (cant_adiados / cant_total * 100) if cant_total > 0 else 0
            pct_concluidos = (cant_concluidos / cant_total * 100) if cant_total > 0 else 0
            
        else:
            df_no_prazo = df_vencidos = df_adiados = df_total = df_concluidos = pd.DataFrame()
            cant_no_prazo = cant_vencidos = cant_adiados = cant_concluidos = cant_total = 0
            pct_no_prazo = pct_vencidos = pct_adiados = pct_concluidos = 0.0

        if 'filtro_dashboard' not in st.session_state:
            st.session_state['filtro_dashboard'] = 'vencidos'

        # Renderização dos cartões clicáveis (Agora com porcentagens)
        st.markdown("### 📊 Indicadores de Regulação (Clique para filtrar a lista abaixo)")
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        
        # Formatação HTML para o número grande e a porcentagem menor logo abaixo
        estilo_numero = "margin-bottom: -5px; margin-top: 5px;"
        estilo_pct = "font-size: 16px; color: #7f8c8d; font-weight: normal; margin-top: 0px;"
        
        with col_m1:
            st.markdown(f"<h3 style='text-align: center; color: #2ecc71; {estilo_numero}'>{cant_no_prazo}</h3><p style='text-align: center; {estilo_pct}'>({pct_no_prazo:.1f}%)</p>", unsafe_allow_html=True)
            if st.button("🟢 No Prazo (<15d)", key="btn_m1", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'no_prazo'
                
        with col_m2:
            st.markdown(f"<h3 style='text-align: center; color: #e74c3c; {estilo_numero}'>{cant_vencidos}</h3><p style='text-align: center; {estilo_pct}'>({pct_vencidos:.1f}%)</p>", unsafe_allow_html=True)
            if st.button("🔴 Vencidos / Verificar", key="btn_m2", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'vencidos'
                
        with col_m3:
            st.markdown(f"<h3 style='text-align: center; color: #f39c12; {estilo_numero}'>{cant_adiados}</h3><p style='text-align: center; {estilo_pct}'>({pct_adiados:.1f}%)</p>", unsafe_allow_html=True)
            if st.button("⏳ Adiados / Pausados", key="btn_m3", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'adiados'
                
        with col_m4:
            st.markdown(f"<h3 style='text-align: center; color: #9b59b6; {estilo_numero}'>{cant_concluidos}</h3><p style='text-align: center; {estilo_pct}'>({pct_concluidos:.1f}%)</p>", unsafe_allow_html=True)
            if st.button("✅ Concluídos", key="btn_m4", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'concluidos'

        with col_m5:
            st.markdown(f"<h3 style='text-align: center; color: #34495e; {estilo_numero}'>{cant_total}</h3><p style='text-align: center; {estilo_pct}'>(100%)</p>", unsafe_allow_html=True)
            if st.button("📋 Total Geral", key="btn_m5", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'total'

        # ==========================================
        # SEÇÃO FIXA E SEMPRE ABERTA: CADASTRO RÁPIDO
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("➕ CADASTRO RÁPIDO: Adicionar Novo Protocolo", expanded=True):
            with st.form("form_novo_protocolo_direto", clear_on_submit=True):
                col_c1, col_c2 = st.columns(2)
                numero = col_c1.text_input("Número do Protocolo/SISREG *")
                paciente = col_c2.text_input("Primeiro Nome do Paciente *")
                
                col_c3, col_c4 = st.columns(2)
                servico = col_c3.text_input("Tipo de Serviço (Ex: Tomografia) *")
                interno = col_c4.text_input("Interno Responsável (Opcional)")
                
                submit = st.form_submit_button("Gravar e Atualizar Sistema", use_container_width=True)
                
                if submit and numero and paciente and servico:
                    numero_limpo = str(numero).strip().split('.')[0]
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
                        st.success("✅ Protocolo cadastrado com sucesso!")
                        st.rerun()

        st.divider()

        # ==========================================
        # EXIBIÇÃO FILTRADA DA CATEGORIA SELECIONADA
        # ==========================================
        situacao = st.session_state['filtro_dashboard']
        
        if situacao == 'no_prazo':
            st.markdown("### 🟢 Protocolos Aguardando Regulação (Dentro do Prazo de 15 dias)")
            df_lista = df_no_prazo
        elif situacao == 'vencidos':
            st.markdown("### 🔴 Pendentes de Verificação (Mais de 15 dias sem desfecho/adiamento)")
            df_lista = df_vencidos
        elif situacao == 'adiados':
            st.markdown("### ⏳ Protocolos Adiados (Aguardando Retorno Stipulado)")
            df_lista = df_adiados
        elif situacao == 'total':
            st.markdown("### 📋 Histórico Geral Completo")
            df_lista = df_total
        elif situacao == 'concluidos':
            st.markdown("### ✅ Protocolos Finalizados")
            df_lista = df_concluidos

        if df_lista.empty:
            st.info("Nenhum registro encontrado para esta categoria.")
        else:
            for index, row in df_lista.iterrows():
                dias_espera = (data_hoje - row['Data_Convertida']).days if pd.notna(row['Data_Convertida']) else 0
                
                if row['Status'] == 'Concluido':
                    tag_status = f"✅ FINALIZADO" + (f" [Prioridade {row['Prioridade_Regulacao']}]" if row['Prioridade_Regulacao'] else "")
                elif row['Status'] == 'Adiado':
                    if pd.notna(row['Data_Retorno_DT']) and row['Data_Retorno_DT'] <= data_hoje:
                        tag_status = "⚠️ ADIAMENTO EXPIRADO (Rever Caso)"
                    else:
                        tag_status = f"⏳ ADIADO (Retorna em {row['Data_Retorno_DT'].strftime('%d/%m/%Y') if pd.notna(row['Data_Retorno_DT']) else 'N/A'})"
                else:
                    tag_status = "🔴 VENCIDO" if dias_espera > 15 else "🟢 NO PRAZO"

                info_interno = f" | Interno: {row['Interno']}" if pd.notna(row['Interno']) and str(row['Interno']).strip() != "" else ""
                
                with st.expander(f"{tag_status} | {row['Paciente']} | Espera: {dias_espera} dias{info_interno}"):
                    # Divisão em 3 colunas em vez de 2, para isolar e apertar o código do protocolo
                    col_prot, col_info, col_acoes = st.columns([1, 1.5, 2.5])
                    
                    with col_prot:
                        st.markdown("**Protocolo:**")
                        # Por estar em uma coluna estreita, o botão de copiar fica encostado no número
                        st.code(row['Protocolo'], language=None)

                    with col_info:
                        st.write(f"**Serviço:** {row['Servico']}")
                        st.write(f"**Data:** {row['Data_Convertida'].strftime('%d/%m/%Y') if pd.notna(row['Data_Convertida']) else 'N/A'}")

                    with col_acoes:
                        if row['Status'] != 'Concluido':
                            obs_atual = row['Observacoes'] if pd.notna(row['Observacoes']) else ""
                            nova_obs = st.text_area("Anotações / Evolução do Caso:", value=obs_atual, key=f"obs_{row['ID']}", height=68)
                            if st.button("💾 Atualizar Notas", key=f"btn_obs_{row['ID']}"):
                                df.at[index, 'Observacoes'] = nova_obs
                                df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                conn.update(worksheet="Dados", data=df_salvar)
                                st.success("Anotação salva!")
                                st.rerun()

                            st.divider()
                            c_b1, c_b2 = st.columns(2)
                            
                            with c_b1:
                                prio = st.selectbox("Prioridade (Opcional):", ["", "A", "B", "C", "D"], key=f"prio_{row['ID']}")
                                if st.button("✅ Concluir/Regular", key=f"ok_{row['ID']}", use_container_width=True):
                                    df.at[index, 'Status'] = 'Concluido'
                                    df.at[index, 'Prioridade_Regulacao'] = prio
                                    df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                    conn.update(worksheet="Dados", data=df_salvar)
                                    st.rerun()
                                    
                            with c_b2:
                                dias_a = st.number_input("Dias de adiamento:", min_value=1, value=7, step=1, key=f"dias_{row['ID']}")
                                if st.button("⏳ Confirmar Adiamento", key=f"adiar_{row['ID']}", use_container_width=True):
                                    nova_data = (data_hoje + timedelta(days=dias_a)).strftime("%Y-%m-%d")
                                    df.at[index, 'Status'] = 'Adiado'
                                    df.at[index, 'Data_Retorno'] = nova_data
                                    df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                    conn.update(worksheet="Dados", data=df_salvar)
                                    st.rerun()
                        else:
                            st.info(f"Protocolo finalizado. Notas: {row['Observacoes'] if row['Observacoes'] else 'Nenhuma'}")

    # ==========================================
    # ABA 2: BUSCA AVANÇADA E RELATÓRIOS
    # ==========================================
    with aba_busca:
        st.header("🔍 Buscar e Exportar Dados")
        if not df.empty:
            c_busca1, c_busca2, c_busca3 = st.columns(3)
            texto_busca = c_busca1.text_input("Buscar Nome, Protocolo ou Interno:")
            
            lista_servicos = ["Todos"] + sorted(df['Servico'].dropna().unique().tolist())
            servico_busca = c_busca2.selectbox("Filtrar por Serviço:", lista_servicos)
            
            df['Mes_Ano'] = df['Data_Convertida'].dt.strftime('%m/%Y').fillna('Sem Data')
            lista_meses = ["Todos"] + sorted(df[df['Mes_Ano'] != 'Sem Data']['Mes_Ano'].unique().tolist(), reverse=True)
            mes_busca = c_busca3.selectbox("Filtrar por Mês/Ano:", lista_meses)

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
                st.warning("Nenhum registro encontrado.")
            else:
                colunas_exibicao = ['Protocolo', 'Paciente', 'Servico', 'Data', 'Status', 'Interno', 'Prioridade_Regulacao', 'Observacoes']
                st.dataframe(df_busca[colunas_exibicao], use_container_width=True)

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
