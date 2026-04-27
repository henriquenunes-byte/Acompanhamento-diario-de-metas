import streamlit as st
import pandas as pd
import numpy as np
import io

# Configuração inicial da página
st.set_page_config(page_title="Análise Logística Pro", layout="wide")

st.title("📦 Analisador de Aderência de Metas")
st.markdown("---")

# Interface de Upload
col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Base de Entregas")
    upload_dados = st.file_uploader("Arquivo n.s.csv", type=['csv'])

with col2:
    st.subheader("2. Tabela de Metas")
    upload_metas = st.file_uploader("Arquivo Meta.csv", type=['csv'])

def extrair_df(file, buscar_coluna=None, pular_fixo=0):
    """Função para ler CSV tentando identificar separador e cabeçalho automaticamente"""
    if file is None: return None
    
    # Testa separadores
    conteudo = file.read().decode('utf-8', errors='ignore')
    file.seek(0)
    sep = ';' if conteudo.count(';') > conteudo.count(',') else ','
    
    # Se não precisamos buscar coluna específica, lê normal
    if not buscar_coluna:
        return pd.read_csv(file, sep=sep)

    # Se precisamos buscar a linha do cabeçalho (caso da aba Meta)
    for i in range(0, 15): # Testa as primeiras 15 linhas
        file.seek(0)
        df = pd.read_csv(file, sep=sep, skiprows=i)
        # Limpa nomes de colunas
        df.columns = [str(c).strip() for c in df.columns]
        if buscar_coluna in df.columns:
            return df
    
    file.seek(0)
    return pd.read_csv(file, sep=sep) # Fallback

if upload_dados and upload_metas:
    try:
        with st.spinner('Cruzando informações...'):
            # --- PROCESSAMENTO DADOS DE ENTREGA ---
            df_dados = extrair_df(upload_dados)
            df_dados.columns = df_dados.columns.str.strip()
            
            # Validação básica de colunas
            colunas_necessarias = ['UF', 'Grupo Transp.', 'Qtd Prevista', 'Entregue no Prazo']
            for col in colunas_necessarias:
                if col not in df_dados.columns:
                    st.error(f"Coluna '{col}' não encontrada no arquivo de Entregas. Verifique o cabeçalho.")
                    st.stop()

            # Limpeza numérica
            df_dados['Qtd Prevista'] = pd.to_numeric(df_dados['Qtd Prevista'], errors='coerce')
            df_dados['Entregue no Prazo'] = pd.to_numeric(df_dados['Entregue no Prazo'], errors='coerce')
            
            # Trata Prazo Real (pode vir com vírgula ou traço)
            df_dados['Prazo Real'] = df_dados['Prazo Real'].astype(str).str.replace(',', '.').str.replace('-', 'nan')
            df_dados['Prazo Real'] = pd.to_numeric(df_dados['Prazo Real'], errors='coerce')
            
            df_dados['N.S Real (Calculado)'] = df_dados['Entregue no Prazo'] / df_dados['Qtd Prevista']
            df_dados['Chave_Busca'] = df_dados['UF'].str.strip() + df_dados['Grupo Transp.'].str.strip()

            # --- PROCESSAMENTO METAS (Busca automática pelo cabeçalho 'Estado') ---
            df_meta = extrair_df(upload_metas, buscar_coluna='Estado')
            
            # Seleciona e renomeia apenas as colunas que importam
            # O iloc garante que pegamos as 5 primeiras colunas independente do nome das outras
            df_meta = df_meta.iloc[:, :5]
            df_meta.columns = ['Estado', 'Concatenar_2', 'Transportadora', 'N.S Projetado', 'Prazo Projetado']
            
            # Limpeza de Metas
            df_meta = df_meta.dropna(subset=['Estado', 'Transportadora'])
            df_meta['N.S Projetado'] = pd.to_numeric(df_meta['N.S Projetado'], errors='coerce')
            df_meta['Prazo Projetado'] = pd.to_numeric(df_meta['Prazo Projetado'], errors='coerce')
            df_meta['Chave_Busca'] = df_meta['Estado'].str.strip() + df_meta['Transportadora'].str.strip()

            # --- CRUZAMENTO ---
            dict_ns = df_meta.set_index('Chave_Busca')['N.S Projetado'].to_dict()
            dict_pz = df_meta.set_index('Chave_Busca')['Prazo Projetado'].to_dict()

            df_dados['N.S Projetado (Meta)'] = df_dados['Chave_Busca'].map(dict_ns)
            df_dados['Prazo Projetado (Meta)'] = df_dados['Chave_Busca'].map(dict_pz)

            # --- REGRAS ---
            df_dados['Aderente N.S?'] = np.where(
                df_dados['N.S Projetado (Meta)'].isna(), 'Sem Meta',
                np.where(df_dados['N.S Real (Calculado)'] >= df_dados['N.S Projetado (Meta)'], 'Sim', 'Não')
            )
            
            df_dados['Aderente Prazo?'] = np.where(
                df_dados['Prazo Projetado (Meta)'].isna(), 'Sem Meta',
                np.where(df_dados['Prazo Real'] <= df_dados['Prazo Projetado (Meta)'], 'Sim', 'Não')
            )

            # --- VISUALIZAÇÃO ---
            st.success("Análise gerada!")
            
            # Formatação para exibição
            df_view = df_dados.copy()
            df_view['N.S Real %'] = (df_view['N.S Real (Calculado)'] * 100).round(2).astype(str) + '%'
            df_view['Meta N.S %'] = (df_view['N.S Projetado (Meta)'] * 100).round(2).astype(str) + '%'
            
            cols_exibir = [
                'Dt Prazo Entrega', 'UF', 'Grupo Transp.', 'Qtd Prevista', 'Entregue no Prazo',
                'N.S Real %', 'Meta N.S %', 'Aderente N.S?', 'Prazo Real', 'Prazo Projetado (Meta)', 'Aderente Prazo?'
            ]
            
            st.dataframe(df_view[cols_exibir].head(50))

            # Botão de Download
            csv = df_view[cols_exibir].to_csv(index=False, sep=';', decimal=',').encode('utf-8')
            st.download_button("📥 Baixar Relatório Completo", csv, "analise_logistica.csv", "text/csv")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
        st.info("Dica: Certifique-se de que o arquivo de Metas contém a coluna 'Estado' e 'N.S Projetado'.")
