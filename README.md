# Fiindo Stock Data Aggregation

This project fetches financial and market data for stock tickers from the Fiindo API, calculates key metrics per ticker, and aggregates them by industry. It provides insight into stock performance, revenue growth, profitability, and debt levels.

---

## Features

1. **Per-Ticker Metrics**

   For each stock ticker, the following metrics are calculated:

    **P/E Ratio**  
    Price-to-Earnings ratio, measures stock price relative to earnings  
    `P/E = Latest Adjusted Close Price / EPS Diluted (Latest Quarter)` 

    **Revenue Growth**  
    Quarter-over-quarter revenue growth  
    `Revenue Growth % = (Revenue_latest - Revenue_previous) / Revenue_previous * 100` 

    **Net Income TTM**  
    Trailing Twelve Months net income, sum of last 4 quarters  
    `Net Income TTM = sum of net income of last 4 consecutive quarters` 

    **Debt Ratio**  
    Debt-to-Equity ratio for the latest fiscal year  
    `Debt Ratio = Total Liabilities / Total Equity` 

   > **Note:** P/E ratios may appear unusually high for some tickers due to low EPS in a quarter, different currencies, or one-off accounting events.

2. **Industry Aggregation**

   Metrics are aggregated across all tickers in an industry:

   **Average P/E Ratio**  
   Mean P/E across tickers in the industry  
   `Average P/E = mean(per-ticker P/E)` 

   **Average Revenue Growth**  
   Mean revenue growth across tickers  
   `Average Revenue Growth = mean(per-ticker revenue growth %)` 

   **Sum of Revenue**  
   Sum of the latest quarterly revenue across tickers  
   `Sum Revenue = sum(latest quarter revenue per ticker)` 

---

## Allowed Industries

Only tickers in the following industries are included:

- Banks - Diversified  
- Software - Application  
- Consumer Electronics  

---

## Requirements

- Python 3.10+  
- Packages:

```bash
pip install -r requirements.txt
```

---

## Fiindo API credentials: 
```
FIRST_NAME = "your_first_name"
LAST_NAME = "your_last_name" 
``` 

Replace the placeholder values with your actual Fiindo API credentials.


## Usage

Run the main script to fetch data and calculate metrics:
``` python main.py```


Run unit tests to verify correctness:
```pytest test.py``` 

## Running with Docker

You can run the application using Docker and Docker Compose without manually installing Python or dependencies.

**Build and Run**

From the project root directory: 
```docker-compose up --build```

 - This will build the Docker image and start a container named fiindo_app.

 - The container will run python main.py, fetching financial data, performing calculations, and writing results to the SQLite database fiindo_challenge.db.

 - Any logs and output will be shown in the terminal. 

**Stop the Container**

```docker-compose down``` 

Stops and removes the container but keeps the database file. 

## Notes

Multiple entries for the same quarter are handled using the timescheme. The latest quarter is selected based on the smallest timescheme number.

Missing or zero values in EPS, revenue, or balance sheet fields are handled gracefully to prevent errors.

All metrics are based on quarterly data; TTM adjustments are applied only where relevant.

Results are stored in a SQLite database fiindo_challenge.db with two tables:

  - TickerStatistics – per-ticker metrics

  - IndustryAggregation – aggregated metrics per industry 

Some tickers are skipped during processing and therefore do not appear in the database:
 - If one of the required API calls for that symbol fails (for example, HTTP 500 on income statement or balance sheet), so income, balance sheet, or EOD data is missing.
 - If no valid latest quarterly income data can be determined (for example, no quarterly entries or missing fields required for the calculations).
In these cases, a warning is logged (e.g. “Skipping WDI.SW due to missing data.”), and the ticker is excluded from per-ticker and industry-level results.


