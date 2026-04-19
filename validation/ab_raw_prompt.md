You are an analyst. Below are signals collected from public sources available before January 2007.
Analyze them for systemic root causes, cluster shared weaknesses,
and prioritize the top interventions under scarcity.

Signals:

Signal 1: Subprime share of new mortgage originations nears one-fifth of the market
Source: inside-mortgage-finance
Type: audit
Body: Trade tallies show subprime production rising from roughly 8 percent of originations in 2003 to nearly 20 percent in 2006 as lenders reach borrowers with thinner credit files, thinner cushions, and weaker documentation.
Labels: Mortgage, Debt, Income

Signal 2: Low-documentation and so-called NINJA loans spread beyond niche programs
Source: broker-channel-survey
Type: field_observation
Body: Mortgage brokers report wider use of loans requiring little verification of borrower pay, work history, or assets, especially in refinance and investor channels.
Labels: Income, Employment, Mortgage

Signal 3: Subprime delinquency and foreclosure starts move higher in late 2006
Source: mortgage-bankers-association
Type: audit
Body: MBA fourth-quarter data show subprime delinquency above 13 percent, with arrears rising fastest on recent vintages as borrowers struggle to meet monthly debt service.
Labels: Arrears, Debt, Mortgage

Signal 4: Large wave of scheduled payment resets due over the next two years
Source: federal-reserve-household-credit
Type: audit
Body: Industry estimates indicate millions of adjustable loans will recast, lifting monthly obligations for borrowers already stretched on carrying costs and thin buffers.
Labels: Housing, Income, Mortgage

Signal 5: Home-price gauges flatten after a long run-up
Source: s-and-p-case-shiller
Type: audit
Body: Case-Shiller and local market reports show several formerly hot metro areas rolling over after peaking in mid-2006, with year-over-year gains narrowing and some markets posting declines.
Labels: Housing, Prices, Market

Signal 6: Months of unsold supply rises as buyer demand softens
Source: national-association-of-realtors
Type: audit
Body: Realtors report a marked rise in the stock of listed properties and longer selling times, suggesting demand is no longer clearing the market at recent levels.
Labels: Housing, Inventory, Sales

Signal 7: Speculative flipping and condo assignment sales remain elevated in boom markets
Source: realtytrac-investor-watch
Type: field_observation
Body: Analysts tracking Las Vegas, Miami, Phoenix, and inland California say investor turnover remains unusually high, leaving these markets exposed if credit terms tighten.
Labels: Housing, Speculation, Investors

Signal 8: Record ownership rate sustained by easier underwriting
Source: census-housing-vacancy-survey
Type: audit
Body: Researchers note the record rate has been supported by looser standards, allowing borrowers with modest resources and little savings to take on larger obligations.
Labels: Housing, Income, Debt

Signal 9: Major dealers operate with leverage ratios that leave little room for error
Source: dealer-balance-sheet-watch
Type: audit
Body: Balance-sheet reviews show several investment banks financing large structured-finance inventories with leverage above 30 to 1, relying on short-term funding and thin common equity.
Labels: Security, Leverage, Funding

Signal 10: Structured-credit issuance climbs past half a trillion dollars in 2006
Source: ifr-structured-credit
Type: audit
Body: Market tallies put CDO issuance above $500 billion for the year as Wall Street packages mortgage risk into ever more complex securities for yield-hungry buyers.
Labels: Security, CDO, Structured Credit

Signal 11: ABX subprime mortgage-backed indexes soften into year-end
Source: abx-market-close
Type: audit
Body: The lower-rated ABX home-equity tranches began to trade down in late 2006, an early sign that buyers are demanding wider spreads on subprime paper.
Labels: Security, ABX, Pricing

Signal 12: Senior tranches backed by subprime collateral continue to win triple-A marks
Source: ratings-industry-watch
Type: audit
Body: Investors and former ratings staff note that pools of weaker loans are still being carved into top-rated paper, leaving many buyers dependent on model assumptions about limited correlation.
Labels: Security, Ratings, Structured Credit

Signal 13: Conduits and SIVs add to off-balance-sheet exposure at major institutions
Source: banking-conduits-monitor
Type: audit
Body: Banks are sponsoring structured investment vehicles and other conduits that hold mortgage paper beyond the main balance sheet, increasing opaque exposure to funding pressure.
Labels: Security, SIV, Funding

Signal 14: FBI says mortgage fraud is becoming an epidemic problem
Source: fbi-press-briefing
Type: incident
Body: Federal investigators warn that misstatement of income, employment, occupancy, and appraisal values is spreading through the mortgage market and could produce broader credit losses.
Labels: Income, Employment, Fraud

Signal 15: Housing correction warnings broaden as a few funds buy protection on subprime paper
Source: market-commentary-roundup
Type: community_report
Body: Public commentary from Robert Shiller and Nouriel Roubini questions the soft-landing view, while a small number of hedge funds are reportedly buying protection against subprime mortgage-backed paper and weaker home finance.
Labels: Housing, Security, Warning

Tasks:
1. What are the shared systemic root causes across these signals?
2. Rank the top 3-5 root causes by severity and breadth.
3. For each root cause, what intervention would address it?
4. What is the most dangerous compounding loop?

Respond with structured JSON containing:
{"root_causes": [{"name": "...", "severity": "...", "signals": [...], "intervention": "...", "predicted_outcome": "..."}]}