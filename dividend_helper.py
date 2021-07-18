import dart_fss as dart
import pandas as pd


def yearly_dividends_raw(corp_code, start, end):
    dividends = []
    for year in range(start, end + 1):
        try:
            # dart api 를 이용, 배당정보추출
            dividend = dart.api.info.get_dividend(corp_code, bsns_year=str(year), reprt_code='11011')
            print(f'{year} Retrieve dividend data')
            dividends.append({'year': year, 'dividend': dividend})
        except:
            print(f"{year} Can't retrieve dividend data")

    return dividends


def extract_df_from_dividends_raw(divdends_raw, criterion):

    results = []
    for div in divdends_raw:
        if div['dividend'] is not None:
            try:
                r = next((item for item in div['dividend']['list'] if
                          all(v in item[k] for k, v in criterion.items())), None)

                extract_columns = ['thstrm', 'frmtrm', 'lwfr']  # 올해, 작년, 재작년
                results.extend([{'year': div['year'] - offset_year, criterion['se']: float(r[column].replace(',', ''))}
                                for offset_year, column in enumerate(extract_columns)])

            except:
                print(f'dividend - no result satisfying criterion: {criterion}')

    if len(results) > 0:
        df = pd.DataFrame(results)
        df.set_index('year', inplace=True)
        return df

    return None


def yearly_dividends(dividends_raw, criteria):
    mdf = None
    for criterion in criteria:
        df = extract_df_from_dividends_raw(dividends_raw, criterion)
        if df is not None:
            if mdf is not None:
                mdf = pd.merge(mdf, df, on='year', how='outer')
            else:
                mdf = df

    mdf = mdf[~mdf.index.duplicated(keep='first')]
    return mdf