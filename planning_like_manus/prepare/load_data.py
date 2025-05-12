import asyncio
from typing import List
import akshare as ak
import pandas as pd
import time
import random


async def save_data(codes: List[str], start_date: str, end_date: str,
    prefix: str):
    all_data = pd.DataFrame()
    tasklist = []
    for code in codes:
        task = asyncio.create_task(load_data(code, start_date, end_date))
        tasklist.append(task)
    ret = await asyncio.gather(*tasklist)
    for r in ret:
        all_data = pd.concat([all_data, r], axis=0)
    filename = "{} {}_{}.csv".format(prefix, start_date, end_date)
    all_data.to_csv(
        "/Users/fengshiyi/Downloads/shayne/learning/LLM/py-projects/langGraph-demo/test_data/planning_like_manus/akshare/{}".format(
            filename))
    print("保存所有日线数据完成,文件名是:{}".format(filename))


async def load_data(symbol, start_date, end_date, max_retries=3):
    # 由于 akshare 的 API 是同步的，我们需要在线程池中运行它
    loop = asyncio.get_event_loop()

    for attempt in range(max_retries):
        try:
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

        except Exception as e:
            print(
                f"Error fetching data for symbol {symbol}, attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                # Add a random delay between retries to avoid overwhelming the server
                wait_time = 2 + random.random() * 3  # Random wait between 2-5 seconds
                print(f"Waiting {wait_time:.2f} seconds before retry...")
                await asyncio.sleep(wait_time)
                return None
            else:
                print(
                    f"Failed to fetch data for {symbol} after {max_retries} attempts")
                return pd.DataFrame()  # Return empty DataFrame after all retries fail
    return None


def get_all_codes():
    df = ak.stock_zh_a_spot_em()
    codes = df['代码']
    bool_list = df['代码'].str.startswith(('60', '30', '00', '68'))
    return codes[bool_list].to_list()


def save_all_data():
    codes = get_all_codes()
    print("共有{}个股票需要抓取".format(len(codes)))
    n = 100
    for i in range(0, len(codes), n):
        subset = codes[i:i + n]
        if len(subset) > 0:
            asyncio.run(save_data(subset, '20250101', '20250501',
                                  prefix=f"{i}_"))
            print("抓取了{}".format(i))
            # Add delay between batches to avoid overwhelming the server
            if i + n < len(codes):  # If not the last batch
                delay = 3  # 10 seconds delay
                print(f"Waiting {delay} seconds before next batch...")
                time.sleep(delay)


if __name__ == "__main__":
    save_all_data()
    # asyncio.run(save_dayk(["300750", "600519"], "20250407", "20250411"))
