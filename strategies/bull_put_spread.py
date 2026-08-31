from strategies.base import OptionsStrategy
from agents.schemas import TradeProposal, OptionsLeg
from datetime import datetime, timedelta
from data.alpaca_client import AlpacaDataClient

class BullPutSpreadStrategy(OptionsStrategy):
    """
    Constructs a Bull Put Spread: A defined-risk, short-volatility, bullish strategy.
    
    Consists of:
    - Short Put (closer to ATM)
    - Long Put (further OTM)
    """
    def construct_proposal(self) -> TradeProposal:
        client = AlpacaDataClient()
        contracts = client.get_active_option_chain(self.symbol, self.current_price)
        
        target_short_delta = 0.30
        target_long_delta = 0.10
        
        short_put = None
        long_put = None
        
        if contracts:
            from datetime import date
            min_date = date.today() + timedelta(days=14)
            filtered_contracts = [c for c in contracts if c['expiration'] >= min_date]
            if filtered_contracts:
                contracts = filtered_contracts
            else:
                max_exp = max([c['expiration'] for c in contracts])
                contracts = [c for c in contracts if c['expiration'] == max_exp]
            
        if contracts:
            puts = [c for c in contracts if c['option_type'] == 'put']
            if puts:
                closest_short_strike = min([p['strike'] for p in puts], key=lambda x: abs(abs(next((c['delta'] for c in puts if c['strike'] == x), 0)) - target_short_delta))
                closest_long_strike = min([p['strike'] for p in puts], key=lambda x: abs(abs(next((c['delta'] for c in puts if c['strike'] == x), 0)) - target_long_delta))
                
                short_candidates = [p for p in puts if p['strike'] == closest_short_strike]
                long_candidates = [p for p in puts if p['strike'] == closest_long_strike]
                
                if short_candidates and long_candidates:
                    short_candidates.sort(key=lambda x: x['expiration'])
                    short_leg_data = short_candidates[0]
                    # match expiration
                    long_leg_data = next((p for p in long_candidates if p['expiration'] == short_leg_data['expiration']), long_candidates[0])
                    
                    short_put = OptionsLeg(
                        contract_symbol=short_leg_data['contract_symbol'], 
                        strike=short_leg_data['strike'], 
                        expiration=short_leg_data['expiration'], 
                        option_type="put", 
                        side="sell", 
                        ratio=1
                    )
                    long_put = OptionsLeg(
                        contract_symbol=long_leg_data['contract_symbol'], 
                        strike=long_leg_data['strike'], 
                        expiration=long_leg_data['expiration'], 
                        option_type="put", 
                        side="buy", 
                        ratio=1
                    )

        if not short_put or not long_put:
            expiration = (datetime.utcnow() + timedelta(days=30)).date()
            short_strike = round(self.current_price * 0.95, 2)
            long_strike = round(self.current_price * 0.90, 2)
            short_symbol = self.generate_osi_symbol(expiration, "put", short_strike)
            long_symbol = self.generate_osi_symbol(expiration, "put", long_strike)
            short_put = OptionsLeg(contract_symbol=short_symbol, strike=short_strike, expiration=expiration, option_type="put", side="sell", ratio=1)
            long_put = OptionsLeg(contract_symbol=long_symbol, strike=long_strike, expiration=expiration, option_type="put", side="buy", ratio=1)
            
        legs = [long_put, short_put]
        
        # Call the live metrics calculator from the base class
        net_credit, max_loss, delta_exposure = self.calculate_live_metrics(legs, strategy_type="credit_spread")
        
        return TradeProposal(
            proposal_id=self._generate_id(),
            symbol=self.symbol,
            strategy_name="Bull Put Spread",
            legs=legs,
            net_credit=net_credit,
            max_loss=max_loss,
            iv_rank=self.iv_rank,
            delta_exposure=delta_exposure
        )
