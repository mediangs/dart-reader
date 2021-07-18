import dart_fss as dart
import OpenDartReader
import pandas as pd
import numpy as np
from pandas.api.types import is_numeric_dtype

from dividend_helper import yearly_dividends_raw, yearly_dividends
from share_helper import yearly_share_volume, yearly_share_prices


def safe_df_append(merged, df):
    if df is not None:
        if merged is None:
            merged = df
        else:
            merged = merged.append(df)
    return merged


def _conditional_exp(condition):
    exprs = []
    for k, v in condition.items():
        exprs.append(f"(df['{k}'].str.contains('{v}'))")
    s = ' & '.join(exprs)
    return s


def account_meet_conditions(df, conditions):
    for c in conditions:
        r = df[eval(_conditional_exp(c))]
        if len(r) > 0:
            return r
        else:
            print(f'{_conditional_exp(c)} 를 만족하는 row 는 없음')
    return None


def pretty_statement(statement):
    """
    1. multi-column header를 가짐, 이를 하나의 column header로 만듦
    2. 'class', 'label_en', 'label_ko' column을 제거
    3. index를 year로 설정
    :param statement:
    :return:
    """

    if statement is not None:
        statement.columns = pd.Index(
            [e[0] if e[0].replace('-', '').isnumeric() else e[1] for e in statement.columns.tolist()])
        cols = [c for c in statement.columns if
                c.lower()[:5] != 'class' and c.lower() != 'label_en' and c.lower() != 'label_ko']
        statement = statement[cols]
        statement.set_index('concept_id', inplace=True)

        statement = statement.T
        if '-' in statement.index[0]:  # 날짜가 '20200101-20201231'인 경우
            statement.index = [pd.to_datetime(x.split('-')[-1]).year for x in list(statement.index)]
        else:  # 날짜가 '20200101'인 경우
            statement.index = [pd.to_datetime(x).year for x in list(statement.index)]

        statement.index.name = 'year'
        return statement

    print(f'Passed financial statement is None!')
    return None


def pick_common_columns(picking_columns, all_columns):
    """
    all_columns에서 picking_columns에 있는 항목만 골라냄
    """
    return list(set(all_columns) & set(picking_columns))


def financial_statement(company, end, odr, start):

    accounts = get_accounts()
    mdf = yearly_finstate(company.corp_code, start, end, accounts, odr)

    denominating_columns = [e['label'] for e in accounts]
    common_denominating_columns = pick_common_columns(denominating_columns, mdf.columns)

    for column in common_denominating_columns:
        order = next(item for item in accounts if item["label"] == column)['order']
        new_col_name = f'{order}.{column}(억)'
        mdf[new_col_name] = mdf[column] / 100000000
        mdf[new_col_name] = mdf[new_col_name].map('{:,.0f}'.format)

    mdf = mdf[sorted(mdf.columns.tolist())]

    return mdf, common_denominating_columns


def finstate_in_year(stock_code, year, accounts, opendart):

    finstate = opendart.finstate_all(stock_code, year)

    if finstate is None:
        print(f'{stock_code}, {year}년 데이터를 가져올 수 없습니다. ')
        return None

    series = []
    for account in accounts:
        account_row = account_meet_conditions(finstate, account['conditions'])
        if account_row is not None:

            this_year = account_row.iloc[0]['thstrm_amount']
            prev_year = account_row.iloc[0]['frmtrm_amount']
            penultimate_year = account_row.iloc[0]['bfefrmtrm_amount']

            # {2020: 1017050375182, 2019: 1000259401598, 2018: 1045526121935} 의 형식으로 만듦
            info = {year-i: int(e) if len(e.strip()) > 0 else 0
                    for i, e in enumerate([this_year, prev_year, penultimate_year])}

            s = pd.Series(info, name=account['label'])
            s.index.name = 'year'
            series.append(s)
        else:
            print(f"[{account['label']} : {account['conditions']}] not exist!")

    return pd.DataFrame({s.name: s for s in series})


def yearly_finstate(stock_code, start, end, accounts, opendart):
    mdf = None
    for year in range(start, end + 1):
        df = finstate_in_year(stock_code, year, accounts, opendart)
        mdf = safe_df_append(mdf, df)

    mdf = mdf[~mdf.index.duplicated(keep='first')]
    return mdf


def yearly_company_performance(company, start, end, odr):

    dividend_criteria = [{'se': '주당순이익'}, {'se': '주당 현금배당금(원)'},
                         {'se': '현금배당수익률(%)'}]

    annual_dividends = yearly_dividends(yearly_dividends_raw(company.corp_code, start, end), dividend_criteria)
    annual_share_prices = yearly_share_prices(company.stock_code, start, end)
    annual_share_volume = yearly_share_volume(company.stock_code, start, end, odr)

    mdf, common_denominating_columns = financial_statement(company, end, odr, start)

    mdf = pd.merge(mdf, annual_share_prices, on='year', how='outer')
    mdf = pd.merge(mdf, annual_share_volume, on='year', how='outer')
    mdf = pd.merge(mdf, annual_dividends, on='year', how='outer')
    mdf.drop(['주가날짜'], axis=1, inplace=True)
    mdf.sort_index(axis=0, inplace=True)
    mdf.fillna(0, inplace=True)

    if {'지배기업소유주당기순이익', '지배기업소유주자본'}.issubset(mdf.columns):
        mdf['ROE'] = mdf['지배기업소유주당기순이익'] / mdf['지배기업소유주자본'].rolling(min_periods=1, window=2).mean()
        mdf['ROE'] = mdf['ROE'].map('{:,.1%}'.format)

    # BPS(Book value per share)
    if {'지배기업소유주자본', '주식수'}.issubset(mdf.columns):
        mdf['BPS'] = mdf['지배기업소유주자본'].div(mdf['주식수'].replace({0: np.nan}))
        mdf['BPS'] = mdf['BPS'].map('{:,.0f}'.format)

    mdf.drop(common_denominating_columns, axis=1, inplace=True)

    return mdf


# def yearly_finstate(stock_code, start, end, accounts, opendart):
#     merged = None
#     for year in range(end, start - 1, -3):
#         df = finstate_in_year(stock_code, year, accounts, opendart)
#         if df is not None:
#             if merged is None:
#                 merged = df
#             else:
#                 merged = merged.append(df)
#
#     return merged


def finstate_in_quarter(stock_code, year, accounts, opendart):
    '''
    reprt_code = [
    '11011' = 사업보고서, 4Q
    '11012' = 반기보고서, 2Q
    '11013' = 1분기보고서, 1Q
    '11014' = 3분기보고서, 3Q
    ]
    :param stock_code:
    :param year:
    :param accounts:
    :param opendart:
    :return:
    '''

    reprt_code = {'11013': '1Q', '11012': '2Q',  '11014': '3Q', '11011': '4Q'}

    dfs = []
    for code, quarter in reprt_code.items():

        finstate = opendart.finstate_all(stock_code, year, reprt_code=code)

        if finstate is not None:
            series = []
            for account in accounts:
                if account['label'] == '보고서':
                    sub_docs = opendart.sub_docs(finstate['rcept_no'][0], match='사업의 내용')
                    _url = sub_docs.iloc[0]['url']
                    #_url = f'<a href="{_url}">보고서</a>'
                    info = {f'{year}.{quarter}': _url}
                    s = pd.Series(info, name='보고서')
                    s.index.name = 'year'
                    series.append(s)
                else:
                    account_row = account_meet_conditions(finstate, account['conditions'])
                    if account_row is not None:
                        this_year = account_row.iloc[0]['thstrm_amount']
                        info = {f'{year}.{quarter}': int(this_year) if len(this_year) > 0 else 0}

                        s = pd.Series(info, name=account['label'])
                        s.index.name = 'year'
                        series.append(s)

            dfs.append(pd.DataFrame({s.name: s for s in series}))

    return None if len(dfs) == 0 else pd.concat(dfs, axis=0).sort_index(axis=0)

def quarterly_company_performance(company, start, end, odr):
    accounts = get_accounts()
    mdf = None
    for year in range(start, end+1):
        df = finstate_in_quarter(company.stock_code, year, accounts, odr)
        mdf = safe_df_append(mdf, df)

    for column in mdf:
        order = next(item for item in accounts if item["label"] == column)['order']
        if is_numeric_dtype(mdf[column]):
            new_col_name = f'{order}.{column}(억)'
            mdf[new_col_name] = mdf[column] / 100000000
            mdf[new_col_name] = mdf[new_col_name].map('{:,.0f}'.format)
        else:
            new_col_name = f'{order}.{column}'
            mdf[new_col_name] = mdf[column]

    mdf = mdf[sorted(mdf.columns.tolist())]
    denominating_columns = [e['label'] for e in accounts]
    mdf.drop(denominating_columns, axis=1, inplace=True)

    return mdf


def get_accounts():
    return [{'label': '매출액', 'order': 1,
             'conditions': [{'account_nm': '매출액'},
                            {'account_id': 'ifrs-full_Revenue'},
                            {'account_id': 'ifrs_Revenue'},
                            {'account_nm': '영업수익'}]},

            {'label': '지배기업소유주당기순이익', 'order': 2,
             'conditions': [{'account_id': 'full_ProfitLossAttributableToOwnersOfParent'},
                            {'account_nm': '당기순이익', 'account_detail': '지배기업의 소유주'},
                            {'account_nm': '당기순이익', 'account_detail': '지배기업 소유주'},
                            {'account_nm': '당기순이익', 'account_detail': '지배지분 | 이익잉여금'},
                            {'account_nm': '분기순이익', 'account_detail': '지배기업의 소유주'},
                            {'account_nm': '분기순이익', 'account_detail': '지배기업 소유주'},
                            {'account_nm': '분기순이익', 'account_detail': '지배지분 | 이익잉여금'}, #SK가스
                            {'account_nm': '분기순손실', 'account_detail': '지배기업의 소유주'},
                            {'account_nm': '반기순이익', 'account_detail': '지배기업의 소유주'},  # ifrs_ProfitLoss
                            {'account_nm': '반기순이익', 'account_detail': '지배기업 소유주'},
                            {'account_nm': '반기순이익', 'account_detail': '지배지분 | 이익잉여금'},
                            {'account_id': 'ifrs_ProfitLoss', 'account_detail': '지배기업의 소유주'},
                            {'account_id': 'ifrs_ProfitLoss', 'account_detail': '지배기업 소유주'},

                            ]},

            {'label': '지배기업소유주자본', 'order': 3,
             'conditions': [{'account_id': 'full_EquityAttributableToOwnersOfParent'},
                            {'account_id': 'ifrs_EquityAttributableToOwnersOfParent'}]},

            {'label': '무형자산', 'order': 4,
             'conditions': [{'account_id': 'full_IntangibleAssetsOtherThanGoodwill'},
                            {'account_nm': '무형자산'}]},

            {'label': '재고자산', 'order': 5,
             'conditions': [{'account_id': 'full_Inventories'},
                            {'account_nm': '재고자산'}]},

            {'label': '매출채권', 'order': 6,
             'conditions': [{'account_id': 'ShortTermTradeReceivable'},
                            {'account_id': 'TradeAndOtherCurrentReceivables'},
                            {'account_nm': '매출채권'}]},

            {'label': '부채총계', 'order': 7,
             'conditions': [{'account_id': 'full_Liabilities'},
                            {'account_nm': '부채총계'}]},

            {'label': '보고서', 'order': 8,
             'conditions': []}

            ]


def test():
    from key import api_key
    dart.set_api_key(api_key=api_key)
    opendartreader = OpenDartReader(api_key)
    corp_list = dart.get_corp_list()
    df = yearly_company_performance(corp_list.find_by_corp_name('AJ네트웍스', exactly=True)[0], 2015, 2020, opendartreader)

    #df = quarterly_company_performance(corp_list.find_by_corp_name('삼성전자', exactly=True)[0], 2019, 2021, opendartreader)
    #df = finstate_in_quarter('051500', 2020, get_accounts(), opendartreader)
    print(df)


    '''
    print('=== 삼성전자 ===')
    ret = get_company_sheet(corp_list.find_by_corp_name('AJ네트웍스', exactly=True)[0], 2015, 2020, opendartreader)
    print(ret)
    '''

    #print(df.head().to_markdown())

if __name__ == '__main__':
    test()
