from datamodel import Order, TradingState
import numpy as np
from typing import Dict, List

class Trader:
    def __init__(self):
        self.position_limits = {
            'VOLCANIC_ROCK_VOUCHER_9500': 20,
            'VOLCANIC_ROCK_VOUCHER_9750': 20,
            'VOLCANIC_ROCK_VOUCHER_10000': 20,
            'VOLCANIC_ROCK_VOUCHER_10250': 20,
            'VOLCANIC_ROCK_VOUCHER_10500': 20
        }
        self.price_history = {product: [] for product in self.position_limits}
        self.volatility = {product: 0 for product in self.position_limits}
        self.last_trade = {product: 0 for product in self.position_limits}
        
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders = {}
        conversions = 0
        trader_data = ""
        
        # Update price history and calculate volatility
        for product in self.position_limits:
            if product in state.order_depths:
                best_bid = max(state.order_depths[product].buy_orders.keys())
                best_ask = min(state.order_depths[product].sell_orders.keys())
                mid_price = (best_bid + best_ask) / 2
                
                self.price_history[product].append(mid_price)
                if len(self.price_history[product]) > 5:
                    self.price_history[product].pop(0)
                    returns = np.diff(np.log(self.price_history[product]))
                    self.volatility[product] = np.std(returns) * np.sqrt(252)  # Annualized volatility
                
                # Calculate fair value as 20-day moving average
                fair_value = np.mean(self.price_history[product]) if self.price_history[product] else mid_price
                
                current_position = state.position.get(product, 0)
                spread = best_ask - best_bid
                
                # Dynamic position sizing based on volatility
                max_position = min(
                    self.position_limits[product],
                    int(20 / (1 + self.volatility[product]))
                )
                
                # Mean-reversion trading logic
                if len(self.price_history[product]) >= 3:
                    # Buy when price is below fair value and spread is tight
                    if mid_price < fair_value * 0.99 and spread < fair_value * 0.01:
                        buy_size = min(max_position - current_position, 
                                      state.order_depths[product].sell_orders[best_ask])
                        if buy_size > 0:
                            orders[product] = [Order(product, best_ask, buy_size)]
                            self.last_trade[product] = state.timestamp
                    
                    # Sell when price is above fair value and spread is tight
                    elif mid_price > fair_value * 1.01 and spread < fair_value * 0.01:
                        sell_size = min(max_position + current_position, 
                                       abs(state.order_depths[product].buy_orders[best_bid]))
                        if sell_size > 0:
                            orders[product] = [Order(product, best_bid, -sell_size)]
                            self.last_trade[product] = state.timestamp
                
                # Profit taking - close positions when profitable
                if current_position > 0 and mid_price > fair_value * 1.005:
                    orders[product] = [Order(product, best_bid, -current_position)]
                elif current_position < 0 and mid_price < fair_value * 0.995:
                    orders[product] = [Order(product, best_ask, -current_position)]
                
                # Stop loss - close positions when losing too much
                if current_position > 0 and mid_price < fair_value * 0.99:
                    orders[product] = [Order(product, best_bid, -current_position)]
                elif current_position < 0 and mid_price > fair_value * 1.01:
                    orders[product] = [Order(product, best_ask, -current_position)]
        
        return orders, conversions, trader_data