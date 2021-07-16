import streamlit as st
import dart_fss as dart
import OpenDartReader
from dart_helper import company_performance, quarterly_company_performance


corps_loaded = False

def load_corps():
    corp_list = dart.get_corp_list()
    return corp_list


def app():
    # Open DART API KEY 설정
    # api_key = 'e8c0a74f3a04fa4cceb74876b3605529f5dd183b'
    api_key = st.text_input("api key")

    opendart = OpenDartReader(api_key)
    dart.set_api_key(api_key=api_key)

    global corps_loaded
    if not corps_loaded:
        corp_list = load_corps()
        corps_loaded = True

    names = [f'{c.corp_name} : {c.stock_code}' for c in corp_list.corps
             if c.stock_code is not None ]
    names = sorted(names)

    start = st.number_input("Start year", 2010)
    selected_company = st.selectbox('select a company', names)
    company = corp_list.find_by_stock_code(selected_company[-6:])

    if st.button('년간 : Get data!'):
        st.header(f'{selected_company}')
        company_sheet = company_performance(company, start, 2021, opendart)
        st.write(company_sheet)

    if st.button('분기별 : Get data!'):
        st.header(f'{selected_company}')
        q_company_sheet = quarterly_company_performance(company, start, 2021, opendart)
        st.write(q_company_sheet)


if __name__ == '__main__':
    app()
