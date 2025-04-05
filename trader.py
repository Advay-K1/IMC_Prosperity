from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

# CLASS HIERARCHY
# Strategy (base)
# └── MarketMakingStrategy (whatever window, liquidity logic we want)
#     ├── ResinStrategy (stable value of 10k)
#     └── KelpStrategy (market midpoint and momentum calculation)

#shared inheirited methods
class Strategy:
    def __init__(self, symbol: str, limit: int) -> None:
        self.symbol = symbol
        self.limit = limit

    def run(self, state: TradingState) -> List[Order]:
        pass

    def load(self, data) -> None:
        pass

    def save(self):
        return None
    
#stable
class ResinStrategy(Strategy):
    def __init__(self, symbol: str, limit: int) -> None:
        super().__init__(symbol, limit)
        self.prices = []
    
    def run(self, state: TradingState) -> List[Order]:
        result = []
        order_depth: OrderDepth = state.order_depths[self.symbol]
        position = state.position.get(self.symbol, 0)

        # Calculate best bid/ask and mid price
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return result

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid_price = (best_bid + best_ask) / 2
        self.prices.append(mid_price)

        mean_price = sum(self.prices) / len(self.prices)
        buy_threshold = mean_price - 1.5
        sell_threshold = mean_price + 1

        # --- BUY if price is low ---
        for ask_price, ask_volume in sorted(order_depth.sell_orders.items()):
            if ask_price <= buy_threshold:
                volume_to_buy = min(ask_volume, self.limit - position)
                if volume_to_buy > 0:
                    result.append(Order(self.symbol, ask_price, volume_to_buy))
                    position += volume_to_buy
                    break

        # --- Fallback buy if stuck and we’re under-positioned ---
            elif position < 0 and ask_price <= mean_price:
                fallback_volume = min(ask_volume, self.limit - position, 1)  # buy back 1 unit
                result.append(Order(self.symbol, ask_price, fallback_volume))
                position += fallback_volume
                break

        # --- SELL if price is high ---
        for bid_price, bid_volume in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid_price >= sell_threshold:
                volume_to_sell = min(bid_volume, self.limit + position)
                if volume_to_sell > 0:
                    result.append(Order(self.symbol, bid_price, -volume_to_sell))
                    position -= volume_to_sell
                    break

        # --- Fallback sell if stuck and we’re over-positioned ---
            elif position > 0 and bid_price >= mean_price:
                fallback_volume = min(bid_volume, self.limit + position, 1)  # sell 1 unit
                result.append(Order(self.symbol, bid_price, -fallback_volume))
                position -= fallback_volume
                break

        return result

#volatile
class KelpStrategy(Strategy):
    def __init__(self, symbol: str, limit: int) -> None:
        super().__init__(symbol, limit)
    
    def run(self, state: TradingState) -> List[Order]:
        return []  # Placeholder for now

class Trader:
    
    def __init__(self) -> None:
    
      # rr is stable while kelp 
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
                

