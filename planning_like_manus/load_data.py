import asyncio
from typing import List
import akshare as ak
import pandas as pd

async def save_data(codes:List[str], start_date:str, end_date:str,prefix:str):
     all_data= pd.DataFrame()
     tasklist=[]
     for code in codes:
         task=asyncio.create_task(load_data(code,start_date,end_date))
         tasklist.append(task)
     ret=await asyncio.gather(*tasklist)
     for r in ret:
         all_data=pd.concat([all_data, r],axis=0)
     filename="{} {}_{}.csv".format(prefix,start_date,end_date)
     all_data.to_csv("/Users/fengshiyi/Downloads/shayne/learning/LLM/py-projects/langGraph-demo/test_data/planning_like_manus/akshare/{}".format(filename))
     print("保存所有日线数据完成,文件名是:{}".format(filename))

async def load_data(symbol, start_date, end_date):
    # 由于 akshare 的 API 是同步的，我们需要在线程池中运行它
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, lambda: ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    ))

    if df.empty:
        return pd.DataFrame()
    df['日期'] = pd.to_datetime(df['日期'])
    df.set_index('日期', inplace=True)
    df.sort_index(ascending=False, inplace=True)

    return df

def get_all_codes():
    df=ak.stock_zh_a_spot_em()
    codes=df['代码']
    bool_list=df['代码'].str.startswith(('60','30','00','68'))
    return codes[bool_list].to_list()

def save_all_data():
    codes=get_all_codes()
    print("共有{}个股票需要抓取".format(len(codes)))
    n=100
    for i in range(0, len(codes), n):
        subset = codes[i:i + n]
        if len(subset) > 0:
            asyncio.run(save_data(subset,'20250101','20250501',
                                  prefix=f"{i}_"))
            print("抓取了{}".format(i))

if __name__ == "__main__":
    save_all_data()
    #asyncio.run(save_dayk(["300750", "600519"], "20250407", "20250411"))