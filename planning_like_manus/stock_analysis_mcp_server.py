import pandas as pd
from mcp.server.fastmcp import FastMCP
from tools.read_local_financial_report import get_financial_report
from tools.analysis_local_all_stock_price import analyze_stocks

# Create an MCP server
mcp = FastMCP("stock-analysis-mcp")

@mcp.tool()
def get_financial_report_by_stocks(stock_codes : list[str]) -> dict:
    """根据股票代码列表查询出财务报表数据"""
    return get_financial_report.invoke({"stock_codes": stock_codes})

@mcp.tool()
def analyze_stocks_by_stocks(stock_codes : list[str]) -> pd.DataFrame:
    """根据股票代码列表查询股票分析数据"""
    return analyze_stocks.invoke({"stock_codes": stock_codes})

# Add this code to run the server with SSE enabled
if __name__ == "__main__":
    # Start the server with SSE enabled
    mcp.run(transport="sse")
    print("Stock Analysis MCP Server running with SSE enabled on port 8000")
