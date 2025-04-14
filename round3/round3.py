from datamodel import Order, TradingState
import numpy as np

class Trader:  # Changed from VoucherTrader to Trader
    def __init__(self):
        self.voucher_data = {}
        self.position_limit = 100
        self.time_decay_factors = {
            'VOUCHER_1': 0.95,
            'VOUCHER_2': 0.90,
            'VOUCHER_3': 0.85,
            'VOUCHER_4': 0.80,
            'VOUCHER_5': 0.75
        }
        
    def run(self, state: TradingState):
        orders = {}
        conversions = 0
        trader_data = ""
        
        for product in state.order_depths:
            if "VOUCHER" in product:
                if product not in self.voucher_data:
                    self.initialize_voucher(product, state)
                
                if product in state.market_trades and len(state.market_trades[product]) > 0:
                    best_bid = max(state.order_depths[product].buy_orders.keys())
                    best_ask = min(state.order_depths[product].sell_orders.keys())
                    fair_value = self.calculate_fair_value(product, state)
                    
                    if best_bid > fair_value * 1.05:
                        orders[product] = [Order(product, best_bid, -min(
                            self.position_limit,
                            state.order_depths[product].buy_orders[best_bid]
                        ))]
                    elif best_ask < fair_value * 0.95:
                        orders[product] = [Order(product, best_ask, min(
                            self.position_limit,
                            abs(state.order_depths[product].sell_orders[best_ask])
                        ))]
        
        return orders, conversions, trader_data
    
    def initialize_voucher(self, product, state):
        if product in state.market_trades and len(state.market_trades[product]) > 0:
            self.voucher_data[product] = {
                'strike': state.market_trades[product][-1].price * 0.9,
                'premium': state.market_trades[product][-1].price * 0.1,
                'days_to_expiry': 7
            }
        else:
            # Default values if no market trades exist yet
            self.voucher_data[product] = {
                'strike': 10000 if '10000' in product else 10500 if '10500' in product else 11000 if '11000' in product else 11500 if '11500' in product else 12000,
                'premium': 1000,
                'days_to_expiry': 7
            }
    
    def calculate_fair_value(self, product, state):
        strike = self.voucher_data[product]['strike']
        premium = self.voucher_data[product]['premium']
        days = self.voucher_data[product]['days_to_expiry']
        
        time_factor = self.time_decay_factors.get(product, 0.9) ** (7 - days)
        return strike + (premium * time_factor)