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

#volatile
class KelpStrategy(Strategy):
    def __init__(self, symbol: str, limit: int) -> None:
        super().__init__(symbol, limit)

class Trader:
    
    def __init__(self) -> None:
    
      # rr is stable while kelp 
      limits = { 
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


        # NO CONVERSIONS ON FIRST ROUND
        CONVERSIONS = 0
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
                







if __name__ == "__main__":
    trader = Trader()
    trader.run()