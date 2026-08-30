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
        contracts = client.get_active_option_chain(self.symbol, self.current_price)
        
        short_put_strike_target = round(self.current_price * 0.95, 2)
        long_put_strike_target = round(self.current_price * 0.90, 2)
        short_call_strike_target = round(self.current_price * 1.05, 2)
        long_call_strike_target = round(self.current_price * 1.10, 2)
        
        long_put, short_put, short_call, long_call = None, None, None, None
        
        if contracts:
            puts = [c for c in contracts if c['option_type'] == 'put']
            calls = [c for c in contracts if c['option_type'] == 'call']
            
            if puts and calls:
                sp_strike = min([p['strike'] for p in puts], key=lambda x: abs(x - short_put_strike_target))
                lp_strike = min([p['strike'] for p in puts], key=lambda x: abs(x - long_put_strike_target))
                sc_strike = min([c['strike'] for c in calls], key=lambda x: abs(x - short_call_strike_target))
                lc_strike = min([c['strike'] for c in calls], key=lambda x: abs(x - long_call_strike_target))
                
                sp_cand = [p for p in puts if p['strike'] == sp_strike]
                
                if sp_cand:
                    sp_cand.sort(key=lambda x: x['expiration'])
                    base_exp = sp_cand[0]['expiration']
                    
                    lp_cand = next((p for p in puts if p['strike'] == lp_strike and p['expiration'] == base_exp), None)
                    sc_cand = next((c for c in calls if c['strike'] == sc_strike and c['expiration'] == base_exp), None)
                    lc_cand = next((c for c in calls if c['strike'] == lc_strike and c['expiration'] == base_exp), None)
                    
                    if lp_cand and sc_cand and lc_cand:
                        short_put = OptionsLeg(contract_symbol=sp_cand[0]['contract_symbol'], strike=sp_strike, expiration=base_exp, option_type="put", side="sell", ratio=1)
                        long_put = OptionsLeg(contract_symbol=lp_cand['contract_symbol'], strike=lp_strike, expiration=base_exp, option_type="put", side="buy", ratio=1)
                        short_call = OptionsLeg(contract_symbol=sc_cand['contract_symbol'], strike=sc_strike, expiration=base_exp, option_type="call", side="sell", ratio=1)
                        long_call = OptionsLeg(contract_symbol=lc_cand['contract_symbol'], strike=lc_strike, expiration=base_exp, option_type="call", side="buy", ratio=1)

        if not (long_put and short_put and short_call and long_call):
            expiration = (datetime.utcnow() + timedelta(days=30)).date()
            long_put = OptionsLeg(contract_symbol=f"{self.symbol}_LONG_PUT", strike=long_put_strike_target, expiration=expiration, option_type="put", side="buy", ratio=1)
            short_put = OptionsLeg(contract_symbol=f"{self.symbol}_SHORT_PUT", strike=short_put_strike_target, expiration=expiration, option_type="put", side="sell", ratio=1)
            short_call = OptionsLeg(contract_symbol=f"{self.symbol}_SHORT_CALL", strike=short_call_strike_target, expiration=expiration, option_type="call", side="sell", ratio=1)
            long_call = OptionsLeg(contract_symbol=f"{self.symbol}_LONG_CALL", strike=long_call_strike_target, expiration=expiration, option_type="call", side="buy", ratio=1)
            
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
