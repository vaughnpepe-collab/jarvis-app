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
#property version   "1.00"
#property description "Macro bias + liquidity sweep + structure shift, with asymmetric risk."
#property strict

#include <Trade/Trade.mqh>

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

input group "=== Risk (Lipschutz / Krieger: survive first, size with conviction) ==="
input double          InpRiskPercent   = 0.5;         // Base risk per trade (% of equity)
input double          InpConvictionMult= 2.0;         // Risk multiplier when ALL filters align ("go for the jugular")
input double          InpMinRR         = 3.0;         // Minimum reward-to-risk to take a trade
input double          InpSLBufferATR   = 0.5;         // Extra stop buffer beyond the sweep, in ATR
input int             InpATRPeriod     = 14;          // ATR period for buffers / volatility
input double          InpMaxRiskPct    = 2.0;         // Hard cap on risk per trade (% of equity)

input group "=== Trade management ==="
input bool            InpMoveToBE      = true;        // Move stop to break-even at +1R
input bool            InpTrailAfter1R  = true;        // Trail the stop after +1R (lock the trend in)
input double          InpTrailATR      = 1.5;         // Trailing distance in ATR
input int             InpMaxPositions  = 1;           // Max concurrent positions from this EA

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

   Print("JarvisMacroEA ready on ", _Symbol,
         " | bias=", EnumToString(InpBiasTF),
         " entry=", EnumToString(InpEntryTF));
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Cleanup                                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hBiasEMA != INVALID_HANDLE) IndicatorRelease(hBiasEMA);
   if(hATR     != INVALID_HANDLE) IndicatorRelease(hATR);
}

//+------------------------------------------------------------------+
//| Main loop                                                        |
//+------------------------------------------------------------------+
void OnTick()
{
   // Manage what is already open on every tick (break-even / trailing).
   ManageOpenPositions();

   // The decision logic runs once per completed entry-TF bar.
   datetime t = iTime(_Symbol, InpEntryTF, 0);
   if(t == lastBarTime) return;
   lastBarTime = t;

   if(!IsTradingAllowed()) return;
   if(CountOwnPositions() >= InpMaxPositions) return;

   int bias = MacroBias();           // +1 long, -1 short, 0 stand aside
   if(bias == 0) return;

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
//+------------------------------------------------------------------+
void TryLong()
{
   double swingLow; int lowIdx;
   if(!FindRecentSwingLow(swingLow, lowIdx)) return;

   // (2) Was that low swept inside the recent window, then reclaimed?
   bool swept = false;
   double sweepLow = swingLow;
   for(int i = 1; i <= InpSweepWindow; i++)
   {
      double lo = iLow(_Symbol, InpEntryTF, i);
      double cl = iClose(_Symbol, InpEntryTF, i);
      if(lo < swingLow && cl > swingLow) { swept = true; sweepLow = MathMin(sweepLow, lo); }
   }
   if(!swept) return;

   // (3) Structure shift up: last closed bar closes above prior swing high.
   double swingHigh; int highIdx;
   if(!FindRecentSwingHigh(swingHigh, highIdx)) return;
   double lastClose = iClose(_Symbol, InpEntryTF, 1);
   if(lastClose <= swingHigh) return;   // no break of structure yet

   double atr = CurrentATR();
   if(atr <= 0) return;

   double entry = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl    = sweepLow - InpSLBufferATR * atr;
   // (4) Target the next pool of buy-side liquidity above; ensure it clears min RR.
   double tp    = NextLiquidityAbove(swingHigh);
   double risk  = entry - sl;
   if(risk <= 0) return;
   if((tp - entry) / risk < InpMinRR)
      tp = entry + InpMinRR * risk;     // fall back to a fixed R-multiple target

   double convoy = ConvictionMultiplier(true);
   OpenTrade(ORDER_TYPE_BUY, entry, sl, tp, convoy);
}

void TryShort()
{
   double swingHigh; int highIdx;
   if(!FindRecentSwingHigh(swingHigh, highIdx)) return;

   bool swept = false;
   double sweepHigh = swingHigh;
   for(int i = 1; i <= InpSweepWindow; i++)
   {
      double hi = iHigh(_Symbol, InpEntryTF, i);
      double cl = iClose(_Symbol, InpEntryTF, i);
      if(hi > swingHigh && cl < swingHigh) { swept = true; sweepHigh = MathMax(sweepHigh, hi); }
   }
   if(!swept) return;

   double swingLow; int lowIdx;
   if(!FindRecentSwingLow(swingLow, lowIdx)) return;
   double lastClose = iClose(_Symbol, InpEntryTF, 1);
   if(lastClose >= swingLow) return;

   double atr = CurrentATR();
   if(atr <= 0) return;

   double entry = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl    = sweepHigh + InpSLBufferATR * atr;
   double tp    = NextLiquidityBelow(swingLow);
   double risk  = sl - entry;
   if(risk <= 0) return;
   if((entry - tp) / risk < InpMinRR)
      tp = entry - InpMinRR * risk;

   double convoy = ConvictionMultiplier(false);
   OpenTrade(ORDER_TYPE_SELL, entry, sl, tp, convoy);
}

//  Next opposing liquidity pool used as a natural take-profit.
double NextLiquidityAbove(double fromPrice)
{
   double best = fromPrice;
   for(int i = InpFractalWing + 1; i <= InpSwingLookback * 2; i++)
   {
      double h = iHigh(_Symbol, InpEntryTF, i);
      if(h > best) best = h;             // highest high above = far liquidity target
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

//========================= CONVICTION ============================//
//  Lipschutz/Krieger: keep base risk small, but when every condition
//  lines up (right session + clean structure) press the advantage.
//+------------------------------------------------------------------+
double ConvictionMultiplier(bool isLong)
{
   double mult = 1.0;
   // In a prime session a clean sweep+shift is the A+ setup.
   if(InpUseSessions && InMainSession()) mult = InpConvictionMult;
   return MathMax(1.0, mult);
}

//========================= EXECUTION =============================//
void OpenTrade(ENUM_ORDER_TYPE type, double price, double sl, double tp, double riskMult)
{
   double riskPct = MathMin(InpRiskPercent * riskMult, InpMaxRiskPct);
   double lots    = LotsForRisk(price, sl, riskPct);
   if(lots <= 0) { Print("Lot sizing returned 0 — trade skipped."); return; }

   sl = NormalizeDouble(sl, _Digits);
   tp = NormalizeDouble(tp, _Digits);

   bool ok = (type == ORDER_TYPE_BUY)
             ? trade.Buy(lots, _Symbol, 0.0, sl, tp, InpComment)
             : trade.Sell(lots, _Symbol, 0.0, sl, tp, InpComment);

   if(!ok)
      Print("Order failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   else
      Print((type == ORDER_TYPE_BUY ? "LONG " : "SHORT "), lots, " lots @~", price,
            " SL=", sl, " TP=", tp, " risk%=", riskPct);
}

//  Position sizing from money at risk and stop distance — the single
//  most important function in the whole EA.
double LotsForRisk(double entry, double sl, double riskPct)
{
   double equity   = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney= equity * riskPct / 100.0;

   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0 || tickSize <= 0) return 0;

   double slDist   = MathAbs(entry - sl);
   if(slDist <= 0) return 0;

   double lossPerLot = (slDist / tickSize) * tickVal;   // money lost per 1.0 lot if SL hit
   if(lossPerLot <= 0) return 0;

   double lots = riskMoney / lossPerLot;

   // Snap to the broker's volume constraints.
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0) lots = MathFloor(lots / step) * step;
   lots = MathMax(minLot, MathMin(maxLot, lots));
   return lots;
}

//===================== POSITION MANAGEMENT =======================//
void ManageOpenPositions()
{
   if(!InpMoveToBE && !InpTrailAfter1R) return;
   double atr = CurrentATR();

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      long   type   = PositionGetInteger(POSITION_TYPE);
      double open   = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl     = PositionGetDouble(POSITION_SL);
      double tp     = PositionGetDouble(POSITION_TP);
      double curSL  = sl;

      double price  = (type == POSITION_TYPE_BUY)
                      ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                      : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double initialRisk = MathAbs(open - sl);
      if(initialRisk <= 0) continue;

      if(type == POSITION_TYPE_BUY)
      {
         double rMultiple = (price - open) / initialRisk;
         if(InpMoveToBE && rMultiple >= 1.0 && curSL < open)
            curSL = open;
         if(InpTrailAfter1R && rMultiple >= 1.0 && atr > 0)
            curSL = MathMax(curSL, price - InpTrailATR * atr);
         if(curSL > sl + _Point)
            trade.PositionModify(ticket, NormalizeDouble(curSL, _Digits), tp);
      }
      else
      {
         double rMultiple = (open - price) / initialRisk;
         if(InpMoveToBE && rMultiple >= 1.0 && (curSL > open || curSL == 0))
            curSL = open;
         if(InpTrailAfter1R && rMultiple >= 1.0 && atr > 0)
            curSL = (curSL == 0) ? price + InpTrailATR * atr
                                 : MathMin(curSL, price + InpTrailATR * atr);
         if(curSL < sl - _Point || (sl == 0 && curSL > 0))
            trade.PositionModify(ticket, NormalizeDouble(curSL, _Digits), tp);
      }
   }
}

//=========================== FILTERS =============================//
bool IsTradingAllowed()
{
   if(!MQLInfoInteger(MQL_TESTER) && !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return false;
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;

   double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPts) return false;

   if(InpUseSessions && !InMainSession()) return false;
   return true;
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

double CurrentATR()
{
   double atr[];
   if(CopyBuffer(hATR, 0, 1, 1, atr) < 1) return 0;
   return atr[0];
}

int CountOwnPositions()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         n++;
   }
   return n;
}
//+------------------------------------------------------------------+
