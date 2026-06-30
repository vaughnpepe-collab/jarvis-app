//+------------------------------------------------------------------+
//|                                               JarvisMacroEA.mq5   |
//|   The Macro-Structure Method — a synthesis of the trading edges  |
//|   of Soros, Druckenmiller, Lipschutz, Krieger and TJR.           |
//|                                                                   |
//|   EDUCATIONAL TEMPLATE. Not financial advice. Trading is risky.  |
//|   Backtest and forward-test on a DEMO account before risking     |
//|   real capital. See ../course/ for the full method.              |
//+------------------------------------------------------------------+
#property copyright "Jarvis Trading Course"
#property link      "https://github.com/vaughnpepe-collab/jarvis-app"
#property version   "2.10"
#property description "Macro bias + liquidity sweep + structure shift, with"
#property description "selectable entry models, scale-outs/pyramiding, safety controls"
#property description "and an on-chart status dashboard."
#property strict

#include <Trade/Trade.mqh>

//============================ ENUMS ===============================//
enum ENUM_ENTRY_MODE
{
   ENTRY_BOS_MARKET,   // Market on the break of structure (default)
   ENTRY_FVG_LIMIT     // Limit order into the fair-value-gap retrace (tighter risk)
};

//============================ INPUTS ===============================//

input group "=== Bias (Druckenmiller / Soros: trade with the macro tide) ==="
input ENUM_TIMEFRAMES InpBiasTF        = PERIOD_H4;   // Higher-timeframe for directional bias
input int             InpBiasEMA       = 50;          // EMA period used to read the macro tide
input bool            InpRequireSlope  = true;        // Require the EMA to be sloping in trade direction

input group "=== Structure & Liquidity (TJR / ICT: where price is going) ==="
input ENUM_TIMEFRAMES InpEntryTF       = PERIOD_M15;  // Timeframe the EA executes on
input int             InpSwingLookback = 25;          // Bars scanned for swing highs/lows (liquidity pools)
input int             InpFractalWing   = 2;           // Bars each side that define a swing point
input int             InpSweepWindow   = 3;           // Recent bars in which a liquidity sweep must have occurred

input group "=== Entry model (which variant to trade) ==="
input ENUM_ENTRY_MODE InpEntryMode     = ENTRY_BOS_MARKET; // BOS market, or FVG-retrace limit
input int             InpFVGExpiryBars = 8;           // Cancel an unfilled FVG limit after N bars

input group "=== Risk (Lipschutz / Krieger: survive first, size with conviction) ==="
input double          InpRiskPercent   = 0.5;         // Base risk per trade (% of equity)
input double          InpConvictionMult= 2.0;         // Risk multiplier when ALL filters align ("go for the jugular")
input double          InpMinRR         = 3.0;         // Minimum reward-to-risk to take a trade
input double          InpSLBufferATR   = 0.5;         // Extra stop buffer beyond the sweep, in ATR
input int             InpATRPeriod     = 14;          // ATR period for buffers / volatility
input double          InpMaxRiskPct    = 2.0;         // Hard cap on risk per SINGLE trade (% of equity)

input group "=== Trade management ==="
input bool            InpMoveToBE      = true;        // Move stop to break-even at +1R
input bool            InpTrailAfter1R  = true;        // Trail the stop after +1R (lock the trend in)
input double          InpTrailATR      = 1.5;         // Trailing distance in ATR
input bool            InpUsePartials   = true;        // Scale out part of the position at a profit target
input double          InpPartialR      = 2.0;         // Take partial profit at this R-multiple
input double          InpPartialPct    = 50.0;        // % of the position to close at the partial target

input group "=== Pyramiding (add to winners, never to losers) ==="
input bool            InpAllowPyramid  = false;       // Allow adding on fresh same-direction setups
input int             InpMaxPyramids   = 2;           // Max ADD-ons on top of the first position
input double          InpPyramidRiskMult = 0.5;       // Risk multiplier applied to each add-on
input int             InpMaxPositions  = 1;           // Max positions when pyramiding is OFF

input group "=== Safety: news filter (avoid high-impact releases) ==="
input bool            InpUseNewsFilter = true;        // Block new trades around high-impact news
input bool            InpNewsHighOnly  = true;        // true=High only, false=High+Moderate
input int             InpNewsMinsBefore= 30;          // Minutes BEFORE an event to stop trading
input int             InpNewsMinsAfter = 30;          // Minutes AFTER an event to resume trading

input group "=== Safety: account guards ==="
input double          InpDailyLossLimitPct  = 3.0;    // Stop trading for the day at this % equity loss (0=off)
input bool            InpCloseAllOnDailyLimit = false;// Also flatten everything when the daily limit hits
input double          InpMaxPortfolioRiskPct  = 3.0;  // Cap on TOTAL open risk across positions (0=off)

input group "=== Sessions & filters (trade when liquidity is real) ==="
input bool            InpUseSessions   = true;        // Only trade inside the windows below (server time)
input int             InpSession1Start = 7;           // London open  (server hour)
input int             InpSession1End   = 11;          // London       (server hour)
input int             InpSession2Start = 13;          // New York open(server hour)
input int             InpSession2End   = 17;          // New York     (server hour)
input double          InpMaxSpreadPts  = 30;          // Skip if spread (points) exceeds this
input bool            InpAllowLongs    = true;        // Enable long setups
input bool            InpAllowShorts   = true;        // Enable short setups

input group "=== Bookkeeping ==="
input long            InpMagic         = 920628;      // Magic number (identifies this EA's trades)
input string          InpComment       = "JarvisMacro";

//============================ GLOBALS ==============================//

CTrade   trade;
int      hBiasEMA = INVALID_HANDLE;   // EMA on the bias timeframe
int      hATR     = INVALID_HANDLE;   // ATR on the entry timeframe
datetime lastBarTime = 0;             // for new-bar detection

datetime g_currentDay     = 0;        // anchor for the daily loss limit
double   g_dayStartEquity = 0;

// Per-ticket bookkeeping so break-even/trailing/partials survive an SL move.
ulong    g_riskTickets[];             // tickets we've recorded the original risk for
double   g_riskValues[];              // original |open-SL| per ticket
ulong    g_partialed[];               // tickets that have already been scaled out

// On-chart status / diagnostics.
string   g_setupNote     = "starting up";   // last reason a setup was/ wasn't taken
datetime g_lastSignalTime= 0;               // time of the last order placed
int      g_tradesPlaced  = 0;               // count of orders placed this run

//+------------------------------------------------------------------+
//| Initialisation                                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(20);
   trade.SetTypeFillingBySymbol(_Symbol);

   hBiasEMA = iMA(_Symbol, InpBiasTF, InpBiasEMA, 0, MODE_EMA, PRICE_CLOSE);
   hATR     = iATR(_Symbol, InpEntryTF, InpATRPeriod);

   if(hBiasEMA == INVALID_HANDLE || hATR == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles.");
      return(INIT_FAILED);
   }

   if(InpRiskPercent <= 0 || InpRiskPercent > InpMaxRiskPct)
      Print("WARNING: base risk % is outside a sane range; it will be clamped to ", InpMaxRiskPct, "%.");

   if(InpUseNewsFilter && MQLInfoInteger(MQL_TESTER))
      Print("NOTE: the economic-calendar news filter is inactive in the Strategy Tester.");

   Print("JarvisMacroEA v2 ready on ", _Symbol,
         " | bias=", EnumToString(InpBiasTF),
         " entry=", EnumToString(InpEntryTF),
         " mode=", EnumToString(InpEntryMode));
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Cleanup                                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hBiasEMA != INVALID_HANDLE) IndicatorRelease(hBiasEMA);
   if(hATR     != INVALID_HANDLE) IndicatorRelease(hATR);
   Comment("");   // clear the on-chart dashboard
}

//+------------------------------------------------------------------+
//| Main loop                                                        |
//+------------------------------------------------------------------+
void OnTick()
{
   SyncBookkeeping();                 // drop records for positions that have closed
   ManageOpenPositions();             // break-even / trailing / partials, every tick
   CleanupStalePendings();            // expire unfilled FVG limit orders
   UpdateDayAnchor();

   int    bias  = MacroBias();        // +1 long, -1 short, 0 stand aside
   string block = BlockReason();      // "" if trading is allowed, else why not
   UpdateDashboard(bias, block);      // refresh the on-chart status every tick

   if(InpCloseAllOnDailyLimit && DailyLimitHit())
   {
      CloseAllOwn();                  // flatten and stand down for the day
      return;
   }

   // The decision logic runs once per completed entry-TF bar.
   datetime t = iTime(_Symbol, InpEntryTF, 0);
   if(t == lastBarTime) return;
   lastBarTime = t;

   if(block != "") { g_setupNote = "blocked: " + block; return; }
   if(bias == 0)   { g_setupNote = "no macro bias — standing aside"; return; }

   if(bias > 0 && InpAllowLongs)  TryLong();
   if(bias < 0 && InpAllowShorts) TryShort();
}

//============================ BIAS ================================//
//  Druckenmiller/Soros idea: identify the macro tide on a higher
//  timeframe and only swim with it. Here: price relative to a slow
//  EMA, plus (optionally) the slope of that EMA.
//+------------------------------------------------------------------+
int MacroBias()
{
   double ema[];
   if(CopyBuffer(hBiasEMA, 0, 0, 3, ema) < 3) return 0;

   double closeNow = iClose(_Symbol, InpBiasTF, 1);
   if(closeNow == 0) return 0;

   bool risingEMA  = ema[0] > ema[2];
   bool fallingEMA = ema[0] < ema[2];

   if(closeNow > ema[0] && (!InpRequireSlope || risingEMA))  return  1;
   if(closeNow < ema[0] && (!InpRequireSlope || fallingEMA)) return -1;
   return 0;
}

//===================== SWING / LIQUIDITY =========================//
//  A swing high is a candle whose high is the highest within
//  InpFractalWing bars on each side (a pool of buy-side liquidity).
//  A swing low is the mirror image (sell-side liquidity).
//+------------------------------------------------------------------+
bool FindRecentSwingLow(double &price, int &barIndex)
{
   int w = InpFractalWing;
   for(int i = w + 1; i <= InpSwingLookback; i++)   // skip forming bar; start past the wing
   {
      double low_i = iLow(_Symbol, InpEntryTF, i);
      bool isSwing = true;
      for(int k = 1; k <= w; k++)
      {
         if(iLow(_Symbol, InpEntryTF, i - k) <= low_i ||
            iLow(_Symbol, InpEntryTF, i + k) <= low_i) { isSwing = false; break; }
      }
      if(isSwing) { price = low_i; barIndex = i; return true; }
   }
   return false;
}

bool FindRecentSwingHigh(double &price, int &barIndex)
{
   int w = InpFractalWing;
   for(int i = w + 1; i <= InpSwingLookback; i++)
   {
      double high_i = iHigh(_Symbol, InpEntryTF, i);
      bool isSwing = true;
      for(int k = 1; k <= w; k++)
      {
         if(iHigh(_Symbol, InpEntryTF, i - k) >= high_i ||
            iHigh(_Symbol, InpEntryTF, i + k) >= high_i) { isSwing = false; break; }
      }
      if(isSwing) { price = high_i; barIndex = i; return true; }
   }
   return false;
}

//============================ ENTRIES ============================//
//  LONG model:
//   1) macro bias is up (checked by caller),
//   2) a recent bar SWEPT a swing low (took the sell-side liquidity)
//      and closed back ABOVE it — the stop-hunt that traps sellers,
//   3) price then SHIFTED structure up: the last closed bar broke
//      above the prior swing high (break of structure / CHoCH),
//   4) stop goes below the sweep, target at the next liquidity pool
//      (swing high) and must clear InpMinRR.
//
//  Entry price depends on InpEntryMode: a market order on the BOS, or
//  a limit order into the fair-value gap the impulse left behind.
//+------------------------------------------------------------------+
void TryLong()
{
   if(!CanOpenNew(1)) { g_setupNote = "long: position/pyramid limit reached"; return; }
   if(InpEntryMode == ENTRY_FVG_LIMIT && HasPendingDir(1)) { g_setupNote = "long: FVG limit order already pending"; return; }

   double swingLow; int lowIdx;
   if(!FindRecentSwingLow(swingLow, lowIdx)) { g_setupNote = "long: no swing low found"; return; }

   // (2) Was that low swept inside the recent window, then reclaimed?
   bool swept = false;
   double sweepLow = swingLow;
   for(int i = 1; i <= InpSweepWindow; i++)
   {
      double lo = iLow(_Symbol, InpEntryTF, i);
      double cl = iClose(_Symbol, InpEntryTF, i);
      if(lo < swingLow && cl > swingLow) { swept = true; sweepLow = MathMin(sweepLow, lo); }
   }
   if(!swept) { g_setupNote = "long: waiting for a liquidity sweep"; return; }

   // (3) Structure shift up: last closed bar closes above prior swing high.
   double swingHigh; int highIdx;
   if(!FindRecentSwingHigh(swingHigh, highIdx)) { g_setupNote = "long: no swing high found"; return; }
   if(iClose(_Symbol, InpEntryTF, 1) <= swingHigh) { g_setupNote = "long: swept, waiting for break of structure"; return; }

   double atr = CurrentATR();
   if(atr <= 0) { g_setupNote = "long: ATR not ready"; return; }

   ENUM_ENTRY_MODE mode = InpEntryMode;
   double entry, sl;

   if(mode == ENTRY_FVG_LIMIT)
   {
      // Bullish FVG over the last three closed bars (3,2,1): gap if low[1] > high[3].
      double gapLow  = iHigh(_Symbol, InpEntryTF, 3);
      double gapHigh = iLow(_Symbol, InpEntryTF, 1);
      if(gapHigh > gapLow)
      {
         entry = (gapLow + gapHigh) / 2.0;                 // limit into the gap
         sl    = MathMin(gapLow, sweepLow) - InpSLBufferATR * atr;
      }
      else
      {
         mode  = ENTRY_BOS_MARKET;                         // no clean FVG → take the BOS
         entry = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         sl    = sweepLow - InpSLBufferATR * atr;
      }
   }
   else
   {
      entry = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl    = sweepLow - InpSLBufferATR * atr;
   }

   double risk = entry - sl;
   if(risk <= 0) { g_setupNote = "long: invalid stop distance"; return; }

   double tp = NextLiquidityAbove(swingHigh);              // target the next pool of liquidity
   if((tp - entry) / risk < InpMinRR)
      tp = entry + InpMinRR * risk;                        // else a fixed R-multiple

   bool   isAdd = (CountDir(1) > 0);
   double rmult = ConvictionMultiplier(true) * (isAdd ? InpPyramidRiskMult : 1.0);
   Execute(1, mode, entry, sl, tp, rmult);
}

void TryShort()
{
   if(!CanOpenNew(-1)) { g_setupNote = "short: position/pyramid limit reached"; return; }
   if(InpEntryMode == ENTRY_FVG_LIMIT && HasPendingDir(-1)) { g_setupNote = "short: FVG limit order already pending"; return; }

   double swingHigh; int highIdx;
   if(!FindRecentSwingHigh(swingHigh, highIdx)) { g_setupNote = "short: no swing high found"; return; }

   bool swept = false;
   double sweepHigh = swingHigh;
   for(int i = 1; i <= InpSweepWindow; i++)
   {
      double hi = iHigh(_Symbol, InpEntryTF, i);
      double cl = iClose(_Symbol, InpEntryTF, i);
      if(hi > swingHigh && cl < swingHigh) { swept = true; sweepHigh = MathMax(sweepHigh, hi); }
   }
   if(!swept) { g_setupNote = "short: waiting for a liquidity sweep"; return; }

   double swingLow; int lowIdx;
   if(!FindRecentSwingLow(swingLow, lowIdx)) { g_setupNote = "short: no swing low found"; return; }
   if(iClose(_Symbol, InpEntryTF, 1) >= swingLow) { g_setupNote = "short: swept, waiting for break of structure"; return; }

   double atr = CurrentATR();
   if(atr <= 0) { g_setupNote = "short: ATR not ready"; return; }

   ENUM_ENTRY_MODE mode = InpEntryMode;
   double entry, sl;

   if(mode == ENTRY_FVG_LIMIT)
   {
      // Bearish FVG over bars (3,2,1): gap if high[1] < low[3].
      double gapHigh = iLow(_Symbol, InpEntryTF, 3);
      double gapLow  = iHigh(_Symbol, InpEntryTF, 1);
      if(gapLow < gapHigh)
      {
         entry = (gapLow + gapHigh) / 2.0;
         sl    = MathMax(gapHigh, sweepHigh) + InpSLBufferATR * atr;
      }
      else
      {
         mode  = ENTRY_BOS_MARKET;
         entry = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         sl    = sweepHigh + InpSLBufferATR * atr;
      }
   }
   else
   {
      entry = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = sweepHigh + InpSLBufferATR * atr;
   }

   double risk = sl - entry;
   if(risk <= 0) { g_setupNote = "short: invalid stop distance"; return; }

   double tp = NextLiquidityBelow(swingLow);
   if((entry - tp) / risk < InpMinRR)
      tp = entry - InpMinRR * risk;

   bool   isAdd = (CountDir(-1) > 0);
   double rmult = ConvictionMultiplier(false) * (isAdd ? InpPyramidRiskMult : 1.0);
   Execute(-1, mode, entry, sl, tp, rmult);
}

//  Next opposing liquidity pool used as a natural take-profit.
double NextLiquidityAbove(double fromPrice)
{
   double best = fromPrice;
   for(int i = InpFractalWing + 1; i <= InpSwingLookback * 2; i++)
   {
      double h = iHigh(_Symbol, InpEntryTF, i);
      if(h > best) best = h;
   }
   double extra = CurrentATR();
   return MathMax(best, fromPrice + 2 * extra);
}

double NextLiquidityBelow(double fromPrice)
{
   double best = fromPrice;
   for(int i = InpFractalWing + 1; i <= InpSwingLookback * 2; i++)
   {
      double l = iLow(_Symbol, InpEntryTF, i);
      if(l < best) best = l;
   }
   double extra = CurrentATR();
   return MathMin(best, fromPrice - 2 * extra);
}

//===================== ENTRY PERMISSION ==========================//
//  Pyramiding: add to winners, never to losers, never hedge.
//+------------------------------------------------------------------+
bool CanOpenNew(int dir)
{
   if(CountDir(-dir) > 0) return false;               // never hold both sides at once

   int sameDir = CountDir(dir);
   if(!InpAllowPyramid)
      return sameDir < InpMaxPositions;

   if(sameDir == 0)                  return true;      // first entry
   if(sameDir >= InpMaxPyramids + 1) return false;     // pyramid is full
   return AllInProfit(dir);                            // only add while it's working
}

//========================= CONVICTION ============================//
//  Lipschutz/Krieger: keep base risk small, but when every condition
//  lines up (right session + clean structure) press the advantage.
//+------------------------------------------------------------------+
double ConvictionMultiplier(bool isLong)
{
   double mult = 1.0;
   if(InpUseSessions && InMainSession()) mult = InpConvictionMult;
   return MathMax(1.0, mult);
}

//========================= EXECUTION =============================//
void Execute(int dir, ENUM_ENTRY_MODE mode, double entry, double sl, double tp, double riskMult)
{
   double riskPct = MathMin(InpRiskPercent * riskMult, InpMaxRiskPct);
   double lots    = LotsForRisk(entry, sl, riskPct);
   if(lots <= 0) { Print("Lot sizing returned 0 — trade skipped."); return; }

   lots = ApplyPortfolioCap(entry, sl, lots);         // total-risk guardrail
   if(lots <= 0) { Print("Portfolio risk cap reached — trade skipped."); return; }

   entry = NormalizeDouble(entry, _Digits);
   sl    = NormalizeDouble(sl,    _Digits);
   tp    = NormalizeDouble(tp,    _Digits);

   bool ok;
   if(mode == ENTRY_FVG_LIMIT)
   {
      datetime expiry = TimeTradeServer() + InpFVGExpiryBars * PeriodSeconds(InpEntryTF);
      ok = (dir > 0)
           ? trade.BuyLimit (lots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, InpComment)
           : trade.SellLimit(lots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, InpComment);
   }
   else
   {
      ok = (dir > 0)
           ? trade.Buy (lots, _Symbol, 0.0, sl, tp, InpComment)
           : trade.Sell(lots, _Symbol, 0.0, sl, tp, InpComment);
   }

   if(!ok)
   {
      g_setupNote = "ORDER FAILED: " + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription();
      Print("Order failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   }
   else
   {
      g_tradesPlaced++;
      g_lastSignalTime = TimeCurrent();
      g_setupNote = (dir > 0 ? "LONG " : "SHORT ") + EnumToString(mode) + " placed " + DoubleToString(lots, 2) + " lots";
      Print((dir > 0 ? "LONG " : "SHORT "), EnumToString(mode), " ", lots,
            " lots @~", entry, " SL=", sl, " TP=", tp, " risk%=", riskPct);
   }
}

//  Position sizing from money at risk and stop distance — the single
//  most important function in the whole EA.
double LotsForRisk(double entry, double sl, double riskPct)
{
   double equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * riskPct / 100.0;

   double lossPerLot = LossPerLot(entry, sl);
   if(lossPerLot <= 0) return 0;

   return NormalizeVolume(riskMoney / lossPerLot);
}

//  Money lost per 1.0 lot if the stop is hit.
double LossPerLot(double entry, double sl)
{
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double slDist   = MathAbs(entry - sl);
   if(tickVal <= 0 || tickSize <= 0 || slDist <= 0) return 0;
   return (slDist / tickSize) * tickVal;
}

double NormalizeVolume(double lots)
{
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0) lots = MathFloor(lots / step) * step;
   return MathMax(minLot, MathMin(maxLot, lots));
}

//  Trim a new position so total open risk stays under InpMaxPortfolioRiskPct.
double ApplyPortfolioCap(double entry, double sl, double lots)
{
   if(InpMaxPortfolioRiskPct <= 0) return lots;

   double lossPerLot = LossPerLot(entry, sl);
   if(lossPerLot <= 0) return lots;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double budget = equity * InpMaxPortfolioRiskPct / 100.0 - OpenRiskMoney();
   if(budget <= 0) return 0;

   double maxByBudget = budget / lossPerLot;
   if(lots > maxByBudget) lots = NormalizeVolume(maxByBudget);

   if(lots < SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)) return 0;
   return lots;
}

//  Sum of money at risk across this EA's open positions (entry → stop).
double OpenRiskMoney()
{
   double total = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;

      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double vol  = PositionGetDouble(POSITION_VOLUME);
      if(sl <= 0) continue;                            // no defined risk to add
      total += LossPerLot(open, sl) * vol;
   }
   return total;
}

//===================== POSITION MANAGEMENT =======================//
void ManageOpenPositions()
{
   double atr = CurrentATR();

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;

      long   type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double vol  = PositionGetDouble(POSITION_VOLUME);

      // Original risk is captured the first time we see the ticket, so it
      // stays correct even after we move the stop to break-even.
      double initialRisk = GetInitialRisk(ticket, open, sl);
      if(initialRisk <= 0) continue;

      double price = (type == POSITION_TYPE_BUY)
                     ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                     : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double rMultiple = (type == POSITION_TYPE_BUY)
                         ? (price - open) / initialRisk
                         : (open - price) / initialRisk;

      // --- Partial scale-out (Lipschutz: bank some, ride the rest) ---
      if(InpUsePartials && rMultiple >= InpPartialR && !IsPartialed(ticket))
      {
         double closeVol = NormalizeVolume(vol * InpPartialPct / 100.0);
         double minLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
         if(closeVol >= minLot && (vol - closeVol) >= minLot)
         {
            if(trade.PositionClosePartial(ticket, closeVol))
               Print("Partial close ", closeVol, " lots of #", ticket, " at +", InpPartialR, "R");
         }
         MarkPartialed(ticket);                        // mark either way so we don't retry
         if(!PositionSelectByTicket(ticket)) continue; // position may be gone if it couldn't split
         vol = PositionGetDouble(POSITION_VOLUME);
      }

      // --- Break-even and ATR trailing ---
      double newSL = sl;
      if(type == POSITION_TYPE_BUY)
      {
         if(InpMoveToBE && rMultiple >= 1.0 && (newSL < open || newSL == 0)) newSL = open;
         if(InpTrailAfter1R && rMultiple >= 1.0 && atr > 0)
            newSL = MathMax(newSL, price - InpTrailATR * atr);
         if(newSL > sl + _Point)
            trade.PositionModify(ticket, NormalizeDouble(newSL, _Digits), tp);
      }
      else
      {
         if(InpMoveToBE && rMultiple >= 1.0 && (newSL > open || newSL == 0)) newSL = open;
         if(InpTrailAfter1R && rMultiple >= 1.0 && atr > 0)
            newSL = (newSL == 0) ? price + InpTrailATR * atr
                                 : MathMin(newSL, price + InpTrailATR * atr);
         if((sl == 0 && newSL > 0) || (newSL > 0 && newSL < sl - _Point))
            trade.PositionModify(ticket, NormalizeDouble(newSL, _Digits), tp);
      }
   }
}

//=========================== FILTERS =============================//
//  Returns an empty string if trading is allowed, otherwise a short
//  human-readable reason (shown on the dashboard so you can see WHY
//  the EA is standing aside).
string BlockReason()
{
   if(!MQLInfoInteger(MQL_TESTER) && !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
      return "Algo Trading OFF (toolbar button)";
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
      return "Algo Trading not allowed for this EA";

   double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPts)
      return StringFormat("Spread %.0f > cap %.0f", spread, InpMaxSpreadPts);

   if(InpUseSessions && !InMainSession()) return "Outside session hours (server time)";
   if(DailyLimitHit())                    return "Daily loss limit hit";
   if(NewsBlackout())                     return "High-impact news window";
   return "";
}

bool IsTradingAllowed() { return BlockReason() == ""; }

//  Live on-chart status panel. Top-left of the chart, refreshed every tick.
void UpdateDashboard(int bias, string block)
{
   string biasStr = (bias > 0) ? "LONG only" : (bias < 0) ? "SHORT only" : "neutral (stand aside)";
   string algo    = MQLInfoInteger(MQL_TRADE_ALLOWED) ? "ON" : "OFF";
   double spread  = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double dayPL   = (g_dayStartEquity > 0) ? AccountInfoDouble(ACCOUNT_EQUITY) - g_dayStartEquity : 0.0;
   string state   = (block == "") ? "READY — scanning for setups" : "WAITING — " + block;
   int    openN   = CountDir(1) + CountDir(-1);

   string txt =
      "──────── JarvisMacroEA v2 ────────\n" +
      "STATUS    : ONLINE\n" +
      "           " + state + "\n" +
      "Symbol/TF : " + _Symbol + "  " + EnumToString(InpEntryTF) + "   (mode: " + EnumToString(InpEntryMode) + ")\n" +
      "Algo trade: " + algo + "     Spread: " + DoubleToString(spread, 0) + " / cap " + DoubleToString(InpMaxSpreadPts, 0) + "\n" +
      "Bias (" + EnumToString(InpBiasTF) + "): " + biasStr + "\n" +
      "Session   : " + (InMainSession() ? "IN session" : "out of session") + "\n" +
      "Positions : " + (string)openN + "    Trades this run: " + (string)g_tradesPlaced + "\n" +
      "Day P/L   : " + DoubleToString(dayPL, 2) + " " + AccountInfoString(ACCOUNT_CURRENCY) + "\n" +
      "Last note : " + g_setupNote + "\n" +
      "Last trade: " + (g_lastSignalTime > 0 ? TimeToString(g_lastSignalTime, TIME_DATE | TIME_MINUTES) : "none yet");

   Comment(txt);
}

bool InMainSession()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int h = dt.hour;
   bool s1 = (h >= InpSession1Start && h < InpSession1End);
   bool s2 = (h >= InpSession2Start && h < InpSession2End);
   return (s1 || s2);
}

//  Daily loss limit — anchored to equity at the start of each server day.
void UpdateDayAnchor()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime day = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(day != g_currentDay)
   {
      g_currentDay     = day;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   }
}

bool DailyLimitHit()
{
   if(InpDailyLossLimitPct <= 0 || g_dayStartEquity <= 0) return false;
   double loss  = g_dayStartEquity - AccountInfoDouble(ACCOUNT_EQUITY);
   double limit = g_dayStartEquity * InpDailyLossLimitPct / 100.0;
   return loss >= limit;
}

//  High-impact news blackout via the MT5 economic calendar.
//  (Calendar data is unavailable in the Strategy Tester, so this is a no-op there.)
bool NewsBlackout()
{
   if(!InpUseNewsFilter)          return false;
   if(MQLInfoInteger(MQL_TESTER)) return false;

   datetime now  = TimeTradeServer();
   datetime from = now - InpNewsMinsAfter  * 60;
   datetime to   = now + InpNewsMinsBefore * 60;

   string cur[2];
   cur[0] = SymbolInfoString(_Symbol, SYMBOL_CURRENCY_BASE);
   cur[1] = SymbolInfoString(_Symbol, SYMBOL_CURRENCY_PROFIT);

   for(int c = 0; c < 2; c++)
   {
      if(cur[c] == "") continue;
      MqlCalendarValue values[];
      int n = CalendarValueHistory(values, from, to, "", cur[c]);
      for(int i = 0; i < n; i++)
      {
         MqlCalendarEvent ev;
         if(!CalendarEventById(values[i].event_id, ev)) continue;
         int impFloor = InpNewsHighOnly ? CALENDAR_IMPORTANCE_HIGH : CALENDAR_IMPORTANCE_MODERATE;
         if((int)ev.importance >= impFloor) return true;
      }
   }
   return false;
}

double CurrentATR()
{
   double atr[];
   if(CopyBuffer(hATR, 0, 1, 1, atr) < 1) return 0;
   return atr[0];
}

//======================== COUNTS / STATE =========================//
int CountDir(int dir)   // +1 = buys, -1 = sells (this EA, this symbol)
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if((dir > 0 && type == POSITION_TYPE_BUY) || (dir < 0 && type == POSITION_TYPE_SELL)) n++;
   }
   return n;
}

bool AllInProfit(int dir)
{
   bool any = false;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if((dir > 0 && type != POSITION_TYPE_BUY) || (dir < 0 && type != POSITION_TYPE_SELL)) continue;
      any = true;
      if(PositionGetDouble(POSITION_PROFIT) <= 0) return false;
   }
   return any;
}

bool HasPendingDir(int dir)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)  continue;
      long t = OrderGetInteger(ORDER_TYPE);
      if(dir > 0 && (t == ORDER_TYPE_BUY_LIMIT  || t == ORDER_TYPE_BUY_STOP))  return true;
      if(dir < 0 && (t == ORDER_TYPE_SELL_LIMIT || t == ORDER_TYPE_SELL_STOP)) return true;
   }
   return false;
}

//  Backup expiry: delete unfilled FVG pendings older than InpFVGExpiryBars.
void CleanupStalePendings()
{
   long maxAge = (long)InpFVGExpiryBars * PeriodSeconds(InpEntryTF);
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)  continue;
      datetime setup = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      if(TimeTradeServer() - setup > maxAge)
         trade.OrderDelete(ticket);
   }
}

void CloseAllOwn()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if(OrderGetInteger(ORDER_MAGIC) == InpMagic && OrderGetString(ORDER_SYMBOL) == _Symbol)
         trade.OrderDelete(ticket);
   }
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic && PositionGetString(POSITION_SYMBOL) == _Symbol)
         trade.PositionClose(ticket);
   }
}

//===================== PER-TICKET BOOKKEEPING ====================//
double GetInitialRisk(ulong ticket, double open, double sl)
{
   for(int i = 0; i < ArraySize(g_riskTickets); i++)
      if(g_riskTickets[i] == ticket) return g_riskValues[i];

   double r = MathAbs(open - sl);                       // first sighting → record it
   int n = ArraySize(g_riskTickets);
   ArrayResize(g_riskTickets, n + 1);
   ArrayResize(g_riskValues,  n + 1);
   g_riskTickets[n] = ticket;
   g_riskValues[n]  = r;
   return r;
}

bool IsPartialed(ulong ticket)
{
   for(int i = 0; i < ArraySize(g_partialed); i++)
      if(g_partialed[i] == ticket) return true;
   return false;
}

void MarkPartialed(ulong ticket)
{
   if(IsPartialed(ticket)) return;
   int n = ArraySize(g_partialed);
   ArrayResize(g_partialed, n + 1);
   g_partialed[n] = ticket;
}

//  Drop records for tickets that are no longer open, so the arrays stay small.
void SyncBookkeeping()
{
   PruneList(g_riskTickets, g_riskValues);
   PruneTickets(g_partialed);
}

void PruneList(ulong &tickets[], double &values[])
{
   ulong  kt[]; double kv[]; int kc = 0;
   for(int i = 0; i < ArraySize(tickets); i++)
   {
      if(PositionSelectByTicket(tickets[i]))
      {
         ArrayResize(kt, kc + 1); ArrayResize(kv, kc + 1);
         kt[kc] = tickets[i]; kv[kc] = values[i]; kc++;
      }
   }
   ArrayResize(tickets, kc); ArrayResize(values, kc);
   for(int i = 0; i < kc; i++) { tickets[i] = kt[i]; values[i] = kv[i]; }
}

void PruneTickets(ulong &tickets[])
{
   ulong kt[]; int kc = 0;
   for(int i = 0; i < ArraySize(tickets); i++)
      if(PositionSelectByTicket(tickets[i])) { ArrayResize(kt, kc + 1); kt[kc++] = tickets[i]; }
   ArrayResize(tickets, kc);
   for(int i = 0; i < kc; i++) tickets[i] = kt[i];
}
//+------------------------------------------------------------------+
