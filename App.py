import streamlit as st
import pandas as pd
import numpy as np

# Configuração inicial da página
st.set_page_config(page_title="Análise de Entregas e Metas", layout="wide")

st.title("📦 Análise de Aderência de Metas Logísticas")
st.write("Faça o upload dos arquivos para gerar o cruzamento de dados.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Dados de Entrega")
    upload_dados = st.file_uploader("Arquivo principal (ex: n.s.csv)", type=['csv'])

with col2:
    st.subheader("2. Tabela de Metas")
    upload_metas = st.file_uploader("Aba Meta (ex: Meta.csv)", type=['csv'])

if upload_dados is not None and upload_metas is not None:
    st.divider()
    
    with st.spinner('Processando e cruzando os dados...'):
        try:
            # --- LEITURA DE DADOS PRINCIPAIS ---
            # Tenta ler com ponto e vírgula primeiro, se não conseguir, tenta com vírgula
            df_dados = pd.read_csv(upload_dados, sep=';')
            if len(df_dados.columns) < 3:
                upload_dados.seek(0)
                df_dados = pd.read_csv(upload_dados, sep=',')
                
            df_dados.columns = df_dados.columns.str.strip()
            
            df_dados['Qtd Prevista'] = pd.to_numeric(df_dados['Qtd Prevista'], errors='coerce')
            df_dados['Entregue no Prazo'] = pd.to_numeric(df_dados['Entregue no Prazo'], errors='coerce')
            df_dados['Prazo Real'] = pd.to_numeric(df_dados['Prazo Real'].astype(str).str.replace(',', '.'), errors='coerce')
            
            df_dados['N.S Real (Calculado)'] = df_dados['Entregue no Prazo'] / df_dados['Qtd Prevista']
            df_dados['Chave_Busca'] = df_dados['UF'].astype(str).str.strip() + df_dados['Grupo Transp.'].astype(str).str.strip()

            # --- LEITURA DAS METAS ---
            df_meta = pd.read_csv(upload_metas, skiprows=2, sep=';')
            if len(df_meta.columns) < 3:
                upload_metas.seek(0)
                df_meta = pd.read_csv(upload_metas, skiprows=2, sep=',')
            
            # Limpa colunas invisíveis/completamente vazias do Excel
            df_meta = df_meta.dropna(how='all', axis=1)
            
            # --- CORREÇÃO DO ERRO DE COLUNAS ---
            # O sistema vai se adaptar se a planilha tiver 5 ou 4 colunas
            if len(df_meta.columns) >= 5:
                df_meta = df_meta.iloc[:, :5].copy()
                df_meta.columns = ['Estado', 'Concatenar_2', 'Transportadora', 'N.S Projetado', 'Prazo Projetado']
            elif len(df_meta.columns) == 4:
                df_meta = df_meta.iloc[:, :4].copy()
                df_meta.columns = ['Estado', 'Transportadora', 'N.S Projetado', 'Prazo Projetado']
            else:
                st.error("Formato inesperado na aba Meta. Verifique se o arquivo possui as colunas Estado, Transportadora, NS Projetado e Prazo.")
                st.stop()
            
            df_meta = df_meta.dropna(subset=['Estado', 'Transportadora'])
            df_meta = df_meta[df_meta['Estado'] != df_meta['Transportadora']] 
            
            # Substitui as vírgulas por pontos antes de transformar em número (evita erros em números brasileiros)
            df_meta['N.S Projetado'] = pd.to_numeric(df_meta['N.S Projetado'].astype(str).str.replace(',', '.'), errors='coerce')
            df_meta['Prazo Projetado'] = pd.to_numeric(df_meta['Prazo Projetado'].astype(str).str.replace(',', '.'), errors='coerce')
            df_meta['Chave_Busca'] = df
