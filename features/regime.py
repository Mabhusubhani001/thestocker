from typing import List

def calculate_iv_rank(current_iv: float, historical_ivs: List[float]) -> float:
    """
    Calculates Implied Volatility Rank (IVR).
    Formula: (Current IV - 52W Low IV) / (52W High IV - 52W Low IV) * 100
    
    Provides deterministic context for the LLM on whether options are currently
    expensive (IVR > 50) or cheap (IVR < 50).
    """
    if not historical_ivs:
        return 50.0  # Default neutral rank if no history is provided
        
    high_iv = max(historical_ivs)
    low_iv = min(historical_ivs)
    
    # Prevent division by zero if volatility was perfectly flat
    if high_iv == low_iv:
        return 50.0
        
    ivr = ((current_iv - low_iv) / (high_iv - low_iv)) * 100.0
    
    # Clamp the result between 0 and 100
    return max(0.0, min(100.0, ivr))
