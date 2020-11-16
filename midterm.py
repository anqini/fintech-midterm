from datetime import timedelta, datetime

class SMAPairsTrading(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2018, 1, 31)   
        self.SetEndDate(2020, 1, 31)
        self.SetCash(100000)
        
        # XOM: market cap 155.853B
        # BP: market cap 64.887B
        symbols = [Symbol.Create("XOM", SecurityType.Equity, Market.USA), Symbol.Create("BP", SecurityType.Equity, Market.USA)]
        
        # V: market cap 466.614B
        # MA: market cap 334.578B
        # symbols = [Symbol.Create("V", SecurityType.Equity, Market.USA), Symbol.Create("MA", SecurityType.Equity, Market.USA)]
        
        # We are limiting our universe of stocks to two for our pair
        # If we wanted to pick a pair from a universe of pairs, you could do that here
        self.AddUniverseSelection(ManualUniverseSelectionModel(symbols))
        
        # This algorithm runs on an hourly basis
        self.UniverseSettings.Resolution = Resolution.Hour
        self.UniverseSettings.DataNormalizationMode = DataNormalizationMode.Raw
        
        # We are creating a custom Alpha here. This is where our pair-trading insight will be defined.
        self.AddAlpha(PairsTradingAlphaModel())
        
        
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        self.SetExecution(ImmediateExecutionModel())
        
    def OnEndOfDay(self, symbol):
        self.Log("Taking a position of " + str(self.Portfolio[symbol].Quantity) + " units of symbol " + str(symbol))

class PairsTradingAlphaModel(AlphaModel):

    def __init__(self):
        self.pair = [ ]
        
        # We will store the running 500 hour average and standard deviation for our Alpha insights
        # These are indicators that we can access - more detail here - https://www.quantconnect.com/docs/algorithm-reference/indicators
        self.spreadMean1 = SimpleMovingAverage(500)
        self.spreadStd1 = StandardDeviation(500)

        self.spreadMean2 = SimpleMovingAverage(2500)
        self.spreadStd2 = StandardDeviation(2500)
        
        # Our insights have a lifespan of 2 hours
        self.period = timedelta(hours=2)
    
    # Run as we receive new data
    def Update(self, algorithm, data):
        spread1 = (self.pair[1].Price - self.pair[0].Price) * 0.9
        
        # Update our indicators by passing algorithm's current time and the current dataset
        self.spreadMean1.Update(algorithm.Time, spread1)
        self.spreadStd1.Update(algorithm.Time, spread1) 
        
        upperthreshold1 = self.spreadMean1.Current.Value + self.spreadStd1.Current.Value
        lowerthreshold1 = self.spreadMean1.Current.Value - 2 * self.spreadStd1.Current.Value
        
        spread2 = self.pair[1].Volume + self.pair[0].Volume
        
        # Update our indicators by passing algorithm's current time and the current dataset
        self.spreadMean2.Update(algorithm.Time, spread2)
        self.spreadStd2.Update(algorithm.Time, spread2) 
        
        lowerthreshold2 = self.spreadMean2.Current.Value - self.spreadStd2.Current.Value

        # If the second asset is greater than 1 standard deviation further from the norm
        if spread1 > upperthreshold1 and spread2 > lowerthreshold2:
            
            # Bullish on the 1st asset
            # Bearish on the 2nd asset
            return Insight.Group(
                [
                    Insight.Price(self.pair[0].Symbol, self.period, InsightDirection.Up),
                    Insight.Price(self.pair[1].Symbol, self.period, InsightDirection.Down)
                ])
        
        if spread1 < lowerthreshold1 and spread2 > lowerthreshold2:
            return Insight.Group(
                [
                    Insight.Price(self.pair[0].Symbol, self.period, InsightDirection.Down),
                    Insight.Price(self.pair[1].Symbol, self.period, InsightDirection.Up)
                ])

        # If no insights, return an empty array
        return []
    
    # When new securities are added. This is called on initialization, and "warms up" our algorithm
    def OnSecuritiesChanged(self, algorithm, changes):
        self.pair = [x for x in changes.AddedSecurities]
        
        #1. Call for 500 bars of history data for each symbol in the pair and save to the variable history
        history = algorithm.History([x.Symbol for x in self.pair], 500)
        #2. Unstack the Pandas data frame to reduce it to the history close price
        history = history.close.unstack(level=0)
        #3. Iterate through the history tuple and update the mean and standard deviation with historical data 
        for tuple in history.itertuples():
            self.spreadMean1.Update(tuple[0], tuple[2]-tuple[1])
            self.spreadStd1.Update(tuple[0], tuple[2]-tuple[1])