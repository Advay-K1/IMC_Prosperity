from collections import deque
from datamodel import Order, TradingState
from typing import List

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
        self.window = deque()
        self.window_size = 10

    def get_true_value(self, state: TradingState) -> int:
        order_depth = state.order_depths[self.symbol]
        buy_orders = order_depth.buy_orders
        sell_orders = order_depth.sell_orders

        if not buy_orders or not sell_orders:
            return 10000  # Fallback value

        best_bid = max(buy_orders.keys())
        best_ask = min(sell_orders.keys())
        return round((best_bid + best_ask) / 2)

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

        self.window.append(abs(position) == self.limit)
        if len(self.window) > self.window_size:
            self.window.popleft()

        max_buy_price = true_value - 1 if position > 0.5 * self.limit else true_value
        min_sell_price = true_value + 1 if position < -0.5 * self.limit else true_value

        soft_liquidate = (
            len(self.window) == self.window_size and
            sum(self.window) >= self.window_size / 2 and
            self.window[-1]
        )
        hard_liquidate = (
            len(self.window) == self.window_size and
            all(self.window)
        )

        # BUY logic (walk sell orders)
        for price, volume in sell_orders:
            if potential_buy > 0 and price <= max_buy_price:
                quantity = min(potential_buy, volume)
                self.buy(price, quantity)
                potential_buy -= quantity

        if potential_buy > 0 and hard_liquidate:
            self.buy(true_value, potential_buy // 2)
            potential_buy -= potential_buy // 2

        if potential_buy > 0 and soft_liquidate:
            self.buy(true_value - 2, potential_buy // 2)
            potential_buy -= potential_buy // 2

        if potential_buy > 0:
            popular_buy_price = max(buy_orders, key=lambda tup: tup[1])[0]
            price = min(max_buy_price, popular_buy_price + 1)
            self.buy(price, potential_buy)

        # SELL logic (walk buy orders)
        for price, volume in buy_orders:
            if potential_sell > 0 and price >= min_sell_price:
                quantity = min(potential_sell, volume)
                self.sell(price, quantity)
                potential_sell -= quantity

        if potential_sell > 0 and hard_liquidate:
            self.sell(true_value, potential_sell // 2)
            potential_sell -= potential_sell // 2

        if potential_sell > 0 and soft_liquidate:
            self.sell(true_value + 2, potential_sell // 2)
            potential_sell -= potential_sell // 2

        if potential_sell > 0:
            popular_sell_price = min(sell_orders, key=lambda tup: tup[1])[0]
            price = max(min_sell_price, popular_sell_price - 1)
            self.sell(price, potential_sell)

        return self.orders


#volatile
class KelpStrategy(Strategy):
    def get_true_value(self, state: TradingState) -> int:
        order_depth = state.order_depths[self.symbol]
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return round((best_bid + best_ask) / 2)
    
    def act(self, state: TradingState) -> list[Order]:
        return []


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
                

