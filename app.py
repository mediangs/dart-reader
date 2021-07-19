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

    quant_data = st.cache(pd.read_csv)('./data/quant-20212Q.csv')
    st.write(quant_data)

    # Open DART API KEY 설정
    #api_key = st.text_input("Enter Dart api key")
    api_key = st.secrets["api_key"]


    if len(api_key) > 0:
        opendart = OpenDartReader(api_key)
        dart.set_api_key(api_key=api_key)

        if not corps_loaded:
            corp_list = load_corps()
            corps_loaded = True

        names = [f'{c.corp_name} : {c.stock_code}' for c in corp_list.corps
                 if c.stock_code is not None ]
        names = sorted(names)

        start = st.number_input("Start year", 2015)
        selected_company = st.selectbox('select a company', names)
        company = corp_list.find_by_stock_code(selected_company[-6:])

        naver_url = f'<a href="https://finance.naver.com/item/main.nhn?code={company.stock_code}" target="_blank" rel="noopener noreferrer">네이버 금융링크</a>'
        st.markdown(naver_url, unsafe_allow_html=True)

        if st.button('년간 사업보고서 : Get data!'):
            st.subheader(f'{selected_company}')
            company_sheet = yearly_company_performance(company, start, 2021, opendart)
            st.write(company_sheet)

        if st.button('분기별 보고서 : Get data!'):
            st.subheader(f'{selected_company}')
            q_company_sheet = quarterly_company_performance(company, start, 2021, opendart)
            #components.html(q_company_sheet.to_html())
            st.write(q_company_sheet)


if __name__ == '__main__':
    app()
