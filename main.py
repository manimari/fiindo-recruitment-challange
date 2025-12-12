
import asyncio
from collections import defaultdict
import logging
import statistics
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker 
import aiohttp 
from tqdm.asyncio import tqdm 

from src.models import IndustryAggregation, TickerStatistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


FIRST_NAME = "**changeme**"  
LAST_NAME = "**changeme**"   
BASE_URL = "https://api.test.fiindo.com/api/v1" 
AUTH_HEADERS = {"Authorization": f"Bearer {FIRST_NAME}.{LAST_NAME}"} 
ALLOWED_INDUSTRIES = {'Banks - Diversified', 'Software - Application', 'Consumer Electronics'}  
DATABASE_URL = 'sqlite:///fiindo_challenge.db'

# Create DB engine and sessionmaker
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

async def request(url: str, session: aiohttp.ClientSession, method: str = "GET", params: dict = None) -> dict | None:
    """
    Generic async HTTP request handler.
    Args:
        url : API endpoint
        session : HTTP session
        method : "GET" or "POST"
        params : Query params for GET or JSON payload for POST
    Returns:
        JSON response from API, or None if error occurs
    """
    try:   
        if method == "GET": 
            async with session.get(url, headers=AUTH_HEADERS, params=params) as response:
                response.raise_for_status()
                return await response.json()
        elif method == "POST": 
            async with session.post(url, headers=AUTH_HEADERS, json=params) as response:
                response.raise_for_status()
                return await response.json()
        else:
            raise NotImplementedError(f"HTTP method {method} is not supported.")
    
    except aiohttp.ClientResponseError as err:
        print(f"HTTP error occurred: {err}") 
        return None
    except Exception as err:
        print(f"An error occurred: {err}") 
        return None
        
async def get_all_symbols(session: aiohttp.ClientSession) -> list[str] | None:
    """
    Fetch the list of all available stock symbols from the API.
    
    Args:
        session : Active HTTP session
    
    Returns:
        List of symbol strings if successful, else None
    """
    url = f"{BASE_URL}/symbols" 
    data = await request(url, session) 
    if isinstance(data, dict) and 'symbols' in data:
        return data['symbols'] 
    return None 

async def get_general_symbol(symbol: str, session: aiohttp.ClientSession) -> dict | None:
    """
    Fetch general profile data for a given stock symbol.
    
    Args:
        symbol : Stock ticker symbol
        session : Active HTTP session
    
    Returns:
        General data dictionary if successful, else None
    """
    url = f"{BASE_URL}/general/{symbol}" 
    data = await request(url, session) 
    return data
    
async def get_eod_per_symbol(symbol: str, session: aiohttp.ClientSession) -> dict | None: 
    """
    Fetch end-of-day (EOD) stock price data for a given symbol.
    
    Args:
        symbol : Stock ticker symbol
        session : Active HTTP session
    
    Returns:
        EOD data dictionary if successful, else None
    """
    url = f"{BASE_URL}/eod/{symbol}" 
    data = await request(url, session) 
    return data
    
async def get_income_statement_per_symbol(symbol: str, session: aiohttp.ClientSession) -> dict | None: 
    """
    Fetch the income statement for a given stock symbol.
    
    Args:
        symbol : Stock ticker symbol
        session : Active HTTP session
    
    Returns:
        Income statement data if successful, else None
    """
    url = f"{BASE_URL}/financials/{symbol}/income_statement"
    data = await request(url, session) 
    return data

async def get_balance_sheet_statement_per_symbol(symbol: str, session: aiohttp.ClientSession) -> dict | None: 
    """
    Fetch the balance sheet statement for a given stock symbol.
    
    Args:
        symbol : Stock ticker symbol
        session : Active HTTP session
    
    Returns:
        Balance sheet data if successful, else None
    """
    url = f"{BASE_URL}/financials/{symbol}/balance_sheet_statement"
    data = await request(url, session) 
    return data

def get_industry_from_general(data: dict) -> str | None:
    """
    Extract industry of a stock from the /general API response.
    
    Args:
        data : JSON response from /general endpoint.
    
    Returns:
        Industry name if successful, else None.
    """
    try:
        return data["fundamentals"]["profile"]["data"][0]["industry"]
    except Exception:
        return None
    
async def filter_symbols_by_industry(symbols: list[str], session: aiohttp.ClientSession) -> list[dict]:
    """
    Filter a list of stock symbols to only include those belonging to allowed industries.
    
    Args:
        symbols : List of stock ticker symbols 
        session : Active HTTP session
    
    Returns:
        List of filtered symbols
    """
    filtered = []

    for symbol in tqdm(symbols, desc="Filtering symbols by industry"):
        general_data = await get_general_symbol(symbol, session)
        if not general_data:
            continue
        industry = get_industry_from_general(general_data)
        if industry in ALLOWED_INDUSTRIES:
            filtered.append({"symbol": symbol, "industry": industry})
    
    return filtered


def get_quarterly_income_data(data: dict) -> tuple[dict | None, dict | None, list[dict] | None]:
        """
        Extracts quarterly income statement data from the /income_statement endpoint and respects timescheme when multiple reports exist for the same quarter.    
        
        Args:
            data : JSON response from /financials/{symbol}/income_statement endpoint
            
        Returns:
        - latest_quarter: the most recent quarter (considering timescheme)
        - previous_quarter: the quarter immediately before the latest 
        - last_4_quarters: up to 4 consecutive quarters for TTM calculation
        """
        income_list = data.get("fundamentals", {}).get("financials", {}).get("income_statement", {}).get("data", []) 
        if not income_list:
            return None, None, []
        
        # Collect only quarterly periods and iterate from newest
        quarterly_entries = [q for q in reversed(income_list) if q.get("period", "").startswith("Q")]
        if not quarterly_entries:
            return None, None, [] 
    
        
        # Group by (calendarYear, period) to handle multiple entries per quarter
        quarter_dict = defaultdict(list)
        for q in quarterly_entries:
            quarter_dict[(q["calendarYear"], q["period"])].append(q)

        # Pick the entry with the smallest timescheme for each quarter
        unique_quarters = []
        for (year, period), entries in quarter_dict.items():
            if len(entries) == 1:
                unique_quarters.append(entries[0])
                continue 
            else: 
                valid_entries = [e for e in entries if e["timescheme"] is not None]
                if not valid_entries:               
                    continue
                smallest_timescheme_entry = min(valid_entries, key=lambda x: int(x["timescheme"].split("-")[1]))
                unique_quarters.append(smallest_timescheme_entry)
        
        # Sort quarters by year descending, then quarter descending (Q4 > Q3 > Q2 > Q1)
        unique_quarters.sort(key=lambda x: (int(x["calendarYear"]), int(x["period"][1])), reverse=True)

        # latest_quarter is the first in sorted list
        latest_quarter = unique_quarters[0]
        
        # Determine previous quarter number/year
        q_num = int(latest_quarter["period"][1])
        year = int(latest_quarter["calendarYear"])
        if q_num == 1:
            prev_q_num = 4
            prev_year = year - 1
        else:
            prev_q_num = q_num - 1
            prev_year = year

        previous_quarter = None
        for entry in quarterly_entries:
            entry_q_num = int(entry["period"][1])
            entry_year = int(entry["calendarYear"])
            if entry_q_num == prev_q_num and entry_year == prev_year:
                previous_quarter = entry
                break

        # Collect last 4 consecutive quarters for TTM
        last_4_quarters = []
        expected_q_num = q_num
        expected_year = year
        for entry in unique_quarters:
            entry_q_num = int(entry["period"][1])
            entry_year = int(entry["calendarYear"])
            if entry_q_num == expected_q_num and entry_year == expected_year:
                last_4_quarters.append(entry)
                # Compute next expected quarter
                if expected_q_num == 1:
                    expected_q_num = 4
                    expected_year -= 1
                else:
                    expected_q_num -= 1
            if len(last_4_quarters) == 4:
                break

        return latest_quarter, previous_quarter, last_4_quarters

def calculate_pe(eod_data: dict, latest_quarter: dict) -> float | None:
    """
    Calculate Price-to-Earnings (P/E) ratio for a stock. 
    
    Args:
        eod_data : JSON response from /eod/{symbol} endpoint, containing adjusted close price. 
        latest_quarter : Latest quarterly income statement, must contain 'eps' or 'epsdiluted'.
    
    Returns:
        P/E ratio if successful, else None
    """
    if not eod_data or not latest_quarter:
        return None

    prices = eod_data.get("stockprice", {}).get("data", []) 
    if not prices:
        return None
        
    current_price = prices[-1]["adjusted_close"]  # latest adjusted close
    eps = latest_quarter.get("epsdiluted") or latest_quarter.get("eps")

    if not eps or eps == 0:
        return None

    pe_ratio = current_price / eps
    return pe_ratio


def calculate_revenue_growth(latest_quarter: dict, previous_quarter: dict) -> float | None: 
    """
    Calculate quarter-over-quarter revenue growth as a percentage. 
    
    Args:
        latest_quarter : Latest quarterly income statement, must contain 'revenue'.
        previous_quarter : Previous quarterly income statement, must contain 'revenue'.
    
    Returns:
        Revenue growth in percentage, or None if revenue data is missing.
    """
    if not latest_quarter or not previous_quarter:
        return None

    latest_revenue = latest_quarter.get("revenue")
    previous_revenue = previous_quarter.get("revenue")

    if not latest_revenue or not previous_revenue:
        return None

    return (latest_revenue - previous_revenue) / previous_revenue * 100


def calculate_net_income_ttm(quarterly_entries: list[dict]) -> float | None:
    """
    Calculate Trailing Twelve Months (TTM) Net Income by summing the last 4 consecutive quarters. 
    
    Args:
        quarterly_entries : List of up to 4 quarterly income statements, ordered newest to oldest. Each entry must contain 'netIncome'.
    
    Returns:
        TTM net income, or None if the list is empty or missing net income values.
    """
    if not quarterly_entries or len(quarterly_entries) < 4:
        return None

    # Sum netIncome
    ttm_net_income = sum(q.get("netIncome", 0) for q in quarterly_entries)
    return ttm_net_income


def calculate_debt_ratio(balance_data: dict) -> float | None:
    """
    Calculate Debt-to-Equity ratio from balance sheet data.

    Args:    
        balance_data : Balance sheet response from get_balance_sheet_statement_per_symbol, expected to contain 'totalLiabilities' and 'totalEquity' for the latest FY.
        
    Returns:
        Debt-to-Equity ratio (totalLiabilities / totalEquity) for the most recent FY, or None if required data is missing or totalEquity is zero.
    """
    bs_entries = balance_data.get("fundamentals", {}).get("financials", {}).get("balance_sheet_statement", {}).get("data", [])
    if not bs_entries:
        return None
    
    # Filter for full year data (FY)
    fy_entries = [entry for entry in reversed(bs_entries) if entry.get("period") == "FY"]
    if not fy_entries:
        return None
    
    latest_fy = fy_entries[0]
    
    total_debt = latest_fy.get("totalLiabilities")
    total_equity = latest_fy.get("totalEquity") 
    
    if total_debt is None or total_equity is None or total_equity == 0:
        return None
    
    debt_ratio = total_debt / total_equity
    return debt_ratio


async def activate_speed_boost(session: aiohttp.ClientSession) -> dict | None: 
    """
    Activate speed boost on the Fiindo API.

    Args:
        session : Active HTTP session.

    Returns:
        Response from the API, or None if an error occurs.

    Notes:
        - This is a POST request that uses first_name and last_name for authentication.
    """
    url = f"{BASE_URL}/speedboost"
    
    payload = {
        "first_name": FIRST_NAME,
        "last_name": LAST_NAME
    }
    
    return await request(url, session, method="POST", params=payload)




        
async def main():
    async with aiohttp.ClientSession() as session:
        logging.info("Activating API speed boost...")
        await activate_speed_boost(session)
        
        logging.info("Fetching all symbols...")
        symbols = await get_all_symbols(session)
        logging.info(f"Total symbols fetched: {len(symbols)}")
        
        logging.info("Filtering symbols by allowed industries...")
        filtered = await filter_symbols_by_industry(symbols, session)
        logging.info(f"Filtered symbols count: {len(filtered)}")
            
        results = []  # per-ticker storage

        logging.info("Processing each symbol...")
        for item in tqdm(filtered, desc="Processing tickers"):
            symbol = item["symbol"]
            industry = item["industry"]

            # Fetch all financials for this symbol
            income_data = await get_income_statement_per_symbol(symbol, session)
            balance_data = await get_balance_sheet_statement_per_symbol(symbol, session)
            eod_data = await get_eod_per_symbol(symbol, session)

            if not income_data or not balance_data or not eod_data:
                logging.warning(f"Skipping {symbol} due to missing data.")
                continue

            # Extract quarterly data
            latest_q, previous_q, last_4_q = get_quarterly_income_data(income_data)


            # Skip ticker if latest quarter data does not exist
            if not latest_q:
                logging.warning(f"Skipping {symbol}: no valid latest quarterly income data.")
                continue

            # Calculations
            pe = calculate_pe(eod_data, latest_q)
            rev_growth = calculate_revenue_growth(latest_q, previous_q)
            net_income_ttm = calculate_net_income_ttm(last_4_q)
            debt_ratio = calculate_debt_ratio(balance_data)

            # Store results
            results.append({
                "symbol": symbol,
                "industry": industry,
                "pe_ratio": pe,
                "revenue_growth": rev_growth,
                "net_income_ttm": net_income_ttm,
                "debt_ratio": debt_ratio, 
                "latest_quarter_revenue": latest_q.get("revenue") 
            })
        
        logging.info("Aggregating industry data...") 
        # Group by industry
        industry_data = defaultdict(list)
        for r in results:
            industry_data[r["industry"]].append(r)    
            
        # Calculate aggregates
        industry_aggregates = {}
        for industry, tickers in industry_data.items():
            pe_list = [t["pe_ratio"] for t in tickers if t["pe_ratio"] is not None]
            rev_growth_list = [t["revenue_growth"] for t in tickers if t["revenue_growth"] is not None]
            revenue_list = [t["latest_quarter_revenue"] for t in tickers if t["latest_quarter_revenue"] is not None] 
            
            industry_aggregates[industry] = {
                "avg_pe_ratio": statistics.mean(pe_list) if pe_list else None,
                "avg_revenue_growth": statistics.mean(rev_growth_list) if rev_growth_list else None,
                "sum_of_revenue": sum(revenue_list) if revenue_list else None
            }

        logging.info("Saving results to database...")
        # Open a DB session
        session = Session()

        # Save per-ticker results
        for r in results:
            ticker = TickerStatistics(
                symbol=r["symbol"],
                industry=r["industry"],
                pe_ratio=r["pe_ratio"],
                revenue_growth=r["revenue_growth"],
                net_income_ttm=r["net_income_ttm"],
                debt_ratio=r["debt_ratio"]
            )
            session.add(ticker)

        # Save industry aggregates
        for industry, agg in industry_aggregates.items():
            record = IndustryAggregation(
                industry=industry,
                avg_pe_ratio=agg["avg_pe_ratio"],
                avg_revenue_growth=agg["avg_revenue_growth"],
                sum_of_revenue=agg["sum_of_revenue"]
            )
            session.add(record)

        session.commit()
        session.close()
        logging.info("All data saved successfully.")

if __name__ == "__main__":
    asyncio.run(main())