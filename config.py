import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

US_STOCKS = [
    # Large cap core
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM",
    "V", "UNH", "XOM", "LLY", "JNJ", "MA", "HD", "AVGO", "PG",
    "MRK", "COST", "ABBV", "CVX", "WMT", "BAC", "KO", "PEP", "NFLX",
    "TMO", "AMD", "ADBE", "CRM", "ORCL", "CSCO", "QCOM", "TXN",
    "INTU", "AMGN", "BKNG", "PYPL", "UBER", "COIN",
    # From user's portfolio
    "NET", "AXP", "CAVA", "RKLB", "OKLO", "IONQ", "NIO", "RGTI",
    "A", "SNEX", "BBIO", "RCEL", "ALHC",
    "QUBT", "ATYR", "RR",
]

DE_STOCKS = [
    # DAX 40
    "ADS.DE", "AIR.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE",
    "CON.DE", "DBK.DE", "DB1.DE", "DHL.DE", "DTE.DE", "EOAN.DE",
    "FRE.DE", "HEI.DE", "HEN3.DE", "IFX.DE", "LIN.DE", "MBG.DE",
    "MRK.DE", "MUV2.DE", "RHM.DE", "RWE.DE", "SAP.DE", "SIE.DE",
    "VOW3.DE", "VNA.DE", "ZAL.DE", "BNR.DE", "SHL.DE", "ENR.DE",
    # From user's portfolio
    "CBK.DE",
    # French/EU stocks (tradeable on Xetra or available via yfinance)
    "AXA.PA",
    # Spanish stocks
    "ACS.MC",
]

CRYPTO = [
    # Core
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
    # From user's portfolio
    "XLM-USD", "ATOM-USD", "TRX-USD", "SHIB-USD",
    "ARB-USD", "OP-USD", "VET-USD",
]

ETFS = [
    # US index ETFs
    "SPY", "QQQ", "IVV", "VTI", "VWO",
    # European ETFs (from user's portfolio + popular ones)
    "IS3Q.DE", "VWCE.DE", "IWDA.AS", "CSPX.L",
    # Sector / thematic
    "GLD", "TLT",
]

TICKER_NAMES = {
    # US Stocks
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon",
    "GOOGL": "Alphabet", "META": "Meta", "TSLA": "Tesla", "JPM": "JPMorgan",
    "V": "Visa", "UNH": "UnitedHealth", "XOM": "ExxonMobil", "LLY": "Eli Lilly",
    "JNJ": "J&J", "MA": "Mastercard", "HD": "Home Depot", "AVGO": "Broadcom",
    "PG": "P&G", "MRK": "Merck", "COST": "Costco", "ABBV": "AbbVie",
    "CVX": "Chevron", "WMT": "Walmart", "BAC": "Bank of America", "KO": "Coca-Cola",
    "PEP": "PepsiCo", "NFLX": "Netflix", "TMO": "ThermoFisher", "AMD": "AMD",
    "ADBE": "Adobe", "CRM": "Salesforce", "ORCL": "Oracle", "CSCO": "Cisco",
    "QCOM": "Qualcomm", "TXN": "Texas Instruments", "INTU": "Intuit",
    "AMGN": "Amgen", "BKNG": "Booking", "PYPL": "PayPal", "UBER": "Uber",
    "COIN": "Coinbase", "NET": "Cloudflare", "AXP": "American Express",
    "CAVA": "CAVA Group", "RKLB": "Rocket Lab", "OKLO": "Oklo",
    "IONQ": "IonQ", "NIO": "NIO", "RGTI": "Rigetti Computing",
    "A": "Agilent", "SNEX": "StoneX Group", "BBIO": "BridgeBio Pharma",
    "RCEL": "AVITA Medical", "ALHC": "Alignment Healthcare",
    "QUBT": "Quantum Computing Inc", "ATYR": "aTyr Pharma", "RR": "Richtech Robotics",
    # German / EU
    "ADS.DE": "Adidas", "AIR.DE": "Airbus", "ALV.DE": "Allianz", "BAS.DE": "BASF",
    "BAYN.DE": "Bayer", "BMW.DE": "BMW", "CON.DE": "Continental", "DBK.DE": "Deutsche Bank",
    "DB1.DE": "Deutsche Börse", "DHL.DE": "DHL", "DTE.DE": "Deutsche Telekom",
    "EOAN.DE": "E.ON", "FRE.DE": "Fresenius", "HEI.DE": "HeidelbergMaterials",
    "HEN3.DE": "Henkel", "IFX.DE": "Infineon", "LIN.DE": "Linde", "MBG.DE": "Mercedes-Benz",
    "MRK.DE": "Merck KGaA", "MUV2.DE": "Munich Re", "RHM.DE": "Rheinmetall",
    "RWE.DE": "RWE", "SAP.DE": "SAP", "SIE.DE": "Siemens", "VOW3.DE": "Volkswagen",
    "VNA.DE": "Vonovia", "ZAL.DE": "Zalando", "BNR.DE": "Brenntag",
    "SHL.DE": "Siemens Healthineers", "ENR.DE": "Siemens Energy",
    "CBK.DE": "Commerzbank", "AXA.PA": "AXA", "ACS.MC": "ACS SA",
    # Crypto
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "BNB-USD": "BNB",
    "XRP-USD": "XRP", "SOL-USD": "Solana", "ADA-USD": "Cardano",
    "DOGE-USD": "Dogecoin", "AVAX-USD": "Avalanche", "DOT-USD": "Polkadot",
    "LINK-USD": "Chainlink", "XLM-USD": "Stellar", "ATOM-USD": "Cosmos",
    "TRX-USD": "Tron", "SHIB-USD": "Shiba Inu",
    "ARB-USD": "Arbitrum", "OP-USD": "Optimism", "VET-USD": "VeChain",
    # ETFs
    "SPY": "S&P 500 ETF", "QQQ": "NASDAQ 100 ETF", "IVV": "iShares S&P 500",
    "VTI": "Vanguard Total Market", "VWO": "Vanguard Emerging Markets",
    "IS3Q.DE": "iShares MSCI World Quality", "VWCE.DE": "Vanguard All-World",
    "IWDA.AS": "iShares Core MSCI World", "CSPX.L": "iShares Core S&P 500",
    "GLD": "Gold ETF", "TLT": "US Treasury Bond ETF",
}

# Prediction targets
HORIZONS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126}
GAIN_THRESHOLDS = {"1W": 0.02, "1M": 0.05, "3M": 0.10, "6M": 0.15}

DATA_PERIOD = "5y"
MODEL_DIR = "models"
CACHE_DIR = "cache"
DB_PATH = "results.db"
TOP_N = 15
MIN_DATA_ROWS = 300
DAILY_RUN_TIME = "07:00"

SECTOR_MAP = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AVGO": "XLK", "ADBE": "XLK",
    "CRM": "XLK",  "ORCL": "XLK", "CSCO": "XLK", "QCOM": "XLK", "TXN": "XLK",
    "INTU": "XLK", "AMD": "XLK",  "NET": "XLK",  "IONQ": "XLK", "RGTI": "XLK",
    "GOOGL": "XLC", "META": "XLC", "NFLX": "XLC",
    "AMZN": "XLY", "TSLA": "XLY", "HD": "XLY", "BKNG": "XLY", "UBER": "XLY",
    "CAVA": "XLY", "NIO": "XLY",
    "JPM": "XLF",  "V": "XLF",   "MA": "XLF",  "BAC": "XLF",  "PYPL": "XLF",
    "COIN": "XLF", "AXP": "XLF", "SNEX": "XLF",
    "UNH": "XLV",  "LLY": "XLV", "JNJ": "XLV", "MRK": "XLV",  "TMO": "XLV",
    "ABBV": "XLV", "AMGN": "XLV", "A": "XLV",  "RCEL": "XLV", "ALHC": "XLV",
    "BBIO": "XLV",
    "PG": "XLP",   "KO": "XLP",  "PEP": "XLP", "COST": "XLP", "WMT": "XLP",
    "XOM": "XLE",  "CVX": "XLE",
    "RKLB": "XLI", "OKLO": "XLI",
    "QUBT": "XLK", "RR": "XLK", "ATYR": "XLV",
}

SECTOR_ETFS = ["XLK", "XLC", "XLY", "XLF", "XLV", "XLP", "XLE", "XLI", "EWG"]
