from strategies.base import OptionsStrategy
from agents.schemas import TradeProposal, OptionsLeg
from datetime import datetime, timedelta
from data.alpaca_client import AlpacaDataClient

class LongStraddleStrategy(OptionsStrategy):
    """
    Constructs a Long Straddle: A defined-risk, long-volatility strategy
    designed to profit from IV expansion and large price movements.
    
    Consists of:
    - Long ATM Call & Long ATM Put
    """
    def construct_proposal(self) -> TradeProposal:
        client = AlpacaDataClient()
        contracts = client.get_active_option_chain(self.symbol, self.current_price)
        
        atm_strike = round(self.current_price, 0)
        
        long_call = None
        long_put = None
        
        if contracts:
            closest_strike = min([c['strike'] for c in contracts], key=lambda x: abs(x - self.current_price))
            
            calls = [c for c in contracts if c['strike'] == closest_strike and c['option_type'] == 'call']
            puts = [c for c in contracts if c['strike'] == closest_strike and c['option_type'] == 'put']
            
            if calls and puts:
                calls.sort(key=lambda x: x['expiration'])
                puts.sort(key=lambda x: x['expiration'])
                
                front_call = calls[0]
                front_put = next((p for p in puts if p['expiration'] == front_call['expiration']), puts[0])
                
                long_call = OptionsLeg(
                    contract_symbol=front_call['contract_symbol'], 
                    strike=front_call['strike'], 
                    expiration=front_call['expiration'], 
                    option_type="call", 
                    side="buy", 
                    ratio=1
                )
                long_put = OptionsLeg(
                    contract_symbol=front_put['contract_symbol'], 
                    strike=front_put['strike'], 
                    expiration=front_put['expiration'], 
                    option_type="put", 
                    side="buy", 
                    ratio=1
                )
        
        # Fallback to synthetic if Alpaca API returns empty (e.g. no keys)
        if not long_call or not long_put:
            expiration = (datetime.utcnow() + timedelta(days=30)).date()
            long_call = OptionsLeg(contract_symbol=f"{self.symbol}_LONG_CALL", strike=atm_strike, expiration=expiration, option_type="call", side="buy", ratio=1)
            long_put = OptionsLeg(contract_symbol=f"{self.symbol}_LONG_PUT", strike=atm_strike, expiration=expiration, option_type="put", side="buy", ratio=1)
            
        legs = [long_put, long_call]
        
        # Call the live metrics calculator from the base class
        net_credit, max_loss, delta_exposure = self.calculate_live_metrics(legs, strategy_type="straddle")
        
        return TradeProposal(
            proposal_id=self._generate_id(),
            symbol=self.symbol,
            strategy_name="Long Straddle",
            legs=legs,
            net_credit=net_credit,
            max_loss=max_loss,
            iv_rank=self.iv_rank,
            delta_exposure=delta_exposure
        )
