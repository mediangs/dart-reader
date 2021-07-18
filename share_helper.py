import re
from datetime import date
import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup


def share_volume_in_year(stock_code, year, opendart):
    '''
    해당년도의 주식수, 사업보고서에서 추출
    주식의 총수 항목에서
    발행한 주식의 총수 [Ⅳ. 발행주식의 총수 (Ⅱ-Ⅲ), 보통주, 우선주, 합계]
    를 반환

    :param stock_code:
    :param year:
    :return: [Ⅳ. 발행주식의 총수 (Ⅱ-Ⅲ), 보통주, 우선주, 합계]

    '''

    try:
        # 사업보고서 문서번호, 연간보고서는 다음해 3월 말에 제출됨
        rpt_list = opendart.list(stock_code, start=f'{year}-12-01', end=f'{year + 1}-5-30', kind='A')
        rcept_no = rpt_list[rpt_list['rm'] == '연'].iloc[0]['rcept_no']

        # 제목이 잘 매치되는 순서로 소트
        # df는 [title], [url] column 을 가짐
        doc_df = opendart.sub_docs(rcept_no, match='주식의 총수')

        print(f'[{year}] {doc_df.iloc[0]["title"]} 에서 주식수를 추출중...')

        response = requests.get(doc_df.iloc[0]['url'])

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
        else:
            print(response.status_code)
            return None

        shares_row = soup.find('td', text=re.compile('발행주식')).parent
        # shares_row = soup.find('td', text=re.compile('유통주식')).parent
        shares = []
        for r in shares_row.find_all('td'):
            r = r.text.replace(',', '').replace('-', '')
            shares.append(int(r) if r.isdigit() else r)
        return shares

    except:
        print(f"[{year}] Can't retrieve share info!")
        return None


def yearly_share_volume(stock_code, start, end, odr):
    shares = []
    for year in range(start, end + 1):
        r = share_volume_in_year(stock_code, year, odr)
        if r is not None:
            shares.append({'year': year, '보통주': r[1], '우선주': r[2], '주식수': r[3]})

    df_shares = pd.DataFrame(shares)
    df_shares.set_index('year', inplace=True)
    return df_shares


def yearly_share_prices(corp_code, start, end):
    """
    각해의 마지막날(년말) 주가의 'Close'값들을 반환
    """
    prices = None

    for year in range(start - 3, end + 1):
        price = fdr.DataReader(corp_code, date(year, 12, 15), date(year, 12, 31)).iloc[-1:, :]
        prices = price if prices is None else pd.concat([prices, price])

    prices = prices[['Close']]
    prices = prices.reset_index()
    prices = prices.set_index(pd.DatetimeIndex(prices['Date']).year)
    prices.index.name = 'year'
    prices.rename(columns={'Date': '주가날짜', 'Close': '주가'}, inplace=True)

    return prices