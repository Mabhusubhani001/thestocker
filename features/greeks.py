import math
from typing import Dict, Literal

def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-x**2 / 2.0) / math.sqrt(2.0 * math.pi)

def calculate_black_scholes(
    S: float, K: float, T: float, r: float, sigma: float, option_type: Literal["call", "put"]
) -> Dict[str, float]:
    """
    Calculates Option Price and Greeks using the Black-Scholes-Merton model.
    Implemented without heavy external dependencies like SciPy for high performance.
    
    :param S: Underlying price (e.g., $500.00)
    :param K: Strike price (e.g., $510.00)
    :param T: Time to expiration (in years, e.g., 30/365)
    :param r: Risk-free interest rate (e.g., 0.05 for 5%)
    :param sigma: Implied Volatility (e.g., 0.20 for 20%)
    :param option_type: 'call' or 'put'
    :return: Dictionary containing 'price', 'delta', 'gamma', 'theta', 'vega'
    """
    # Handle edge case where option is at or past expiration
    if T <= 0:
        price = max(0.0, S - K) if option_type == "call" else max(0.0, K - S)
        delta = 1.0 if (option_type == "call" and S > K) else (-1.0 if (option_type == "put" and K > S) else 0.0)
        return {"price": price, "delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        delta = norm_cdf(d1)
        # Theta is traditionally represented as decay per day (/365)
        theta = (- (S * sigma * norm_pdf(d1)) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0
    else:
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1.0
        theta = (- (S * sigma * norm_pdf(d1)) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0

    gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
    # Vega is traditionally represented per 1% change in IV (/100)
    vega = S * norm_pdf(d1) * math.sqrt(T) / 100.0

    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega
    }

def calculate_implied_volatility(
    target_price: float, S: float, K: float, T: float, r: float, option_type: Literal["call", "put"], 
    tol: float = 1e-5, max_iter: int = 100
) -> float:
    """
    Calculates Implied Volatility (Sigma) using the Newton-Raphson root-finding method.
    Reverse-engineers the Black-Scholes formula to find the IV that matches the market price.
    """
    if T <= 0 or target_price <= 0:
        return 0.0

    # Initial guess for sigma (50% volatility)
    sigma = 0.50 
    
    for _ in range(max_iter):
        bs_result = calculate_black_scholes(S, K, T, r, sigma, option_type)
        price = bs_result["price"]
        
        # Vega from our function is divided by 100 (for 1% change display). 
        # We need raw Vega (derivative of price with respect to sigma) for Newton-Raphson.
        vega = bs_result["vega"] * 100.0
        
        diff = price - target_price
        
        if abs(diff) < tol:
            return sigma
            
        if vega < 1e-4:
            # If vega is effectively 0 (deep ITM/OTM), Newton-Raphson fails to converge.
            # We break and return the best estimate.
            break
            
        sigma = sigma - (diff / vega)
        
        # Prevent sigma from dropping below 0 or blowing up to infinity
        if sigma <= 0.001:
            sigma = 0.001
        elif sigma > 5.0:
            sigma = 5.0
            
    return sigma
