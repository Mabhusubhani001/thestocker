import numpy as np

def extract_risk_neutral_probabilities(strikes: list[float], call_prices: list[float]) -> dict[float, float]:
    """
    Extracts the market-implied risk-neutral probability distribution 
    using the Breeden-Litzenberger theorem: P(S > K) = -dC/dK.
    
    Args:
        strikes: A sorted list of strike prices.
        call_prices: The corresponding call option prices (mid-price).
        
    Returns:
        A dictionary mapping strike prices to the implied probability 
        that the underlying stock will expire ABOVE that strike.
    """
    if len(strikes) != len(call_prices) or len(strikes) < 3:
        return {}
        
    # Calculate finite differences for the derivative -dC/dK
    probabilities = {}
    
    # Forward difference for the first element
    dC = call_prices[1] - call_prices[0]
    dK = strikes[1] - strikes[0]
    probabilities[strikes[0]] = max(0.0, min(1.0, -dC / dK if dK != 0 else 0))
    
    # Central difference for interior points
    for i in range(1, len(strikes) - 1):
        dC = call_prices[i+1] - call_prices[i-1]
        dK = strikes[i+1] - strikes[i-1]
        prob = -dC / dK if dK != 0 else 0
        probabilities[strikes[i]] = max(0.0, min(1.0, prob))
        
    # Backward difference for the last element
    dC = call_prices[-1] - call_prices[-2]
    dK = strikes[-1] - strikes[-2]
    probabilities[strikes[-1]] = max(0.0, min(1.0, -dC / dK if dK != 0 else 0))
    
    return probabilities
