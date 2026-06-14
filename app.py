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

    # Tratamento e higienização inicial dos dados
    if not df.empty:
        colunas_necessarias = ['Interno', 'Observacoes', 'Data_Retorno', 'Prioridade_Regulacao']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = ""
        
        # Correção definitiva do bug do ".0" nos números de protocolo
        df['Protocolo'] = df['Protocolo'].astype(str).apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)
        df['Data_Convertida'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Data_Retorno_DT'] = pd.to_datetime(df['Data_Retorno'], errors='coerce')

    # Organização das Abas Principais (Novo Protocolo agora está integrado no Painel)
    aba_painel, aba_busca = st.tabs(["🏥 Painel de Controle & Cadastro", "🔍 Busca Avançada & Relatórios"])

    # ==========================================
    # ABA 1: PAINEL DE CONTROLE (DASHBOARD + CADASTRO)
    # ==========================================
    with aba_painel:
        data_hoje = datetime.now()
        data_15_dias_atras = data_hoje - timedelta(days=15)

        # Separação estrita dos 4 grupos conforme solicitado
        if not df.empty:
            # 1. No Prazo e Pendente (<= 15 dias)
            df_no_prazo = df[(df['Status'] == 'Pendente') & (df['Data_Convertida'] > data_15_dias_atras)]
            
            # 2. Fora do Prazo / Adiados (> 15 dias ou marcados como Adiado)
            df_fora_prazo = df[(df['Status'] == 'Adiado') | ((df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_15_dias_atras))]
            
            # FILTRO DE EXIBIÇÃO: Oculta temporariamente os adiados cuja data de retorno não chegou
            df_fora_prazo_exibicao = df[
                ((df['Status'] == 'Pendente') & (df['Data_Convertida'] <= data_15_dias_atras)) |
                ((df['Status'] == 'Adiado') & (df['Data_Retorno_DT'] <= data_hoje))
            ]
            
            # 3. Total Geral de Cadastrados
            df_total = df.copy()
            
            # 4. Concluídos / Finalizados
            df_concluidos = df[df['Status'] == 'Concluido']

            cant_no_prazo = len(df_no_prazo)
            cant_fora_prazo = len(df_fora_prazo)
            cant_total = len(df_total)
            cant_concluidos = len(df_concluidos)
        else:
            df_no_prazo = df_fora_prazo = df_fora_prazo_exibicao = df_total = df_concluidos = pd.DataFrame()
            cant_no_prazo = cant_fora_prazo = cant_total = cant_concluidos = 0

        # Estado da sessão para controlar qual categoria está ativa na tela
        if 'filtro_dashboard' not in st.session_state:
            st.session_state['filtro_dashboard'] = 'fora_prazo'  # Padrão focado em pendências críticas

        # Renderização dos cartões clicáveis no Dashboard
        st.markdown("### 📊 Visão Geral (Clique para filtrar a listagem abaixo)")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            st.markdown(f"<h3 style='text-align: center; color: #2ecc71; margin-bottom: 0;'>{cant_no_prazo}</h3>", unsafe_allow_html=True)
            if st.button("⏳ Aguardando (No Prazo)", key="btn_m1", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'no_prazo'
                
        with col_m2:
            st.markdown(f"<h3 style='text-align: center; color: #e74c3c; margin-bottom: 0;'>{cant_fora_prazo}</h3>", unsafe_allow_html=True)
            if st.button("🚨 Adiados / Fora do Prazo", key="btn_m2", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'fora_prazo'
                
        with col_m3:
            st.markdown(f"<h3 style='text-align: center; color: #34495e; margin-bottom: 0;'>{cant_total}</h3>", unsafe_allow_html=True)
            if st.button("📋 Total Cadastrados", key="btn_m3", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'total'
                
        with col_m4:
            st.markdown(f"<h3 style='text-align: center; color: #9b59b6; margin-bottom: 0;'>{cant_concluidos}</h3>", unsafe_allow_html=True)
            if st.button("✅ Concluídos / Regulados", key="btn_m4", use_container_width=True):
                st.session_state['filtro_dashboard'] = 'concluidos'

        # ==========================================
        # SEÇÃO INTEGRADA: CADASTRO DE NOVO PROTOCOLO
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("➕ CADASTRO RÁPIDO: Adicionar Novo Protocolo", expanded=False):
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
        # EXIBIÇÃO DINÂMICA DA SITUAÇÃO SELECIONADA
        # ==========================================
        situacao = st.session_state['filtro_dashboard']
        
        if situacao == 'no_prazo':
            st.markdown("### 🟢 Protocolos Aguardando Regulação (Dentro do Prazo de 15 dias)")
            df_lista = df_no_prazo
        elif situacao == 'fora_prazo':
            st.markdown("### 🔴 Alertas Ativos: Fora do Prazo ou Retorno de Adiamento")
            df_lista = df_fora_prazo_exibicao
        elif situacao == 'total':
            st.markdown("### 📋 Histórico Geral Completo (Todos os Status)")
            df_lista = df_total
        elif situacao == 'concluidos':
            st.markdown("### ✅ Protocolos Finalizados / Regulados")
            df_lista = df_concluidos

        if df_lista.empty:
            st.info("Nenhum registro encontrado para a situação selecionada.")
        else:
            for index, row in df_lista.iterrows():
                dias_espera = (data_hoje - row['Data_Convertida']).days if pd.notna(row['Data_Convertida']) else 0
                
                # Definição de tags e cores visuais para cada cartão
                if row['Status'] == 'Concluido':
                    tag_status = f"✅ FINALIZADO" + (f" [Prioridade {row['Prioridade_Regulacao']}]" if row['Prioridade_Regulacao'] else "")
                elif row['Status'] == 'Adiado':
                    tag_status = "⏳ ADIADO (Aguardando Prazo)"
                else:
                    tag_status = "🔴 CRÍTICO (>30 dias)" if dias_espera > 30 else "🟠 FORA DO PRAZO" if dias_espera > 15 else "🟢 NO PRAZO"

                info_interno = f" | Interno: {row['Interno']}" if pd.notna(row['Interno']) and str(row['Interno']).strip() != "" else ""
                
                with st.expander(f"{tag_status} | {row['Paciente']} | Espera: {dias_espera} dias{info_interno}"):
                    col_info, col_acoes = st.columns([1.5, 2])
                    
                    with col_info:
                        st.write("**Código do Protocolo (Clique no ícone à direita para copiar):**")
                        st.code(row['Protocolo'], language=None)
                        st.write(f"**Serviço:** {row['Servico']}")
                        st.write(f"**Data da Solicitação:** {row['Data_Convertida'].strftime('%d/%m/%Y') if pd.notna(row['Data_Convertida']) else 'N/A'}")
                        if row['Status'] == 'Adiado' and pd.notna(row['Data_Retorno_DT']):
                            st.write(f"**Retorna ao painel em:** {row['Data_Retorno_DT'].strftime('%d/%m/%Y')}")

                    with col_acoes:
                        # Exibe formulários de ação apenas se não estiver concluído
                        if row['Status'] != 'Concluido':
                            obs_atual = row['Observacoes'] if pd.notna(row['Observacoes']) else ""
                            nova_obs = st.text_area("Anotações / Evolução do Caso:", value=obs_atual, key=f"obs_{row['ID']}", height=68)
                            if st.button("💾 Atualizar Histórico/Notas", key=f"btn_obs_{row['ID']}"):
                                df.at[index, 'Observacoes'] = nova_obs
                                df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                conn.update(worksheet="Dados", data=df_salvar)
                                st.success("Anotação salva!")
                                st.rerun()

                            st.divider()
                            c_b1, c_b2 = st.columns(2)
                            
                            with c_b1:
                                prio = st.selectbox("Prioridade da Regulação (Opcional):", ["", "A", "B", "C", "D"], key=f"prio_{row['ID']}")
                                if st.button("✅ Concluir/Regular", key=f"ok_{row['ID']}", use_container_width=True):
                                    df.at[index, 'Status'] = 'Concluido'
                                    df.at[index, 'Prioridade_Regulacao'] = prio
                                    df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                    conn.update(worksheet="Dados", data=df_salvar)
                                    st.rerun()
                                    
                            with c_b2:
                                dias_a = st.number_input("Estipular dias de adiamento:", min_value=1, value=7, step=1, key=f"dias_{row['ID']}")
                                if st.button("⏳ Confirmar Adiamento", key=f"adiar_{row['ID']}", use_container_width=True):
                                    nova_data = (data_hoje + timedelta(days=dias_a)).strftime("%Y-%m-%d")
                                    df.at[index, 'Status'] = 'Adiado'
                                    df.at[index, 'Data_Retorno'] = nova_data
                                    df_salvar = df.drop(columns=['Data_Convertida', 'Data_Retorno_DT'], errors='ignore')
                                    conn.update(worksheet="Dados", data=df_salvar)
                                    st.rerun()
                        else:
                            st.info(f"Protocolo finalizado. Notas registradas: {row['Observacoes'] if row['Observacoes'] else 'Nenhuma'}")

    # ==========================================
    # ABA 2: BUSCA AVANÇADA E RELATÓRIOS (MANTIDA INTEGRALMENTE)
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
