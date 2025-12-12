from collections import defaultdict

from main import (
    get_quarterly_income_data,
    calculate_pe,
    calculate_revenue_growth,
    calculate_net_income_ttm,
    calculate_debt_ratio,
    get_industry_from_general,
)

# ---------- Dummy Data ----------

dummy_income_data = {
    "fundamentals": {
        "financials": {
            "income_statement": {
                "data": [
                    {
                        "date": "2024-09-30",
                        "period": "Q3",
                        "calendarYear": "2024",
                        "timescheme": "Q-4",
                        "revenue": 36544000000.0,
                        "netIncome": 6516000000.0,
                        "epsdiluted": 0.34
                    }, 
                    {
                        "date": "2024-12-31",
                        "period": "Q4",
                        "calendarYear": "2024",
                        "timescheme": "Q-3",
                        "revenue": 34568000000.0,
                        "netIncome": 351000000.0,
                        "epsdiluted": 0.0109
                    }, 
                    {
                        "date": "2025-03-30",
                        "period": "Q1",
                        "calendarYear": "2025",
                        "timescheme": "Q-2",
                        "revenue": 33851000000.0,
                        "netIncome": 7324000000.0,
                        "epsdiluted": 0.39
                    }, 
                    {
                        "date": "2025-06-30",
                        "period": "Q2",
                        "calendarYear": "2025",
                        "timescheme": "Q-1",
                        "revenue": 33733000000.0,
                        "netIncome": 4733000000.0,
                        "epsdiluted": 0.26
                    }, 
                                       {
                        "date": "2025-06-30",
                        "period": "Q2",
                        "calendarYear": "2025",
                        "timescheme": "Q-2",
                        "revenue": 35733000000.0,
                        "netIncome": 4833000000.0,
                        "epsdiluted": 0.26
                    },
                ]
            }
        }
    }
}


dummy_balance_data = {
    "fundamentals": {
        "financials": {
            "balance_sheet_statement": {
                "data": [
                    {"period": "FY", "totalLiabilities": 50000000000.0, "totalEquity": 25000000000.0},
                    {"period": "FY", "totalLiabilities": 48000000000.0, "totalEquity": 24000000000.0},
                ]
            }
        }
    }
}


dummy_eod_data = {
    "stockprice": {
        "data": [
            {"adjusted_close": 50.0},
            {"adjusted_close": 52.0},
        ]
    }
}

dummy_general_data = {
    "fundamentals": {
        "profile": {
            "data": [
                {"industry": "Software - Application"}
            ]
        }
    }
}

# ---------- Tests ----------

def test_get_quarterly_income_data():
    latest, previous, last_4 = get_quarterly_income_data(dummy_income_data)
    assert latest["period"] == "Q2"
    assert latest["timescheme"] == "Q-1"
    assert latest["revenue"] == 33733000000.0
    assert previous["period"] == "Q1"  
    assert previous["revenue"] == 33851000000.0
    assert len(last_4) == 4
    assert last_4[0]["period"] == "Q2"


def test_missing_previous_quarter():
    data = {
        "fundamentals": {
            "financials": {
                "income_statement": {
                    "data": [
                        {"date": "2025-06-30", "period": "Q2", "calendarYear": "2025", "timescheme": "Q-1", "revenue": 100, "netIncome": 10, "epsdiluted": 1},
                    ]
                }
            }
        }
    }

    latest, previous, last_4 = get_quarterly_income_data(data)
    assert previous is None  # There is no previous quarter
    assert len(last_4) == 1
    
    
def test_empty_income_statement():
    latest, previous, last_4 = get_quarterly_income_data({"fundamentals": {"financials": {"income_statement": {"data": []}}}})
    assert latest is None
    assert previous is None
    assert last_4 == []


def test_debt_ratio_zero_equity():
    data = {
        "fundamentals": {
            "financials": {
                "balance_sheet_statement": {"data": [{"period": "FY", "totalLiabilities": 100, "totalEquity": 0}]}
            }
        }
    }
    assert calculate_debt_ratio(data) is None


def test_debt_ratio_missing_fields():
    data = {"fundamentals": {"financials": {"balance_sheet_statement": {"data": [{}]}}}}
    assert calculate_debt_ratio(data) is None


def test_pe_missing_data():
    latest = {"epsdiluted": 1.0}
    assert calculate_pe({"stockprice": {"data": []}}, latest) is None
    assert calculate_pe(None, latest) is None
    assert calculate_pe({"stockprice": {"data": [{"adjusted_close": 50}]}} , None) is None
    
    
def test_calculate_pe():
    latest, _, _ = get_quarterly_income_data(dummy_income_data)
    pe = calculate_pe(dummy_eod_data, latest)
    assert pe is not None
    assert pe == (52.0 / 0.26) # latest price / epsdiluted


def test_calculate_revenue_growth():
    latest, previous, _ = get_quarterly_income_data(dummy_income_data)
    growth = calculate_revenue_growth(latest, previous)
    expected = (33733000000.0 - 33851000000.0) / 33851000000.0 * 100
    assert growth== expected 


def test_revenue_growth_missing():
    latest = {"revenue": 100}
    previous = {}
    assert calculate_revenue_growth(latest, previous) is None


def test_calculate_net_income_ttm():
    _, _, last_4 = get_quarterly_income_data(dummy_income_data)
    ttm = calculate_net_income_ttm(last_4)
    expected = 4733000000.0 + 7324000000.0 + 351000000.0 + 6516000000.0
    assert ttm == expected


def test_calculate_debt_ratio():
    ratio = calculate_debt_ratio(dummy_balance_data)
    expected = 48000000000.0 / 24000000000.0  # latest FY
    assert ratio == expected


def test_get_industry_from_general():
    industry = get_industry_from_general(dummy_general_data)
    assert industry == "Software - Application"


def test_industry_aggregation():
    # Simulate results list as would be in main()
    results = [
        {"symbol": "AAA", "industry": "Software - Application", "pe_ratio": 20, "revenue_growth": 10, "net_income_ttm": 100},
        {"symbol": "BBB", "industry": "Software - Application", "pe_ratio": 30, "revenue_growth": 20, "net_income_ttm": 200},
        {"symbol": "CCC", "industry": "Banks - Diversified", "pe_ratio": 15, "revenue_growth": 5, "net_income_ttm": 50},
    ]

    industry_data = defaultdict(list)
    for r in results:
        industry_data[r["industry"]].append(r)

    industry_aggregates = {}
    for industry, tickers in industry_data.items():
        pe_list = [t["pe_ratio"] for t in tickers if t["pe_ratio"] is not None]
        rev_list = [t["revenue_growth"] for t in tickers if t["revenue_growth"] is not None]
        net_list = [t["net_income_ttm"] for t in tickers if t["net_income_ttm"] is not None]
        industry_aggregates[industry] = {
            "average_pe_ratio": sum(pe_list)/len(pe_list) if pe_list else None,
            "average_revenue_growth": sum(rev_list)/len(rev_list) if rev_list else None,
            "sum_net_income_ttm": sum(net_list) if net_list else None
        }

    assert industry_aggregates["Software - Application"]["average_pe_ratio"] == 25
    assert industry_aggregates["Software - Application"]["average_revenue_growth"] == 15
    assert industry_aggregates["Software - Application"]["sum_net_income_ttm"] == 300
    assert industry_aggregates["Banks - Diversified"]["average_pe_ratio"] == 15
    assert industry_aggregates["Banks - Diversified"]["sum_net_income_ttm"] == 50
    
