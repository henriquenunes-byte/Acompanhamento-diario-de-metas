import streamlit as st
import pandas as pd
import numpy as np

# Configuração inicial da página
st.set_page_config(page_title="Análise de Entregas e Metas", layout="wide")

st.title("📦 Análise de Aderência de Metas Logísticas")
st.write("Faça o upload dos arquivos extraídos do sistema para gerar o cruzamento de dados.")

# Criando colunas para organizar os botões de upload
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Dados de Entrega")
    upload_dados = st.file_uploader("Arquivo principal (ex: n.s.csv)", type=['csv'])

with col2:
    st.subheader("2. Tabela de Metas")
    upload_metas = st.file_uploader("Aba Meta salva em CSV (ex: Meta.csv)", type=['csv'])

# Só executa o código se os dois arquivos forem inseridos
if upload_dados is not None and upload_metas is not None:
    st.divider()
    
    with st.spinner('Processando e cruzando os dados...'):
        try:
            # --- LEITURA E LIMPEZA: DADOS ---
            # Tenta ler com ';' primeiro (Padrão Brasil), se falhar, tenta com ','
            try:
                df_dados = pd.read_csv(upload_dados, sep=';')
                if len(df_dados.columns) < 3:
                    upload_dados.seek(0)
                    df_dados = pd.read_csv(upload_dados, sep=',')
            except:
                upload_dados.seek(0)
                df_dados = pd.read_csv(upload_dados, sep=',')
                
            df_dados.columns = df_dados.columns.str.strip()
            
            # Checa se a coluna principal existe
            if 'Qtd Prevista' not in df_dados.columns:
                st.error("Erro: A coluna 'Qtd Prevista' não foi encontrada nos Dados de Entrega.")
                st.stop()
            
            df_dados['Qtd Prevista'] = pd.to_numeric(df_dados['Qtd Prevista'], errors='coerce')
            df_dados['Entregue no Prazo'] = pd.to_numeric(df_dados['Entregue no Prazo'], errors='coerce')
            df_dados['Prazo Real'] = pd.to_numeric(df_dados['Prazo Real'].astype(str).str.replace(',', '.'), errors='coerce')
            
            df_dados['N.S Real (Calculado)'] = df_dados['Entregue no Prazo'] / df_dados['Qtd Prevista']
            df_dados['Chave_Busca'] = df_dados['UF'].astype(str).str.strip() + df_dados['Grupo Transp.'].astype(str).str.strip()

            # --- LEITURA E LIMPEZA: METAS ---
            try:
                df_meta = pd.read_csv(upload_metas, skiprows=2, sep=';')
                if len(df_meta.columns) < 5:
                    upload_metas.seek(0)
                    df_meta = pd.read_csv(upload_metas, skiprows=2, sep=',')
            except:
                upload_metas.seek(0)
                df_meta = pd.read_csv(upload_metas, skiprows=2, sep=',')
            
            # Trava de segurança para garantir que leu no mínimo as 5 colunas vitais
            if len(df_meta.columns) < 5:
                st.error(f"Erro: O arquivo de Metas não pôde ser lido corretamente (Encontradas apenas {len(df_meta.columns)} colunas). Certifique-se de que salvou a aba correta em CSV.")
                st.stop()

            df_meta = df_meta.iloc[:, :5].copy()
            df_meta.columns = ['Estado', 'Concatenar_2', 'Transportadora', 'N.S Projetado', 'Prazo Projetado']
            
            df_meta = df_meta.dropna(subset=['Estado', 'Transportadora'])
            df_meta = df_meta[df_meta['Estado'] != df_meta['Transportadora']] 
            
            df_meta['N.S Projetado'] = pd.to_numeric(df_meta['N.S Projetado'], errors='coerce')
            df_meta['Prazo Projetado'] = pd.to_numeric(df_meta['Prazo Projetado'], errors='coerce')
            df_meta['Chave_Busca'] = df_meta['Estado'].astype(str).str.strip() + df_meta['Transportadora'].astype(str).str.strip()

            # --- CRUZAMENTO ---
            dict_ns_meta = dict(zip(df_meta['Chave_Busca'], df_meta['N.S Projetado']))
            dict_prazo_meta = dict(zip(df_meta['Chave_Busca'], df_meta['Prazo Projetado']))
            
            df_dados['N.S Projetado (Meta)'] = df_dados['Chave_Busca'].map(dict_ns_meta)
            df_dados['Prazo Projetado (Meta)'] = df_dados['Chave_Busca'].map(dict_prazo_meta)

            # --- REGRAS DE ADERÊNCIA ---
            df_dados['Aderente N.S?'] = np.where(
                df_dados['N.S Projetado (Meta)'].isna(), 'Sem Meta',
                np.where(df_dados['N.S Real (Calculado)'] >= df_dados['N.S Projetado (Meta)'], 'Sim', 'Não')
            )
            
            df_dados['Aderente Prazo?'] = np.where(
                df_dados['Prazo Projetado (Meta)'].isna(), 'Sem Meta',
                np.where(df_dados['Prazo Real'] <= df_dados['Prazo Projetado (Meta)'], 'Sim', 'Não')
            )

            # --- FORMATAÇÃO FINAL ---
            df_dados['N.S Real (Calculado)'] = (df_dados['N.S Real (Calculado)'] * 100).round(2).astype(str) + '%'
            df_dados['N.S Projetado (Meta)'] = (df_dados['N.S Projetado (Meta)'] * 100).round(2).astype(str) + '%'
            df_dados['N.S Projetado (Meta)'] = df_dados['N.S Projetado (Meta)'].replace('nan%', '-')
            
            colunas_finais = [
                'Dt Prazo Entrega', 'UF', 'Grupo Transp.', 'Qtd Prevista', 'Entregue no Prazo', 
                'N.S Real (Calculado)', 'N.S Projetado (Meta)', 'Aderente N.S?', 
                'Prazo Prometido', 'Prazo Real', 'Prazo Projetado (Meta)', 'Aderente Prazo?'
            ]
            
            df_analise = df_dados[colunas_finais].copy()
            df_analise['Dt Prazo Entrega'] = pd.to_datetime(df_analise['Dt Prazo Entrega'], format='%d/%m/%Y', errors='coerce')
            df_analise = df_analise.sort_values(by=['Dt Prazo Entrega', 'UF'])
            df_analise['Dt Prazo Entrega'] = df_analise['Dt Prazo Entrega'].dt.strftime('%d/%m/%Y')

            # --- INTERFACE DE RESULTADOS ---
            st.success("✅ Análise concluída com sucesso!")
            
            st.write("### Prévia dos Dados Processados:")
            st.dataframe(df_analise.head(15))
            
            csv = df_analise.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
            st.download_button(
                label="📥 Baixar Planilha Completa (CSV)",
                data=csv,
                file_name='analise_aderencia_metas.csv',
                mime='text/csv',
            )

        except Exception as e:
            st.error(f"Ocorreu um erro crítico. Detalhe técnico: {e}")
