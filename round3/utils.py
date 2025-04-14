def calculate_volatility(prices):
    """Calculate historical volatility from price series"""
    returns = np.log(prices[1:]/prices[:-1])
    return np.std(returns) * np.sqrt(252)  # Annualized volatility

def black_scholes(S, K, T, r, sigma, option_type):
    """Basic Black-Scholes option pricing"""
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r*T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return price