from strategies.base import OptionsStrategy
from agents.schemas import TradeProposal, OptionsLeg
from datetime import datetime, timedelta
from data.alpaca_client import AlpacaDataClient

class IronCondorStrategy(OptionsStrategy):
    """
    Constructs an Iron Condor: A defined-risk, delta-neutral strategy 
    designed to profit from IV crush and time decay (Theta).
    
    Consists of:
    - Short Call & Short Put (collect premium)
    - Long Call & Long Put (cap maximum loss)
    """
    def construct_proposal(self) -> TradeProposal:
        client = AlpacaDataClient()
        current_iv, _ = client.get_volatility_metrics(self.symbol, self.current_price)
        contracts = client.get_active_option_chain(self.symbol, self.current_price, current_iv)
        
        target_short_delta = 0.16
        target_long_delta = 0.05
        
        long_put, short_put, short_call, long_call = None, None, None, None
        
        if contracts:
            from datetime import date
            min_date = date.today() + timedelta(days=14)
            filtered_contracts = [c for c in contracts if c['expiration'] >= min_date]
            if filtered_contracts:
                contracts = filtered_contracts
            else:
                # Alpaca Paper Trading often only provides near-term weeklies (0-4 days out).
                # Fallback to the furthest expiration available.
                max_exp = max([c['expiration'] for c in contracts])
                contracts = [c for c in contracts if c['expiration'] == max_exp]
            
        if contracts:
            puts = [c for c in contracts if c['option_type'] == 'put']
            calls = [c for c in contracts if c['option_type'] == 'call']
            
            if puts and calls:
                # Find the option closest to target absolute delta
                sp_cand = min(puts, key=lambda x: abs(abs(x['delta']) - target_short_delta))
                lp_cand = min(puts, key=lambda x: abs(abs(x['delta']) - target_long_delta))
                sc_cand = min(calls, key=lambda x: abs(abs(x['delta']) - target_short_delta))
                lc_cand = min(calls, key=lambda x: abs(abs(x['delta']) - target_long_delta))
                
                sp_strike = sp_cand['strike']
                lp_strike = lp_cand['strike']
                sc_strike = sc_cand['strike']
                lc_strike = lc_cand['strike']
                
                # Match expiration dates to the short put
                base_exp = sp_cand['expiration']
                
                lp_cand = next((p for p in puts if p['strike'] == lp_strike and p['expiration'] == base_exp), None)
                sc_cand = next((c for c in calls if c['strike'] == sc_strike and c['expiration'] == base_exp), None)
                lc_cand = next((c for c in calls if c['strike'] == lc_strike and c['expiration'] == base_exp), None)
                    
                if lp_cand and sc_cand and lc_cand:
                    short_put = OptionsLeg(contract_symbol=sp_cand['contract_symbol'], strike=sp_strike, expiration=base_exp, option_type="put", side="sell", ratio=1)
                    long_put = OptionsLeg(contract_symbol=lp_cand['contract_symbol'], strike=lp_strike, expiration=base_exp, option_type="put", side="buy", ratio=1)
                    short_call = OptionsLeg(contract_symbol=sc_cand['contract_symbol'], strike=sc_strike, expiration=base_exp, option_type="call", side="sell", ratio=1)
                    long_call = OptionsLeg(contract_symbol=lc_cand['contract_symbol'], strike=lc_strike, expiration=base_exp, option_type="call", side="buy", ratio=1)

        if not (long_put and short_put and short_call and long_call):
            expiration = (datetime.utcnow() + timedelta(days=30)).date()
            lp_strike = round(self.current_price * 0.90, 2)
            sp_strike = round(self.current_price * 0.95, 2)
            sc_strike = round(self.current_price * 1.05, 2)
            lc_strike = round(self.current_price * 1.10, 2)
            
            lp_sym = self.generate_osi_symbol(expiration, "put", lp_strike)
            sp_sym = self.generate_osi_symbol(expiration, "put", sp_strike)
            sc_sym = self.generate_osi_symbol(expiration, "call", sc_strike)
            lc_sym = self.generate_osi_symbol(expiration, "call", lc_strike)
            
            long_put = OptionsLeg(contract_symbol=lp_sym, strike=lp_strike, expiration=expiration, option_type="put", side="buy", ratio=1)
            short_put = OptionsLeg(contract_symbol=sp_sym, strike=sp_strike, expiration=expiration, option_type="put", side="sell", ratio=1)
            short_call = OptionsLeg(contract_symbol=sc_sym, strike=sc_strike, expiration=expiration, option_type="call", side="sell", ratio=1)
            long_call = OptionsLeg(contract_symbol=lc_sym, strike=lc_strike, expiration=expiration, option_type="call", side="buy", ratio=1)
            
        legs = [long_put, short_put, short_call, long_call]
        
        # Call the live metrics calculator from the base class
        net_credit, max_loss, delta_exposure = self.calculate_live_metrics(legs, strategy_type="iron_condor")
        
        return TradeProposal(
            proposal_id=self._generate_id(),
            symbol=self.symbol,
            strategy_name="Iron Condor",
            legs=legs,
            net_credit=net_credit,
            max_loss=max_loss,
            iv_rank=self.iv_rank,
            delta_exposure=delta_exposure
        )
