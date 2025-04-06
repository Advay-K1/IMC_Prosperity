from collections import deque
from datamodel import Order, TradingState
from typing import List
import numpy as np

class Strategy:
    def __init__(self, symbol: str, limit: int) -> None:
        self.symbol = symbol
        self.limit = limit

    def run(self, state: TradingState) -> list[Order]:
        self.orders = []
        return self.act(state)

    def buy(self, price: int, quantity: int) -> None:
        self.orders.append(Order(self.symbol, int(price), quantity))

    def sell(self, price: int, quantity: int) -> None:
        self.orders.append(Order(self.symbol, int(price), -quantity))


class ResinStrategy(Strategy):
    def __init__(self, symbol: str, limit: int) -> None:
        super().__init__(symbol, limit)

    def get_true_value(self, state: TradingState) -> int:
       return 10000

    def act(self, state: TradingState) -> list[Order]:
        order_depth = state.order_depths[self.symbol]
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        true_value = self.get_true_value(state)

        buy_orders = sorted(order_depth.buy_orders.items(), reverse=True)
        sell_orders = sorted(order_depth.sell_orders.items())

        position = state.position.get(self.symbol, 0)
        potential_buy = self.limit - position
        potential_sell = self.limit + position

        max_buy_price = true_value - 1 if position > 0.5 * self.limit else true_value
        min_sell_price = true_value + 1 if position < -0.5 * self.limit else true_value

        # BUY 
        for price, volume in sell_orders:
            if potential_buy > 0 and price <= max_buy_price:
                quantity = min(potential_buy, volume)
                self.buy(price, quantity)
                potential_buy -= quantity


        # SELL 
        for price, volume in buy_orders:
            if potential_sell > 0 and price >= min_sell_price:
                quantity = min(potential_sell, volume)
                self.sell(price, quantity)
                potential_sell -= quantity

        # fall back buy
        if potential_buy > 0:
            popular_buy_price = max(buy_orders, key=lambda tup: tup[1])[0]
            price = min(max_buy_price, popular_buy_price + 1)
            quantity = min(potential_buy, self.limit - position)
            if quantity > 0:
                self.buy(price, quantity)

        # fall back sell
        if potential_sell > 0:
            popular_sell_price = min(sell_orders, key=lambda tup: tup[1])[0]
            price = max(min_sell_price, popular_sell_price - 1)
            quantity = min(potential_sell, self.limit + position)
            if quantity > 0:
                self.sell(price, quantity)

        return self.orders


#volatile
class KelpStrategy(Strategy):
    def __init__(self, symbol: str, limit: int, T: int = 20000, gamma: float = 0.0001, kappa: float = 0.345, sigma_window: int = 4) -> None:
        super().__init__(symbol, limit)
        self.symbol = symbol
        self.T = T
        self.gamma = gamma
        self.kappa = kappa
        self.sigma_window = sigma_window
        self.prices = deque(maxlen=sigma_window)
        self.inventory = 0
        self.cash = 0
        self.tick = 0


    def compute_sigma(self):
        if len(self.prices) < 2:
            return 0.1  # minimum volatility
        return np.std(np.diff(np.array(self.prices)))

    def act(self, state: TradingState) -> list[Order]:
        self.tick += 100

        order_depth = state.order_depths[self.symbol]
        position = state.position.get(self.symbol, 0)
        self.inventory = position  # sync with live position

        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)

        if best_bid is None or best_ask is None:
            return []

        mid_price = (best_bid + best_ask) / 2
        self.prices.append(mid_price)

        sigma_t = self.compute_sigma()
        time_rem = self.T - self.tick

        # Reservation price & optimal spread
        rp_t = mid_price - self.gamma * (sigma_t**2) * time_rem * self.inventory
        spread = self.gamma * sigma_t**2 * time_rem + (2 / self.gamma) * np.log(1 + self.gamma / self.kappa)

        q_bid = rp_t - spread / 2
        q_ask = rp_t + spread / 2

        q_bid = round(q_bid)
        q_ask = round(q_ask)


        potential_buy = self.limit - position
        potential_sell = self.limit + position

        orders = [
            Order(self.symbol, q_bid, max(0,min(potential_buy, 5))),   
            Order(self.symbol, q_ask, max(0,-min(potential_sell, 5))),  
        ]

        buy_qty = max(0, min(potential_buy - 2, 10))
        sell_qty = max(0, -min(potential_sell + 2, 10))

        print(
        f"[KELP] Tick {self.tick} | σ²={sigma_t**2:.5f} | time_rem={time_rem} | inv={self.inventory}\n"
        f"  mid={mid_price:.2f} | rp={rp_t:.2f} | spread={spread:.2f}\n"
        f"  → q_bid={q_bid} ({buy_qty}), q_ask={q_ask} ({sell_qty}) | best_bid={best_bid}, best_ask={best_ask}"
        )

        return orders

class Trader:
    
    def __init__(self) -> None:
    
      # rr is stable while kelp is volatile
      self.limits = { 
          "RAINFOREST_RESIN" : 50,
          "KELP" : 50,  
      }

      strategy_classes = {
          "RAINFOREST_RESIN" : ResinStrategy,
          "KELP" : KelpStrategy,
    
      }

      self.strategies = {
            symbol: strategy_class(symbol, self.limits[symbol])
            for symbol, strategy_class in strategy_classes.items()
      }

    
    
    def run(self, state: TradingState):
        
        
        print(f"[TRADER] Positions: {state.position}")
        result = {}
        # NO CONVERSIONS FIRST ROUND
        CONVERSIONS = 0
        traderData = ""

        for symbol, strategy in self.strategies.items():
            if symbol in state.order_depths:
                orders = strategy.run(state)
                result[symbol] = orders

        return result, CONVERSIONS, traderData

  



 # Default trading algorithm
 # print("traderData: " + state.traderData)
        # print("Observations: " + str(state.observations))

				# # Orders to be placed on exchange matching engine
        # result = {}
        # for product in state.order_depths:
        #     order_depth: OrderDepth = state.order_depths[product]
        #     orders: List[Order] = []
        #     acceptable_price = 10  # Participant should calculate this value
        #     print("Acceptable price : " + str(acceptable_price))
        #     print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
    
        #     if len(order_depth.sell_orders) != 0:
        #         best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
        #         if int(best_ask) < acceptable_price:
        #             print("BUY", str(-best_ask_amount) + "x", best_ask)
        #             orders.append(Order(product, best_ask, -best_ask_amount))

        #     if len(order_depth.buy_orders) != 0:
        #         best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
        #         if int(best_bid) > acceptable_price:
        #             print("SELL", str(best_bid_amount) + "x", best_bid)
        #             orders.append(Order(product, best_bid, -best_bid_amount))
            
        #     result[product] = orders
    
		    # # String value holding Trader state data required. 
				# # It will be delivered as TradingState.traderData on next execution.
        # traderData = "SAMPLE" 
        
				# # Sample conversion request. Check more details below. 
        # CONVERSIONS = 0
        # return result, CONVERSIONS, traderData
                

