import streamlit as st
import dart_fss as dart
import pandas as pd
import OpenDartReader
from statement_helper import yearly_company_performance, quarterly_company_performance

corps_loaded = False


def load_corps():
    corp_list = dart.get_corp_list()
    return corp_list


def app():

    global corps_loaded
    st.set_page_config(layout="wide")

    quant_data = st.cache(pd.read_csv)('./data/quant-20212Q.csv')
    all_category = quant_data['업종 (대)'].unique()

    selected_category = st.sidebar.selectbox('업종선택(2021.1Q) 적자순', all_category)
    filtered_qdf = quant_data.loc[quant_data['업종 (대)'] == selected_category]
    st.write(filtered_qdf)

    f_name = filtered_qdf['회사명'].to_list()
    f_code = [e[1:] for e in filtered_qdf['코드 번호'].to_list()]
    filtered_name_code = [f'{x} : {y}' for x, y in zip(f_name, f_code)]

    # Open DART API KEY 설정
    #api_key = st.text_input("Enter Dart api key")
    #from key import api_key

    api_key = st.secrets["api_key"]

    if len(api_key) > 0:
        opendart = OpenDartReader(api_key)
        dart.set_api_key(api_key=api_key)

        if not corps_loaded:
            with st.spinner('Loading...'):
                corp_list = load_corps()
            corps_loaded = True

        all_name_code = [f'{c.corp_name} : {c.stock_code}' for c in corp_list.corps
                         if c.stock_code is not None ]

        scope = st.sidebar.radio('범위', [f'{selected_category}', '전체'])
        if scope == '전체':
            list_scope = sorted(all_name_code)
        else:
            list_scope = filtered_name_code

        selected_company = st.sidebar.selectbox(f'select a company', list_scope)

        start = st.sidebar.number_input("Start year", 2015)

        company = corp_list.find_by_stock_code(selected_company[-6:])

        naver_url = f'<a href="https://finance.naver.com/item/main.nhn?code={company.stock_code}" ' \
                    f'target="_blank" rel="noopener noreferrer">{company.corp_name} 네이버 금융링크</a>'
        st.sidebar.markdown(naver_url, unsafe_allow_html=True)

        if st.sidebar.button('년간 사업보고서'):
            st.subheader(f'{selected_company} 년간 사업보고서')
            with st.spinner('Loading...'):
                company_sheet = yearly_company_performance(company, start, 2021, opendart)
            st.write(company_sheet)

        if st.sidebar.button('분기별 보고서'):
            st.subheader(f'{selected_company} 분기별 보고서')
            with st.spinner('Loading...'):
                q_company_sheet = quarterly_company_performance(company, start, 2021, opendart)
            st.write(q_company_sheet)





if __name__ == '__main__':
    app()
