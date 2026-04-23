import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7969528399:AAGk2OmA-jOO3sB8Qxz02AeSGuY9MFyfYa0")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "171471899")

US_STOCKS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM",
    "V", "UNH", "XOM", "LLY", "JNJ", "MA", "HD", "AVGO", "PG",
    "MRK", "COST", "ABBV", "CVX", "WMT", "BAC", "KO", "PEP", "NFLX",
    "TMO", "AMD", "ADBE", "CRM", "ORCL", "CSCO", "QCOM", "TXN",
    "INTU", "AMGN", "BKNG", "PYPL", "UBER", "COIN",
]

DE_STOCKS = [
    "ADS.DE", "AIR.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE",
    "CON.DE", "DBK.DE", "DB1.DE", "DHL.DE", "DTE.DE", "EOAN.DE",
    "FRE.DE", "HEI.DE", "HEN3.DE", "IFX.DE", "LIN.DE", "MBG.DE",
    "MRK.DE", "MUV2.DE", "RHM.DE", "RWE.DE", "SAP.DE", "SIE.DE",
    "VOW3.DE", "VNA.DE", "ZAL.DE", "BNR.DE", "SHL.DE", "ENR.DE",
]

CRYPTO = [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
]

TICKER_NAMES = {
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
    "COIN": "Coinbase",
    "ADS.DE": "Adidas", "AIR.DE": "Airbus", "ALV.DE": "Allianz", "BAS.DE": "BASF",
    "BAYN.DE": "Bayer", "BMW.DE": "BMW", "CON.DE": "Continental", "DBK.DE": "Deutsche Bank",
    "DB1.DE": "Deutsche Börse", "DHL.DE": "DHL", "DTE.DE": "Deutsche Telekom",
    "EOAN.DE": "E.ON", "FRE.DE": "Fresenius", "HEI.DE": "HeidelbergMaterials",
    "HEN3.DE": "Henkel", "IFX.DE": "Infineon", "LIN.DE": "Linde", "MBG.DE": "Mercedes-Benz",
    "MRK.DE": "Merck KGaA", "MUV2.DE": "Munich Re", "RHM.DE": "Rheinmetall",
    "RWE.DE": "RWE", "SAP.DE": "SAP", "SIE.DE": "Siemens", "VOW3.DE": "Volkswagen",
    "VNA.DE": "Vonovia", "ZAL.DE": "Zalando", "BNR.DE": "Brenntag",
    "SHL.DE": "Siemens Healthineers", "ENR.DE": "Siemens Energy",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "BNB-USD": "BNB",
    "XRP-USD": "XRP", "SOL-USD": "Solana", "ADA-USD": "Cardano",
    "DOGE-USD": "Dogecoin", "AVAX-USD": "Avalanche", "DOT-USD": "Polkadot",
    "LINK-USD": "Chainlink",
}

# Prediction targets: probability of gaining at least X% in Y months
HORIZONS = {"1M": 21, "3M": 63, "6M": 126}
GAIN_THRESHOLDS = {"1M": 0.05, "3M": 0.10, "6M": 0.15}

DATA_PERIOD = "5y"
MODEL_DIR = "models"
CACHE_DIR = "cache"
DB_PATH = "results.db"
TOP_N = 15
MIN_DATA_ROWS = 300
DAILY_RUN_TIME = "07:00"
