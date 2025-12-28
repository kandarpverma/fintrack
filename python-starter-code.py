# ============================================================================
# INDIAN FINANCE TRACKER - PYTHON STARTER CODE
# Quick implementation examples for bank, stock, and MF integrations
# ============================================================================

import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# 1. FINBOX ACCOUNT AGGREGATOR - BANK ACCOUNT INTEGRATION
# ============================================================================

class BankAggregatorService:
    """
    Integration with FinBox Account Aggregator API
    Handles bank account linking and statement fetching
    """
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.finbox.in/bank-connect/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def initiate_account_linking(self, user_id: str, redirect_url: str) -> Dict:
        """
        Initiate bank account linking via Account Aggregator
        
        Returns:
            dict: Contains linking_id and redirect URL for user
        """
        payload = {
            "user_id": user_id,
            "redirect_url": redirect_url,
            "integration_type": "account_aggregator",
            "include_methods": ["account_aggregator", "net_banking", "manual_upload"]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/initiate-linking",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error initiating account linking: {e}")
            return {"error": str(e)}
    
    def get_linking_status(self, user_id: str) -> Dict:
        """Check if user has completed account linking"""
        try:
            response = requests.get(
                f"{self.base_url}/link-status/{user_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def fetch_bank_statements(self, user_id: str, months: int = 6) -> List[Dict]:
        """
        Fetch linked bank statements
        
        Args:
            user_id: User identifier
            months: Number of months to fetch (max 12)
        
        Returns:
            List of transactions with account details
        """
        try:
            response = requests.get(
                f"{self.base_url}/statements/{user_id}",
                params={"months": min(months, 12)},
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_statements(data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching statements: {e}")
            return []
    
    def get_account_balance(self, user_id: str) -> Dict:
        """
        Get real-time balance from all linked accounts
        
        Returns:
            dict: Account-wise balance details
        """
        try:
            response = requests.get(
                f"{self.base_url}/balance/{user_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _parse_statements(self, raw_data: Dict) -> List[Dict]:
        """Parse raw statement data into structured format"""
        transactions = []
        
        for account in raw_data.get('accounts', []):
            for txn in account.get('transactions', []):
                transactions.append({
                    'account_number': account.get('account_number'),
                    'bank_name': account.get('bank_name'),
                    'date': txn.get('date'),
                    'amount': txn.get('amount'),
                    'type': 'debit' if txn.get('amount', 0) < 0 else 'credit',
                    'description': txn.get('description', ''),
                    'balance': txn.get('balance_after_transaction'),
                    'reference_id': txn.get('reference_id')
                })
        
        return transactions


# ============================================================================
# 2. STOCK PORTFOLIO SERVICE - YFINANCE & NSEPY
# ============================================================================

class StockPortfolioService:
    """
    Manage stock holdings using yfinance for prices and NSEpy for Indian stocks
    """
    
    def __init__(self):
        self.holdings = {}  # {ticker: {'qty': int, 'cost': float, 'date': str}}
    
    def add_stock(self, ticker: str, quantity: float, purchase_price: float, 
                  purchase_date: str):
        """Add stock holding"""
        self.holdings[ticker] = {
            'quantity': quantity,
            'purchase_price': purchase_price,
            'purchase_date': purchase_date,
            'current_price': None
        }
    
    def fetch_current_prices(self, tickers: List[str]) -> Dict:
        """
        Fetch current prices for multiple tickers
        
        Indian stocks use .NS (NSE) and .BO (BSE) suffixes
        Example: 'RELIANCE.NS', 'TCS.NS', 'INFY.NS'
        """
        prices = {}
        
        try:
            data = yf.download(tickers, period='1d', progress=False, group_by='ticker')
            
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    current_price = stock.info.get('currentPrice')
                    prices[ticker] = {
                        'price': current_price,
                        'market_cap': stock.info.get('marketCap'),
                        'pe_ratio': stock.info.get('trailingPE'),
                        'change_percent': stock.info.get('regularMarketChangePercent'),
                        '52_week_high': stock.info.get('fiftyTwoWeekHigh'),
                        '52_week_low': stock.info.get('fiftyTwoWeekLow'),
                    }
                except Exception as e:
                    print(f"Error fetching {ticker}: {e}")
        
        except Exception as e:
            print(f"Error downloading data: {e}")
        
        return prices
    
    def calculate_portfolio_metrics(self) -> Dict:
        """Calculate portfolio gains, losses, and allocations"""
        tickers = list(self.holdings.keys())
        if not tickers:
            return {}
        
        prices = self.fetch_current_prices(tickers)
        
        total_invested = 0
        total_current = 0
        holdings_detail = {}
        
        for ticker, holding in self.holdings.items():
            invested_value = holding['purchase_price'] * holding['quantity']
            current_price = prices.get(ticker, {}).get('price', holding['purchase_price'])
            current_value = current_price * holding['quantity']
            
            gain_loss = current_value - invested_value
            gain_loss_percent = (gain_loss / invested_value * 100) if invested_value > 0 else 0
            
            total_invested += invested_value
            total_current += current_value
            
            holdings_detail[ticker] = {
                'quantity': holding['quantity'],
                'purchase_price': holding['purchase_price'],
                'current_price': current_price,
                'invested_value': invested_value,
                'current_value': current_value,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent,
                'allocation_percent': (current_value / total_current * 100) if total_current > 0 else 0
            }
        
        return {
            'total_invested': total_invested,
            'total_current': total_current,
            'total_gain_loss': total_current - total_invested,
            'total_gain_loss_percent': ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0,
            'holdings': holdings_detail
        }
    
    def get_stock_analysis(self, ticker: str, period: str = '1y') -> Dict:
        """Get detailed stock analysis with technical data"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            # Calculate simple moving averages
            hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
            hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
            
            return {
                'ticker': ticker,
                'name': stock.info.get('longName'),
                'sector': stock.info.get('sector'),
                'industry': stock.info.get('industry'),
                'current_price': stock.info.get('currentPrice'),
                'previous_close': stock.info.get('previousClose'),
                'open_price': stock.info.get('open'),
                'day_high': stock.info.get('dayHigh'),
                'day_low': stock.info.get('dayLow'),
                '52_week_high': stock.info.get('fiftyTwoWeekHigh'),
                '52_week_low': stock.info.get('fiftyTwoWeekLow'),
                'market_cap': stock.info.get('marketCap'),
                'volume': stock.info.get('volume'),
                'pe_ratio': stock.info.get('trailingPE'),
                'dividend_yield': stock.info.get('dividendYield'),
                'earnings_growth': stock.info.get('earningsGrowth'),
                'historical_data': hist.to_dict()
            }
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            return {}


# ============================================================================
# 3. MUTUAL FUND SERVICE - MFAPI.IN INTEGRATION
# ============================================================================

class MutualFundService:
    """
    Manage mutual fund holdings using mfapi.in (free Indian MF data API)
    """
    
    def __init__(self):
        self.mf_api_url = "https://api.mfapi.in/mf"
        self.holdings = {}  # {scheme_code: {units, nav, amount_invested}}
    
    def get_all_schemes(self) -> List[Dict]:
        """Fetch all available mutual fund schemes"""
        try:
            response = requests.get(f"{self.mf_api_url}/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching schemes: {e}")
            return []
    
    def search_scheme(self, scheme_name: str) -> Optional[Dict]:
        """Search for a specific scheme"""
        schemes = self.get_all_schemes()
        
        for scheme_code, scheme_data in schemes.items():
            if scheme_name.lower() in scheme_data.get('schemeName', '').lower():
                return {
                    'scheme_code': scheme_code,
                    'scheme_name': scheme_data.get('schemeName')
                }
        return None
    
    def get_scheme_nav_history(self, scheme_code: str) -> List[Dict]:
        """Fetch NAV history for a scheme"""
        try:
            response = requests.get(f"{self.mf_api_url}/{scheme_code}")
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('nav', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching NAV: {e}")
            return []
    
    def add_holding(self, scheme_code: str, units: float, amount_invested: float):
        """Add mutual fund holding"""
        nav_history = self.get_scheme_nav_history(scheme_code)
        latest_nav = float(nav_history[0]['nav']) if nav_history else 0
        
        self.holdings[scheme_code] = {
            'units': units,
            'amount_invested': amount_invested,
            'current_nav': latest_nav,
            'purchase_date': datetime.now().isoformat()
        }
    
    def calculate_portfolio_metrics(self) -> Dict:
        """Calculate MF portfolio gains and performance"""
        total_invested = 0
        total_current = 0
        holdings_detail = {}
        
        for scheme_code, holding in self.holdings.items():
            current_value = holding['units'] * holding['current_nav']
            gain_loss = current_value - holding['amount_invested']
            gain_loss_percent = (gain_loss / holding['amount_invested'] * 100) if holding['amount_invested'] > 0 else 0
            
            total_invested += holding['amount_invested']
            total_current += current_value
            
            holdings_detail[scheme_code] = {
                'units': holding['units'],
                'nav': holding['current_nav'],
                'amount_invested': holding['amount_invested'],
                'current_value': current_value,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent
            }
        
        return {
            'total_invested': total_invested,
            'total_current': total_current,
            'total_gain_loss': total_current - total_invested,
            'total_gain_loss_percent': ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0,
            'holdings': holdings_detail
        }
    
    def calculate_sip_returns(self, scheme_code: str, monthly_amount: float, months: int) -> Dict:
        """Calculate SIP (Systematic Investment Plan) returns"""
        nav_history = self.get_scheme_nav_history(scheme_code)
        
        if len(nav_history) < months:
            return {"error": f"Insufficient data. Only {len(nav_history)} months available"}
        
        total_invested = monthly_amount * months
        units_purchased = 0
        
        # Simulate monthly investments
        for i in range(min(months, len(nav_history))):
            nav = float(nav_history[i]['nav'])
            units_purchased += monthly_amount / nav
        
        latest_nav = float(nav_history[0]['nav'])
        current_value = units_purchased * latest_nav
        gain = current_value - total_invested
        gain_percent = (gain / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'monthly_investment': monthly_amount,
            'total_invested': total_invested,
            'units_purchased': units_purchased,
            'current_nav': latest_nav,
            'current_value': current_value,
            'gain': gain,
            'gain_percent': gain_percent,
            'xirr_estimate': self._estimate_xirr(current_value, total_invested, months)
        }
    
    @staticmethod
    def _estimate_xirr(current_value: float, total_invested: float, months: int) -> float:
        """Rough XIRR estimate (simplified calculation)"""
        if total_invested == 0 or months == 0:
            return 0
        
        total_return = (current_value - total_invested) / total_invested
        annual_return = ((1 + total_return) ** (12 / months) - 1) * 100
        return annual_return


# ============================================================================
# 4. UNIFIED PORTFOLIO SERVICE - COMBINES ALL ASSETS
# ============================================================================

class FinanceTrackerDashboard:
    """
    Main dashboard service combining bank accounts, stocks, and MF
    """
    
    def __init__(self, finbox_api_key: str):
        self.bank_service = BankAggregatorService(finbox_api_key, "")
        self.stock_service = StockPortfolioService()
        self.mf_service = MutualFundService()
    
    def get_net_worth(self) -> Dict:
        """Calculate total net worth across all assets"""
        
        # Get bank balance
        bank_balance = 0  # Would fetch from bank_service in real implementation
        
        # Get stock portfolio value
        stock_metrics = self.stock_service.calculate_portfolio_metrics()
        stock_value = stock_metrics.get('total_current', 0)
        
        # Get MF portfolio value
        mf_metrics = self.mf_service.calculate_portfolio_metrics()
        mf_value = mf_metrics.get('total_current', 0)
        
        total_net_worth = bank_balance + stock_value + mf_value
        
        return {
            'bank_balance': bank_balance,
            'stock_portfolio_value': stock_value,
            'mf_portfolio_value': mf_value,
            'total_net_worth': total_net_worth,
            'asset_allocation': {
                'bank_percent': (bank_balance / total_net_worth * 100) if total_net_worth > 0 else 0,
                'stocks_percent': (stock_value / total_net_worth * 100) if total_net_worth > 0 else 0,
                'mf_percent': (mf_value / total_net_worth * 100) if total_net_worth > 0 else 0
            }
        }
    
    def get_portfolio_performance(self) -> Dict:
        """Get combined portfolio performance"""
        stock_metrics = self.stock_service.calculate_portfolio_metrics()
        mf_metrics = self.mf_service.calculate_portfolio_metrics()
        
        total_invested = stock_metrics.get('total_invested', 0) + mf_metrics.get('total_invested', 0)
        total_current = stock_metrics.get('total_current', 0) + mf_metrics.get('total_current', 0)
        total_gain = total_current - total_invested
        
        return {
            'total_invested': total_invested,
            'total_current': total_current,
            'total_gain': total_gain,
            'total_gain_percent': (total_gain / total_invested * 100) if total_invested > 0 else 0,
            'stock_details': stock_metrics,
            'mf_details': mf_metrics
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    
    # Initialize dashboard
    dashboard = FinanceTrackerDashboard(finbox_api_key="your_api_key_here")
    
    # ---- STOCK PORTFOLIO EXAMPLE ----
    print("=" * 60)
    print("STOCK PORTFOLIO SETUP")
    print("=" * 60)
    
    # Add stocks
    dashboard.stock_service.add_stock("RELIANCE.NS", 10, 2500, "2023-01-15")
    dashboard.stock_service.add_stock("TCS.NS", 5, 3500, "2023-03-20")
    dashboard.stock_service.add_stock("INFY.NS", 8, 1800, "2023-06-10")
    
    # Get portfolio metrics
    stock_metrics = dashboard.stock_service.calculate_portfolio_metrics()
    print(f"\nStock Portfolio:")
    print(f"Total Invested: ₹{stock_metrics.get('total_invested', 0):,.2f}")
    print(f"Current Value: ₹{stock_metrics.get('total_current', 0):,.2f}")
    print(f"Gain/Loss: ₹{stock_metrics.get('total_gain_loss', 0):,.2f}")
    print(f"Return %: {stock_metrics.get('total_gain_loss_percent', 0):.2f}%")
    
    # ---- MUTUAL FUND EXAMPLE ----
    print("\n" + "=" * 60)
    print("MUTUAL FUND PORTFOLIO SETUP")
    print("=" * 60)
    
    # Add MF holdings (example scheme codes)
    dashboard.mf_service.add_holding("119551", 100, 150000)  # Axis Midcap Fund
    dashboard.mf_service.add_holding("102170", 50, 120000)   # ICICI Prudential Growth Fund
    
    # Get MF portfolio metrics
    mf_metrics = dashboard.mf_service.calculate_portfolio_metrics()
    print(f"\nMF Portfolio:")
    print(f"Total Invested: ₹{mf_metrics.get('total_invested', 0):,.2f}")
    print(f"Current Value: ₹{mf_metrics.get('total_current', 0):,.2f}")
    print(f"Gain/Loss: ₹{mf_metrics.get('total_gain_loss', 0):,.2f}")
    
    # ---- NET WORTH CALCULATION ----
    print("\n" + "=" * 60)
    print("CONSOLIDATED NET WORTH")
    print("=" * 60)
    
    net_worth = dashboard.get_net_worth()
    print(f"\nNet Worth Summary:")
    print(f"Stock Portfolio: ₹{net_worth.get('stock_portfolio_value', 0):,.2f}")
    print(f"MF Portfolio: ₹{net_worth.get('mf_portfolio_value', 0):,.2f}")
    print(f"Bank Balance: ₹{net_worth.get('bank_balance', 0):,.2f}")
    print(f"Total Net Worth: ₹{net_worth.get('total_net_worth', 0):,.2f}")
    
    print(f"\nAsset Allocation:")
    alloc = net_worth.get('asset_allocation', {})
    print(f"Stocks: {alloc.get('stocks_percent', 0):.1f}%")
    print(f"Mutual Funds: {alloc.get('mf_percent', 0):.1f}%")
    print(f"Cash: {alloc.get('bank_percent', 0):.1f}%")
