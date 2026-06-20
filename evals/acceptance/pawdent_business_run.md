# PawDent Business Simulation

## Institution Charter
**Name:** Pet Care Venture Institution
**Mission:** Launch and operate PawDent for 3 simulated years while improving decisions through verifiable calibration.

## Product Launched
`PawDent`: Monthly dog dental-care kit with dental chews, brushing wipes, breath strips, and a mobile reminder/tracking experience.

## Market Simulator Contract
The market simulator is a deterministic oracle, not an agent. It fabricates market reality only from seed, month, product state, pricing, channel spend, customer satisfaction, competitor pressure, seasonality, supply reliability, and macro shock state. Every monthly actual carries `source_id`, `seed`, `month`, `simulated_date`, and `market_state_hash`.
- Seed: `7319`
- First market_state_hash: `71f98856342f7d811688381f8251e6d2c0e8445005fa9d7672853ed1521b3713`

## Agent Roster
| Team | Agent | Role |
|---|---|---|
| Founder Office | Founder CEO | Sets strategy, approves pivots, and decides whether to continue, raise, cut, or shut down. |
| Market Intelligence Team | Market Research Agent | Requests market studies and identifies customer segments. |
| Product Team | Product Manager | Chooses bundle, roadmap, packaging, and customer promises. |
| Growth Team | Growth Marketer | Chooses channels, creative angle, ad budget, and acquisition targets. |
| Growth Team | Sales & Partnerships Agent | Chooses vet clinics, groomers, pet stores, or D2C focus. |
| Operations Team | Operations Manager | Chooses inventory, suppliers, buffers, fulfillment capacity, and quality controls. |
| Finance Team | Finance Controller | Tracks cash, runway, unit economics, margin, burn, and funding need. |
| Risk & Governance Team | Risk Officer | Blocks circular verification, unsupported confidence, reckless spend, and low-trust decisions. |
| Calibration Office | Calibration Auditor | Pre-registers predictions, resolves them, and updates trust. |
| Learning Office | Learning Agent | Extracts lessons and changes operating policy. |

## What Agent Took What Call?
| Month | Team | Agent | Call type | Rationale |
|---:|---|---|---|---|
| 1 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 1 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 1 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 1 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 1 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 1 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 1 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 1 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 1 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 1 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 1 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 1 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 1 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 1 | Risk & Governance Team | Risk Officer | circular_verification_rejection | same-source verification cannot resolve a market claim |
| 1 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 1 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 1 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 1 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 1 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 1 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 2 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 2 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 2 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 2 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 2 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 2 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 2 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 2 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 2 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 2 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 2 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 2 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 2 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 2 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 2 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 2 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 2 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 2 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 2 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 3 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 3 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 3 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 3 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 3 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 3 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 3 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 3 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 3 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 3 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 3 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 3 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 3 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 3 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 3 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 3 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 3 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 3 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 3 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 4 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 4 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 4 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 4 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 4 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 4 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 4 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 4 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 4 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 4 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 4 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 4 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 4 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 4 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 4 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 4 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 4 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 4 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 4 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 5 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 5 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 5 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 5 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 5 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 5 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 5 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 5 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 5 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 5 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 5 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 5 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 5 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 5 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 5 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 5 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 5 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 5 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 5 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 6 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 6 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 6 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 6 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 6 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 6 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 6 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 6 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 6 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 6 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 6 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 6 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 6 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 6 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 6 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 6 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 6 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 6 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 6 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 7 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 7 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 7 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 7 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 7 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 7 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 7 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 7 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 7 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 7 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 7 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 7 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 7 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 7 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 7 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 7 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 7 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 7 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 7 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 8 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 8 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 8 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 8 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 8 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 8 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 8 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 8 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 8 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 8 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 8 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 8 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 8 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 8 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 8 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 8 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 8 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 8 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 8 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 9 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 9 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 9 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 9 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 9 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 9 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 9 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 9 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 9 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 9 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 9 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 9 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 9 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 9 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 9 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 9 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 9 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 9 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 9 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 10 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 10 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 10 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 10 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 10 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 10 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 10 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 10 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 10 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 10 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 10 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 10 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 10 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 10 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 10 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 10 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 10 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 10 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 10 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 11 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 11 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 11 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 11 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 11 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 11 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 11 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 11 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 11 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 11 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 11 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 11 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 11 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 11 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 11 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 11 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 11 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 11 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 11 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 12 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 12 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 12 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 12 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 12 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 12 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 12 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 12 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 12 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 12 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 12 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 12 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 12 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 12 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 12 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 12 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 12 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 12 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 12 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 13 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 13 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 13 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 13 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 13 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 13 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 13 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 13 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 13 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 13 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 13 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 13 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 13 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 13 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 13 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 13 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 13 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 13 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 13 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 14 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 14 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 14 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 14 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 14 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 14 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 14 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 14 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 14 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 14 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 14 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 14 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 14 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 14 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 14 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 14 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 14 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 14 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 14 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 15 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 15 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 15 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 15 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 15 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 15 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 15 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 15 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 15 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 15 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 15 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 15 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 15 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 15 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 15 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 15 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 15 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 15 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 15 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 16 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 16 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 16 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 16 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 16 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 16 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 16 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 16 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 16 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 16 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 16 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 16 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 16 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 16 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 16 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 16 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 16 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 16 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 16 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 17 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 17 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 17 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 17 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 17 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 17 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 17 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 17 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 17 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 17 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 17 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 17 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 17 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 17 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 17 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 17 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 17 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 17 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 17 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 18 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 18 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 18 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 18 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 18 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 18 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 18 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 18 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 18 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 18 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 18 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 18 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 18 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 18 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 18 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 18 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 18 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 18 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 18 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 19 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 19 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 19 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 19 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 19 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 19 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 19 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 19 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 19 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 19 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 19 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 19 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 19 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 19 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 19 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 19 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 19 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 19 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 19 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 20 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 20 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 20 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 20 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 20 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 20 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 20 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 20 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 20 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 20 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 20 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 20 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 20 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 20 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 20 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 20 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 20 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 20 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 20 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 21 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 21 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 21 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 21 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 21 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 21 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 21 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 21 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 21 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 21 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 21 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 21 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 21 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 21 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 21 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 21 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 21 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 21 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 21 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 22 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 22 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 22 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 22 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 22 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 22 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 22 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 22 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 22 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 22 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 22 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 22 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 22 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 22 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 22 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 22 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 22 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 22 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 22 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 23 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 23 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 23 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 23 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 23 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 23 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 23 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 23 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 23 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 23 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 23 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 23 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 23 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 23 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 23 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 23 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 23 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 23 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 23 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 24 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 24 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 24 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 24 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 24 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 24 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 24 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 24 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 24 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 24 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 24 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 24 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 24 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 24 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 24 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 24 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 24 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 24 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 24 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 25 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 25 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 25 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 25 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 25 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 25 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 25 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 25 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 25 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 25 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 25 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 25 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 25 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 25 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 25 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 25 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 25 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 25 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 25 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 26 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 26 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 26 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 26 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 26 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 26 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 26 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 26 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 26 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 26 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 26 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 26 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 26 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 26 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 26 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 26 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 26 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 26 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 26 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 27 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 27 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 27 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 27 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 27 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 27 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 27 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 27 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 27 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 27 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 27 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 27 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 27 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 27 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 27 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 27 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 27 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 27 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 27 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 28 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 28 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 28 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 28 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 28 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 28 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 28 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 28 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 28 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 28 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 28 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 28 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 28 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 28 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 28 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 28 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 28 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 28 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 28 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 29 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 29 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 29 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 29 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 29 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 29 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 29 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 29 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 29 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 29 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 29 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 29 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 29 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 29 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 29 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 29 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 29 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 29 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 29 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 30 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 30 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 30 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 30 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 30 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 30 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 30 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 30 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 30 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 30 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 30 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 30 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 30 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 30 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 30 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 30 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 30 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 30 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 30 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 31 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 31 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 31 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 31 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 31 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 31 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 31 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 31 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 31 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 31 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 31 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 31 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 31 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 31 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 31 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 31 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 31 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 31 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 31 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 32 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 32 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 32 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 32 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 32 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 32 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 32 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 32 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 32 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 32 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 32 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 32 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 32 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 32 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 32 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 32 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 32 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 32 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 32 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 33 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 33 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 33 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 33 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 33 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 33 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 33 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 33 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 33 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 33 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 33 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 33 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 33 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 33 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 33 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 33 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 33 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 33 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 33 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 34 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 34 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 34 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 34 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 34 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 34 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 34 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 34 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 34 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 34 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 34 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 34 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 34 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 34 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 34 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 34 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 34 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 34 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 34 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 35 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 35 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 35 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 35 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 35 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 35 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 35 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 35 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 35 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 35 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 35 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 35 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 35 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 35 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 35 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 35 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 35 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 35 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 35 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |
| 36 | Market Intelligence Team | Market Research Agent | market_context | read only pre-decision oracle signals; no monthly actuals exposed |
| 36 | Founder Office | Founder CEO | strategy_call | deterministic policy using pre-decision oracle signals and prior resolved months |
| 36 | Product Team | Product Manager | product_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 36 | Growth Team | Growth Marketer | ad_budget_and_channel | deterministic policy using pre-decision oracle signals and prior resolved months |
| 36 | Growth Team | Sales & Partnerships Agent | partnership_decision | deterministic policy using pre-decision oracle signals and prior resolved months |
| 36 | Operations Team | Operations Manager | inventory_and_quality | deterministic policy using pre-decision oracle signals and prior resolved months |
| 36 | Finance Team | Finance Controller | cash_and_unit_economics | deterministic policy using pre-decision oracle signals and prior resolved months |
| 36 | Risk & Governance Team | Risk Officer | risk_approval | deterministic policy using pre-decision oracle signals and prior resolved months |
| 36 | Growth Team | Growth Marketer | pre_registered_claim | claim registered before monthly market actual was revealed |
| 36 | Product Team | Product Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 36 | Finance Team | Finance Controller | pre_registered_claim | claim registered before monthly market actual was revealed |
| 36 | Operations Team | Operations Manager | pre_registered_claim | claim registered before monthly market actual was revealed |
| 36 | Founder Office | Founder CEO | pre_registered_claim | claim registered before monthly market actual was revealed |
| 36 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 36 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 36 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 36 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 36 | Calibration Office | Calibration Auditor | resolve_prediction | resolved against market oracle monthly actual only after preregistration |
| 36 | Learning Office | Learning Agent | learning_update | updated next-month policy from resolved actuals and calibration results |

## 36-Month Timeline
| Month | Date | Phase | Active subscribers | Revenue | Operating profit | Cash | NPS | State hash |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | 2027-01-01 | idea exploration and customer discovery | 53 | 1272.00 | -20813.47 | 229186.53 | 53 | 71f98856342f |
| 2 | 2027-02-01 | idea exploration and customer discovery | 119 | 1800.00 | -20691.47 | 208495.06 | 30 | bccfb7377982 |
| 3 | 2027-03-01 | idea exploration and customer discovery | 171 | 4200.00 | -20369.13 | 188125.93 | 52 | 47a9c0a45a22 |
| 4 | 2027-04-01 | MVP design and pilot | 340 | 9612.00 | -24659.31 | 163466.62 | 51 | 75bb3f38b4a9 |
| 5 | 2027-05-01 | MVP design and pilot | 525 | 14850.00 | -23232.64 | 140233.98 | 59 | 92f6b9a040d4 |
| 6 | 2027-06-01 | MVP design and pilot | 747 | 20250.00 | -22136.48 | 118097.50 | 59 | 21fa0db93f0f |
| 7 | 2027-07-01 | public launch and early growth | 1040 | 30078.00 | -38230.48 | 79867.02 | 56 | 8ed54c2b439f |
| 8 | 2027-08-01 | public launch and early growth | 1319 | 38097.00 | -34788.93 | 45078.09 | 61 | ac74b9121f49 |
| 9 | 2027-09-01 | public launch and early growth | 1595 | 46224.00 | -29702.78 | 15375.31 | 67 | dac45b739cef |
| 10 | 2027-10-01 | public launch and early growth | 1541 | 45387.00 | -14176.55 | 1198.76 | 68 | 1c6339921e57 |
| 11 | 2027-11-01 | public launch and early growth | 1512 | 44091.00 | -14366.43 | -13167.67 | 61 | 40a2b75d348b |
| 12 | 2027-12-01 | public launch and early growth | 1514 | 43632.00 | -14063.46 | -27231.13 | 65 | 74101e290d9d |
| 13 | 2028-01-01 | scaling, retention, partnerships, and product iterations | 1706 | 49086.00 | -21283.90 | -48515.03 | 64 | 65e6ac6d3158 |
| 14 | 2028-02-01 | scaling, retention, partnerships, and product iterations | 1902 | 53892.00 | -21581.45 | -70096.48 | 66 | 081d75059021 |
| 15 | 2028-03-01 | scaling, retention, partnerships, and product iterations | 2105 | 59670.00 | -19045.85 | -89142.33 | 73 | 2bc0f75af9e5 |
| 16 | 2028-04-01 | scaling, retention, partnerships, and product iterations | 2302 | 65340.00 | -17559.22 | -106701.55 | 67 | f9503a7c0c2d |
| 17 | 2028-05-01 | scaling, retention, partnerships, and product iterations | 2466 | 70983.00 | -14909.76 | -121611.31 | 70 | ee75f951f176 |
| 18 | 2028-06-01 | scaling, retention, partnerships, and product iterations | 2569 | 73872.00 | -15365.20 | -136976.51 | 69 | eb165d0c3d22 |
| 19 | 2028-07-01 | scaling, retention, partnerships, and product iterations | 2678 | 76896.00 | -26435.13 | -163411.64 | 73 | a65a465ca288 |
| 20 | 2028-08-01 | scaling, retention, partnerships, and product iterations | 2869 | 81081.00 | -24378.94 | -187790.58 | 70 | c4ae6ca69d6c |
| 21 | 2028-09-01 | scaling, retention, partnerships, and product iterations | 3024 | 85671.00 | -23038.91 | -210829.49 | 73 | b2152644681b |
| 22 | 2028-10-01 | scaling, retention, partnerships, and product iterations | 3156 | 89991.00 | -24372.36 | -235201.85 | 73 | e7221cb3ccb5 |
| 23 | 2028-11-01 | scaling, retention, partnerships, and product iterations | 3316 | 92502.00 | -23213.72 | -258415.57 | 75 | e89f98f4e3bb |
| 24 | 2028-12-01 | scaling, retention, partnerships, and product iterations | 3430 | 97362.00 | -21432.06 | -279847.63 | 73 | 38e402bb437a |
| 25 | 2029-01-01 | maturity, competition, survival, expansion, or shutdown | 3595 | 101088.00 | -21102.60 | -300950.23 | 75 | 306c74aa06fa |
| 26 | 2029-02-01 | maturity, competition, survival, expansion, or shutdown | 3794 | 106596.00 | -18698.73 | -319648.96 | 78 | 2170a9e1d2cb |
| 27 | 2029-03-01 | maturity, competition, survival, expansion, or shutdown | 3971 | 110970.00 | -18500.12 | -338149.08 | 70 | 30c7c7ea076a |
| 28 | 2029-04-01 | maturity, competition, survival, expansion, or shutdown | 4181 | 116721.00 | -23647.92 | -361797.00 | 74 | 2889fa5a0194 |
| 29 | 2029-05-01 | maturity, competition, survival, expansion, or shutdown | 4314 | 121797.00 | -25969.63 | -387766.63 | 74 | 0badd4157864 |
| 30 | 2029-06-01 | maturity, competition, survival, expansion, or shutdown | 4500 | 126171.00 | -13331.14 | -401097.77 | 78 | 48f3e24d7d29 |
| 31 | 2029-07-01 | maturity, competition, survival, expansion, or shutdown | 4678 | 131328.00 | -12310.09 | -413407.86 | 72 | 1cb1dd2ec553 |
| 32 | 2029-08-01 | maturity, competition, survival, expansion, or shutdown | 4874 | 135378.00 | -10357.30 | -423765.16 | 71 | 13e9c6244914 |
| 33 | 2029-09-01 | maturity, competition, survival, expansion, or shutdown | 5050 | 141183.00 | -11072.71 | -434837.87 | 76 | dcdd63b67912 |
| 34 | 2029-10-01 | maturity, competition, survival, expansion, or shutdown | 5226 | 145314.00 | -9433.59 | -444271.46 | 71 | 4251ceae8f81 |
| 35 | 2029-11-01 | maturity, competition, survival, expansion, or shutdown | 5374 | 148743.00 | -10525.79 | -454797.25 | 75 | 90485b38f35a |
| 36 | 2029-12-01 | maturity, competition, survival, expansion, or shutdown | 5520 | 152847.00 | -6374.57 | -461171.82 | 78 | 4e9d57fc6823 |

## Monthly Agent Decision Table
See the call ledger above and `pawdent_agent_decisions.jsonl` for every structured decision event.

## Pre-Registered Claims and Calibration
| Month | Prediction id | Agent | Claim | Outcome | Trust change |
|---:|---|---|---|---|---|
| 1 | `fbbb7688-d551-46a4-9a1a-0ef54208ee57` | Growth Marketer | Month 1 CAC will be <= 38.68. | False | 0.4960->0.4712 |
| 1 | `1caa2d88-7340-430e-a9f0-3f52aa008cc3` | Product Manager | Month 1 conversion rate will be >= 0.0401. | True | 0.4640->0.4408 |
| 1 | `89562ee7-581c-4783-b370-124be13e915b` | Finance Controller | Month 1 gross revenue will be >= 500.00. | True | 0.4800->0.4560 |
| 1 | `8db92b44-263a-4411-9c77-71054643b484` | Operations Manager | Month 1 stockout risk will be <= 0.1000. | True | 0.5120->0.4864 |
| 1 | `a8d1bf15-5dd7-42c3-9699-591f320ebe46` | Founder CEO | Month 1 strategy will improve business health score. | True | 0.4480->0.4256 |
| 2 | `fdace90f-8266-4820-bb0d-9385d3287b5b` | Growth Marketer | Month 2 CAC will be <= 36.38. | False | 0.4712->0.4464 |
| 2 | `a7385460-11da-4247-9e83-acf506004533` | Product Manager | Month 2 conversion rate will be >= 0.0420. | True | 0.4408->0.4176 |
| 2 | `11798647-e3d5-438b-adf2-3593d9e1a640` | Finance Controller | Month 2 gross revenue will be >= 699.60. | True | 0.4560->0.4320 |
| 2 | `d7735c58-c30c-43ed-9083-6cbc2d6f94b4` | Operations Manager | Month 2 stockout risk will be <= 0.1000. | False | 0.4864->0.4608 |
| 2 | `dcd35350-6f50-469c-9e6a-34def0567b9b` | Founder CEO | Month 2 strategy will improve business health score. | False | 0.4256->0.4032 |
| 3 | `780c48a7-9ca6-44f4-afb5-0cfb9ca43a05` | Growth Marketer | Month 3 CAC will be <= 38.61. | False | 0.4464->0.4216 |
| 3 | `be485613-9a7f-450f-a0a7-dd4607239443` | Product Manager | Month 3 conversion rate will be >= 0.0377. | True | 0.4176->0.3944 |
| 3 | `5fd33b55-9da1-4127-bb16-0250bd45b567` | Finance Controller | Month 3 gross revenue will be >= 1570.80. | True | 0.4320->0.4080 |
| 3 | `edec9c55-bcff-403e-9a33-8eb926d4f2bc` | Operations Manager | Month 3 stockout risk will be <= 0.1000. | True | 0.4608->0.4352 |
| 3 | `680959bd-44b3-49b1-9364-b70fed1366c9` | Founder CEO | Month 3 strategy will improve business health score. | True | 0.4032->0.3808 |
| 4 | `3094548f-a82f-46c1-9caa-46c851593fba` | Growth Marketer | Month 4 CAC will be <= 39.83. | False | 0.4216->0.3968 |
| 4 | `890c3727-638d-4ce7-8e09-39511edbb059` | Product Manager | Month 4 conversion rate will be >= 0.0416. | True | 0.3944->0.3712 |
| 4 | `89e0a947-794b-4521-adf6-a117801c20e2` | Finance Controller | Month 4 gross revenue will be >= 3578.85. | True | 0.4080->0.3840 |
| 4 | `de5942e9-4acb-46a8-a955-d5ad8fd64db7` | Operations Manager | Month 4 stockout risk will be <= 0.1000. | True | 0.4352->0.4096 |
| 4 | `e6dd240f-a674-458f-844c-9427b9939a5d` | Founder CEO | Month 4 strategy will improve business health score. | False | 0.3808->0.3584 |
| 5 | `09e1891e-9469-4db0-a016-a88ddc4b573a` | Growth Marketer | Month 5 CAC will be <= 39.72. | False | 0.3968->0.0000 |
| 5 | `02bb3dd3-d074-4110-8a66-e6b67464fb6e` | Product Manager | Month 5 conversion rate will be >= 0.0407. | True | 0.3712->0.0900 |
| 5 | `dd976199-745a-4b36-9e1f-8eded13f2fa7` | Finance Controller | Month 5 gross revenue will be >= 6088.50. | True | 0.3840->0.0900 |
| 5 | `2ac8940f-2b3b-46b5-981d-2be6c79a3589` | Operations Manager | Month 5 stockout risk will be <= 0.1600. | True | 0.4096->0.2800 |
| 5 | `2d611c03-0c1a-4c89-be82-53f55f8a8804` | Founder CEO | Month 5 strategy will improve business health score. | False | 0.3584->0.3584 |
| 6 | `cbc10457-680c-40be-a20b-a9f2aded667f` | Growth Marketer | Month 6 CAC will be <= 42.34. | True | 0.0000->0.0150 |
| 6 | `529c3a28-ace0-48b2-b9e6-3f7815770f5f` | Product Manager | Month 6 conversion rate will be >= 0.0411. | True | 0.0900->0.0900 |
| 6 | `febfa872-d6d6-4f80-ab26-5002db22c2e6` | Finance Controller | Month 6 gross revenue will be >= 8835.75. | True | 0.0900->0.0900 |
| 6 | `df38eb42-6330-4d95-b436-213abf5a449b` | Operations Manager | Month 6 stockout risk will be <= 0.1600. | True | 0.2800->0.1667 |
| 6 | `e64a07aa-4543-463f-90e8-d8a195da8667` | Founder CEO | Month 6 strategy will improve business health score. | False | 0.3584->0.1778 |
| 7 | `bb296f59-28b0-4b3e-9b96-d1c77d4a8e93` | Growth Marketer | Month 7 CAC will be <= 43.15. | True | 0.0150->0.0306 |
| 7 | `bff4c2d9-c34c-465b-a068-cfd0d25ba22a` | Product Manager | Month 7 conversion rate will be >= 0.0407. | True | 0.0900->0.0900 |
| 7 | `ac2d2e7a-7dfe-49fa-9a9c-f5b966d46712` | Finance Controller | Month 7 gross revenue will be >= 13691.70. | True | 0.0900->0.0900 |
| 7 | `bb260a38-d1c3-47d8-9526-50a177bbc501` | Operations Manager | Month 7 stockout risk will be <= 0.1000. | True | 0.1667->0.1359 |
| 7 | `8c3293d5-86af-4ca9-ae7f-2be21e86afac` | Founder CEO | Month 7 strategy will improve business health score. | False | 0.1778->0.0805 |
| 8 | `c83a1a36-e477-420e-b0d4-3535acc12b7d` | Growth Marketer | Month 8 CAC will be <= 35.72. | False | 0.0306->0.0225 |
| 8 | `a58c57a3-81e0-4ea8-91fb-4c8d722df9ed` | Product Manager | Month 8 conversion rate will be >= 0.0435. | True | 0.0900->0.0900 |
| 8 | `2ff2e36b-0213-454f-81f2-b898b4aeff5c` | Finance Controller | Month 8 gross revenue will be >= 18376.88. | True | 0.0900->0.0900 |
| 8 | `fcc2a7a0-ad9c-4c7e-8d42-4b34fade44a7` | Operations Manager | Month 8 stockout risk will be <= 0.1600. | True | 0.1359->0.1247 |
| 8 | `d412be40-fea2-4ba6-bfdb-33f96f596bb2` | Founder CEO | Month 8 strategy will improve business health score. | False | 0.0805->0.0413 |
| 9 | `7eab52dc-0b96-4b0b-96e4-13b8eed1904e` | Growth Marketer | Month 9 CAC will be <= 42.97. | False | 0.0225->0.0200 |
| 9 | `1466cdce-9f4f-4036-bbe7-75df6bba9905` | Product Manager | Month 9 conversion rate will be >= 0.0443. | True | 0.0900->0.0900 |
| 9 | `73ef8205-a243-4e27-aba4-a570732b90da` | Finance Controller | Month 9 gross revenue will be >= 22854.15. | True | 0.0900->0.0900 |
| 9 | `092c5b2e-f5d3-44a3-bb66-027155478bcd` | Operations Manager | Month 9 stockout risk will be <= 0.1600. | True | 0.1247->0.1156 |
| 9 | `f5af8bd6-4a4b-4962-97d6-cc4046c7419c` | Founder CEO | Month 9 strategy will improve business health score. | False | 0.0413->0.0311 |
| 10 | `f20d749e-f6ec-41eb-a327-ef11057c3dd8` | Growth Marketer | Month 10 CAC will be <= 42.69. | True | 0.0200->0.0360 |
| 10 | `d9ea91cb-0a73-4c1b-8f49-51c1d1df5027` | Product Manager | Month 10 conversion rate will be >= 0.0464. | True | 0.0900->0.0900 |
| 10 | `fa4732a4-d4a1-4f63-a00c-39dd91d83320` | Finance Controller | Month 10 gross revenue will be >= 27286.88. | True | 0.0900->0.0900 |
| 10 | `89b9858c-ca12-4cca-bd40-54d45a0b5d91` | Operations Manager | Month 10 stockout risk will be <= 0.1600. | True | 0.1156->0.1080 |
| 10 | `a0c3dac1-1761-4fe3-8632-7fbb150946c6` | Founder CEO | Month 10 strategy will improve business health score. | False | 0.0311->0.0240 |
| 11 | `9157b821-392d-497e-b10d-4129734107ac` | Growth Marketer | Month 11 CAC will be <= 35.97. | True | 0.0360->0.0684 |
| 11 | `900acafe-9e2f-4992-800b-49b978d1332e` | Product Manager | Month 11 conversion rate will be >= 0.0487. | True | 0.0900->0.0900 |
| 11 | `6b9fddc6-a763-49a9-b675-1bdb7b5817ad` | Finance Controller | Month 11 gross revenue will be >= 26819.10. | True | 0.0900->0.0900 |
| 11 | `4f73cb7c-2410-46db-84ec-aa2490ebc387` | Operations Manager | Month 11 stockout risk will be <= 0.1600. | True | 0.1080->0.1017 |
| 11 | `0cb62861-d138-4d61-a26c-9edc071b759d` | Founder CEO | Month 11 strategy will improve business health score. | False | 0.0240->0.0188 |
| 12 | `d4fe0fac-e99d-48ac-b4bd-64b4ca061cea` | Growth Marketer | Month 12 CAC will be <= 40.82. | True | 0.0684->0.1823 |
| 12 | `8d9cb843-08c6-4c47-a872-a71a02ae749b` | Product Manager | Month 12 conversion rate will be >= 0.0439. | True | 0.0900->0.0900 |
| 12 | `fac9423e-cff2-4664-96dc-436f7035de95` | Finance Controller | Month 12 gross revenue will be >= 26722.58. | True | 0.0900->0.0900 |
| 12 | `2dc6b3ad-87d9-4469-a82c-370496354b7f` | Operations Manager | Month 12 stockout risk will be <= 0.1600. | True | 0.1017->0.0963 |
| 12 | `16247455-ba97-4cdd-841f-ff4ea2692b6e` | Founder CEO | Month 12 strategy will improve business health score. | False | 0.0188->0.0150 |
| 13 | `b75ee464-22d6-43b3-9298-0cac0b417e2f` | Growth Marketer | Month 13 CAC will be <= 41.48. | True | 0.1823->0.3298 |
| 13 | `b7fdf14c-87ce-4bc0-848f-12cf6c5ef8a1` | Product Manager | Month 13 conversion rate will be >= 0.0495. | True | 0.0900->0.0900 |
| 13 | `b07cc894-6e07-44f8-9799-9ceab7aa96d2` | Finance Controller | Month 13 gross revenue will be >= 25022.25. | True | 0.0900->0.0900 |
| 13 | `b60352f8-5354-4a89-87f6-a866e4419a9b` | Operations Manager | Month 13 stockout risk will be <= 0.1600. | True | 0.0963->0.0916 |
| 13 | `9556222d-d72f-4e50-9d5b-7f21a7add7de` | Founder CEO | Month 13 strategy will improve business health score. | False | 0.0150->0.0138 |
| 14 | `662e6806-c0be-4859-9ac4-fb151c3322fd` | Growth Marketer | Month 14 CAC will be <= 43.28. | True | 0.3298->0.5000 |
| 14 | `36b40338-5254-4e85-9db1-31ae27e868f5` | Product Manager | Month 14 conversion rate will be >= 0.0486. | True | 0.0900->0.0900 |
| 14 | `8694ab1c-939e-46ff-bc3d-651ac3b3c300` | Finance Controller | Month 14 gross revenue will be >= 27591.30. | True | 0.0900->0.0900 |
| 14 | `142e6da8-8c32-4ec5-8253-2a4a6c7eb33b` | Operations Manager | Month 14 stockout risk will be <= 0.1600. | True | 0.0916->0.0876 |
| 14 | `1c8db6bb-1089-4a7f-9ccc-0ed6decea209` | Founder CEO | Month 14 strategy will improve business health score. | False | 0.0138->0.0129 |
| 15 | `8c7360f8-1f20-4108-8849-46d29893139f` | Growth Marketer | Month 15 CAC will be <= 37.24. | False | 0.5000->0.3500 |
| 15 | `0328126e-ed53-48c2-81f0-20d1479b42f4` | Product Manager | Month 15 conversion rate will be >= 0.0454. | True | 0.0900->0.0900 |
| 15 | `635402b3-b70b-4a69-8677-e73a824019f0` | Finance Controller | Month 15 gross revenue will be >= 30390.53. | True | 0.0900->0.0900 |
| 15 | `e7153c62-638e-40cb-b527-82f2ee74f50d` | Operations Manager | Month 15 stockout risk will be <= 0.1600. | True | 0.0876->0.0840 |
| 15 | `ee633748-e26b-4267-afe2-e2fea0b0a167` | Founder CEO | Month 15 strategy will improve business health score. | False | 0.0129->0.0120 |
| 16 | `0b28fbe7-b08b-4634-b770-506249e91da2` | Growth Marketer | Month 16 CAC will be <= 43.05. | True | 0.3500->0.5000 |
| 16 | `3aa08926-c0c5-438e-8f4b-ecde4e34e4e7` | Product Manager | Month 16 conversion rate will be >= 0.0464. | True | 0.0900->0.0900 |
| 16 | `5d985ad4-ac7f-4ed5-a5b7-5ed74769bd5e` | Finance Controller | Month 16 gross revenue will be >= 33546.15. | True | 0.0900->0.0900 |
| 16 | `60f66243-fd9b-4eae-8f0b-475d227cb878` | Operations Manager | Month 16 stockout risk will be <= 0.1600. | True | 0.0840->0.0844 |
| 16 | `ca8d08a5-54d0-434b-9a2e-1feffb0d2139` | Founder CEO | Month 16 strategy will improve business health score. | False | 0.0120->0.0112 |
| 17 | `a2451f9b-e194-4811-83d1-f4e763cffbea` | Growth Marketer | Month 17 CAC will be <= 42.95. | True | 0.5000->0.5294 |
| 17 | `e272719b-559a-4d12-bf1c-dbb0a3c2e0b7` | Product Manager | Month 17 conversion rate will be >= 0.0471. | True | 0.0900->0.0900 |
| 17 | `9b6034d8-af4b-4f81-a3c1-59255e861ef5` | Finance Controller | Month 17 gross revenue will be >= 36516.15. | True | 0.0900->0.0900 |
| 17 | `49613b50-93c7-4d5e-b3ac-d33f1aa7749b` | Operations Manager | Month 17 stockout risk will be <= 0.1600. | True | 0.0844->0.0847 |
| 17 | `ed96488b-d55b-49b6-a68b-37b9de490567` | Founder CEO | Month 17 strategy will improve business health score. | False | 0.0112->0.0106 |
| 18 | `d57aa199-ff0a-4815-b6f2-6110355b4629` | Growth Marketer | Month 18 CAC will be <= 38.07. | False | 0.5294->0.5000 |
| 18 | `0c1fe276-43b0-4dd0-9b93-0f2c2f5681fe` | Product Manager | Month 18 conversion rate will be >= 0.0477. | True | 0.0900->0.0900 |
| 18 | `fe3b4c75-68c6-4072-bea4-dc410510bd91` | Finance Controller | Month 18 gross revenue will be >= 39040.65. | True | 0.0900->0.0900 |
| 18 | `ff292ac5-2e38-4f70-beec-97296c1f747b` | Operations Manager | Month 18 stockout risk will be <= 0.1600. | True | 0.0847->0.0850 |
| 18 | `b0a106c1-1108-4cf9-b60a-b6839a497454` | Founder CEO | Month 18 strategy will improve business health score. | False | 0.0106->0.0100 |
| 19 | `fddefa2c-7c56-41ff-a9fd-0a86eeba805b` | Growth Marketer | Month 19 CAC will be <= 42.04. | False | 0.5000->0.3789 |
| 19 | `b147217e-5070-4e8a-84cb-6eb5b0454d12` | Product Manager | Month 19 conversion rate will be >= 0.0459. | True | 0.0900->0.0900 |
| 19 | `9419d2d6-e96e-4947-9c47-0156ab533c4b` | Finance Controller | Month 19 gross revenue will be >= 40154.40. | True | 0.0900->0.0900 |
| 19 | `ae45a0b6-1b5a-4540-a6d0-a5120cf66a85` | Operations Manager | Month 19 stockout risk will be <= 0.1600. | True | 0.0850->0.0853 |
| 19 | `609c9e6a-704c-43b6-9e56-dede5233e012` | Founder CEO | Month 19 strategy will improve business health score. | False | 0.0100->0.0095 |
| 20 | `262ddc45-ffc5-47b8-8a92-b0d329ec1da3` | Growth Marketer | Month 20 CAC will be <= 40.82. | True | 0.3789->0.5000 |
| 20 | `541959ac-51cc-4fb9-8e01-8e5bcd571105` | Product Manager | Month 20 conversion rate will be >= 0.0505. | True | 0.0900->0.0900 |
| 20 | `2761ee2c-2760-4155-bf30-a5354f4eb5b0` | Finance Controller | Month 20 gross revenue will be >= 41839.88. | True | 0.0900->0.0900 |
| 20 | `b69e701b-1993-411c-9604-7a9629fc2f3e` | Operations Manager | Month 20 stockout risk will be <= 0.1600. | True | 0.0853->0.0855 |
| 20 | `82f120b8-97b1-4c6c-95dd-f9fdedfe7b36` | Founder CEO | Month 20 strategy will improve business health score. | False | 0.0095->0.0090 |
| 21 | `20931226-091b-4f78-8893-9320bd54dc95` | Growth Marketer | Month 21 CAC will be <= 41.78. | True | 0.5000->0.5238 |
| 21 | `713f85c6-debe-4b0a-b431-b94d56a269a8` | Product Manager | Month 21 conversion rate will be >= 0.0497. | True | 0.0900->0.0900 |
| 21 | `4d03d42d-8da7-4d05-9e03-9e038bf7fe4b` | Finance Controller | Month 21 gross revenue will be >= 45017.78. | True | 0.0900->0.0900 |
| 21 | `c9b70c57-4729-4caa-a992-a1636b269f23` | Operations Manager | Month 21 stockout risk will be <= 0.1600. | True | 0.0855->0.0857 |
| 21 | `5373ac82-3d1e-4198-a99a-11305f2e0f5f` | Founder CEO | Month 21 strategy will improve business health score. | False | 0.0090->0.0086 |
| 22 | `29891e2f-2f7f-4bdc-adcf-6a8137554a14` | Growth Marketer | Month 22 CAC will be <= 46.73. | True | 0.5238->0.5455 |
| 22 | `2451bdc2-e100-4c39-aae2-2ea6a973cd4e` | Product Manager | Month 22 conversion rate will be >= 0.0514. | True | 0.0900->0.0900 |
| 22 | `d74e2fbe-535d-4b14-a04c-39b414fc9739` | Finance Controller | Month 22 gross revenue will be >= 47163.60. | True | 0.0900->0.0900 |
| 22 | `ddaebb7e-fa96-423e-aa9d-f32aa8bd7ba1` | Operations Manager | Month 22 stockout risk will be <= 0.1600. | True | 0.0857->0.0859 |
| 22 | `ec441785-96b4-445d-9fec-c6a0a0373601` | Founder CEO | Month 22 strategy will improve business health score. | False | 0.0086->0.0082 |
| 23 | `835344c2-8a56-4c14-8c09-c4a8b3ef24d4` | Growth Marketer | Month 23 CAC will be <= 41.83. | False | 0.5455->0.5217 |
| 23 | `6e381d6b-6571-479a-bd0e-e8ff8ede3ef0` | Product Manager | Month 23 conversion rate will be >= 0.0502. | True | 0.0900->0.0900 |
| 23 | `2b5efdbd-a68b-4c17-9611-4a668e0a4bd7` | Finance Controller | Month 23 gross revenue will be >= 49160.93. | True | 0.0900->0.0900 |
| 23 | `2fb23fa1-d53a-4daf-90ad-af354d93c78c` | Operations Manager | Month 23 stockout risk will be <= 0.1600. | True | 0.0859->0.0861 |
| 23 | `2b0b256b-e818-475f-acf3-80ee4323f572` | Founder CEO | Month 23 strategy will improve business health score. | False | 0.0082->0.0078 |
| 24 | `fd4b0c79-83f0-425b-b78e-0380a068897f` | Growth Marketer | Month 24 CAC will be <= 45.06. | True | 0.5217->0.5417 |
| 24 | `704a9841-874c-4a15-83aa-00e371ae1050` | Product Manager | Month 24 conversion rate will be >= 0.0530. | True | 0.0900->0.0900 |
| 24 | `114b534b-e517-47f0-aec1-6a387b1fb43d` | Finance Controller | Month 24 gross revenue will be >= 51247.35. | True | 0.0900->0.0900 |
| 24 | `cf9341de-dc56-4519-8ac6-0456f06f59f7` | Operations Manager | Month 24 stockout risk will be <= 0.1600. | True | 0.0861->0.0862 |
| 24 | `001b8934-f603-43ba-bfc5-3b03eaf21082` | Founder CEO | Month 24 strategy will improve business health score. | False | 0.0078->0.0075 |
| 25 | `5c3294f0-74bc-4aad-b03a-f1ca60df8e84` | Growth Marketer | Month 25 CAC will be <= 46.38. | True | 0.5417->0.5600 |
| 25 | `a4d24815-f826-461b-ac70-1b99b8e5c2a6` | Product Manager | Month 25 conversion rate will be >= 0.0514. | True | 0.0900->0.0900 |
| 25 | `f3fbab69-b95f-447b-8f9a-f751b6a8ac26` | Finance Controller | Month 25 gross revenue will be >= 53081.33. | True | 0.0900->0.0900 |
| 25 | `22019dbf-8a77-4f04-b25f-6c5db1e1ce09` | Operations Manager | Month 25 stockout risk will be <= 0.1600. | True | 0.0862->0.0864 |
| 25 | `64284bfb-6043-4659-a8d2-ae2f187c7f89` | Founder CEO | Month 25 strategy will improve business health score. | False | 0.0075->0.0072 |
| 26 | `7ec8f7ff-490e-493f-86d5-115db23148e5` | Growth Marketer | Month 26 CAC will be <= 45.89. | True | 0.5600->0.5769 |
| 26 | `327250f1-9260-453b-8f78-191966608ad5` | Product Manager | Month 26 conversion rate will be >= 0.0506. | True | 0.0900->0.0900 |
| 26 | `6c809cea-e6a8-4fa6-b065-bfe72e95098d` | Finance Controller | Month 26 gross revenue will be >= 55709.78. | True | 0.0900->0.0900 |
| 26 | `95f16c75-e903-44ff-a5c3-fe4d40908ccc` | Operations Manager | Month 26 stockout risk will be <= 0.1600. | True | 0.0864->0.0865 |
| 26 | `5168d725-b59a-4664-bd9c-b74eeeea560b` | Founder CEO | Month 26 strategy will improve business health score. | False | 0.0072->0.0069 |
| 27 | `61517bd2-08d1-4dd2-86c6-9487c3898a9e` | Growth Marketer | Month 27 CAC will be <= 41.00. | True | 0.5769->0.5926 |
| 27 | `26268276-a043-48f2-909e-526487603da0` | Product Manager | Month 27 conversion rate will be >= 0.0528. | True | 0.0900->0.0900 |
| 27 | `241e3e00-2d70-4dc8-afcd-acc2be768090` | Finance Controller | Month 27 gross revenue will be >= 58880.25. | True | 0.0900->0.0900 |
| 27 | `b702e9df-9d65-469b-88b3-4c1f66ddac83` | Operations Manager | Month 27 stockout risk will be <= 0.1600. | True | 0.0865->0.0867 |
| 27 | `fe050d88-2b78-4902-9663-6c16f54e2572` | Founder CEO | Month 27 strategy will improve business health score. | False | 0.0069->0.0067 |
| 28 | `8cea6649-79fc-4d56-8115-a000bd702fa3` | Growth Marketer | Month 28 CAC will be <= 47.19. | True | 0.5926->0.6071 |
| 28 | `cdb1c5f0-a33e-4ed5-80bd-3077d4b1616f` | Product Manager | Month 28 conversion rate will be >= 0.0471. | True | 0.0900->0.0900 |
| 28 | `b7f06f72-4ed8-47ec-a0be-a332770288d1` | Finance Controller | Month 28 gross revenue will be >= 61315.65. | True | 0.0900->0.0900 |
| 28 | `ccc51196-86d0-40b2-9cc1-19aed973eb37` | Operations Manager | Month 28 stockout risk will be <= 0.1600. | True | 0.0867->0.0868 |
| 28 | `7f0b8f75-7ea0-4495-bff5-4e58fad1f932` | Founder CEO | Month 28 strategy will improve business health score. | False | 0.0067->0.0064 |
| 29 | `9f8a3c6c-1caa-43a0-958c-34b93c9b1bba` | Growth Marketer | Month 29 CAC will be <= 47.29. | True | 0.6071->0.6207 |
| 29 | `0f60f497-d0d6-4f17-816a-a1a4011d0891` | Product Manager | Month 29 conversion rate will be >= 0.0473. | True | 0.0900->0.0900 |
| 29 | `bfe19e7b-e335-4ef4-a86c-8f16be0be46a` | Finance Controller | Month 29 gross revenue will be >= 64627.20. | True | 0.0900->0.0900 |
| 29 | `d5268aec-fe83-481c-8d5a-33a2f685d301` | Operations Manager | Month 29 stockout risk will be <= 0.1600. | True | 0.0868->0.0869 |
| 29 | `0797798e-ffb9-4683-8240-9134a1fa3fea` | Founder CEO | Month 29 strategy will improve business health score. | False | 0.0064->0.0062 |
| 30 | `e4d650bb-8424-493f-b0b3-ff19d4790e3b` | Growth Marketer | Month 30 CAC will be <= 46.84. | True | 0.6207->0.6333 |
| 30 | `eea1e4f1-9d61-49f4-abc2-6ee158adc150` | Product Manager | Month 30 conversion rate will be >= 0.0509. | True | 0.0900->0.0900 |
| 30 | `547450f6-d406-4199-a51c-423515b15621` | Finance Controller | Month 30 gross revenue will be >= 66513.15. | True | 0.0900->0.0900 |
| 30 | `7d7fb330-6ecb-4e48-bd7f-5acd089d708a` | Operations Manager | Month 30 stockout risk will be <= 0.1600. | True | 0.0869->0.0870 |
| 30 | `cad0ddaf-ca19-46a5-8a27-0107dd58d458` | Founder CEO | Month 30 strategy will improve business health score. | False | 0.0062->0.0060 |
| 31 | `63b862ab-c635-40a7-8496-dc8d2c66f00b` | Growth Marketer | Month 31 CAC will be <= 49.10. | True | 0.6333->0.6452 |
| 31 | `2b40cdbc-4031-444e-a46b-c4d04517574d` | Product Manager | Month 31 conversion rate will be >= 0.0482. | True | 0.0900->0.0900 |
| 31 | `58fd5ac8-a2e5-4262-b9b7-0cf7fc54370d` | Finance Controller | Month 31 gross revenue will be >= 69364.35. | True | 0.0900->0.0900 |
| 31 | `f7f072f8-5cc2-4f58-b543-d6cbcada113c` | Operations Manager | Month 31 stockout risk will be <= 0.1600. | True | 0.0870->0.0871 |
| 31 | `d545231d-c250-4238-986b-b548f0e2e1a5` | Founder CEO | Month 31 strategy will improve business health score. | False | 0.0060->0.0058 |
| 32 | `83c730a9-2067-4de0-99b6-2d27a1d89450` | Growth Marketer | Month 32 CAC will be <= 49.07. | True | 0.6452->0.6562 |
| 32 | `5613e193-46c5-41f5-8fec-479e2202e5b1` | Product Manager | Month 32 conversion rate will be >= 0.0459. | True | 0.0900->0.0900 |
| 32 | `e084e93f-6c39-4bef-94b1-4c44845a920d` | Finance Controller | Month 32 gross revenue will be >= 72007.65. | True | 0.0900->0.0900 |
| 32 | `6ce93c82-3b77-44ad-a36b-cb23e21c0f8d` | Operations Manager | Month 32 stockout risk will be <= 0.1600. | True | 0.0871->0.0872 |
| 32 | `33f9660d-62df-4996-b5d4-61c12aea4fc9` | Founder CEO | Month 32 strategy will improve business health score. | False | 0.0058->0.0056 |
| 33 | `63ee84db-1401-4583-b06e-44603f1ec37b` | Growth Marketer | Month 33 CAC will be <= 46.55. | True | 0.6562->0.6667 |
| 33 | `0e4965d8-add1-455f-a3ee-a543ac01f4da` | Product Manager | Month 33 conversion rate will be >= 0.0469. | True | 0.0900->0.0900 |
| 33 | `b4664522-a673-4f53-80eb-352c145bdc65` | Finance Controller | Month 33 gross revenue will be >= 74873.70. | True | 0.0900->0.0900 |
| 33 | `8bd02190-cfb3-499b-8293-6279c38f2b53` | Operations Manager | Month 33 stockout risk will be <= 0.1600. | True | 0.0872->0.0873 |
| 33 | `8a6aab63-9b78-4eda-ac11-a9ae3dbd3fd0` | Founder CEO | Month 33 strategy will improve business health score. | False | 0.0056->0.0055 |
| 34 | `e07d4b46-80df-450b-8ed4-4ea0c4e9d443` | Growth Marketer | Month 34 CAC will be <= 46.10. | True | 0.6667->0.6765 |
| 34 | `2dce1598-14fa-4d47-95d0-a56babd9ede0` | Product Manager | Month 34 conversion rate will be >= 0.0510. | True | 0.0900->0.0900 |
| 34 | `4ecd17b2-da7e-4d0e-9ed7-51769788191c` | Finance Controller | Month 34 gross revenue will be >= 77531.85. | True | 0.0900->0.0900 |
| 34 | `9224e866-4fd1-42c6-85b8-37953962f7ff` | Operations Manager | Month 34 stockout risk will be <= 0.1600. | True | 0.0873->0.0874 |
| 34 | `71bb8c48-e0e9-4f23-95f9-5902a7530205` | Founder CEO | Month 34 strategy will improve business health score. | False | 0.0055->0.0053 |
| 35 | `0db4c409-25ed-4796-9d7d-7d9d4f4393a4` | Growth Marketer | Month 35 CAC will be <= 45.16. | True | 0.6765->0.6857 |
| 35 | `e38f366e-c58b-4f42-8f71-26b81b7fdf96` | Product Manager | Month 35 conversion rate will be >= 0.0486. | True | 0.0900->0.0900 |
| 35 | `5e42382d-f9c8-4077-93a7-5215417bc42b` | Finance Controller | Month 35 gross revenue will be >= 80071.20. | True | 0.0900->0.0900 |
| 35 | `4f696be2-63ec-4413-a210-47d9a3cddc0e` | Operations Manager | Month 35 stockout risk will be <= 0.1600. | True | 0.0874->0.0874 |
| 35 | `153b07f6-9d68-44c1-907a-4129ff37c9c6` | Founder CEO | Month 35 strategy will improve business health score. | False | 0.0053->0.0051 |
| 36 | `a7170f83-5bf8-431d-b205-5c22dd0c4da3` | Growth Marketer | Month 36 CAC will be <= 44.95. | True | 0.6857->0.6944 |
| 36 | `2ec9fe2e-753b-4d1b-89da-2121c82033ed` | Product Manager | Month 36 conversion rate will be >= 0.0521. | True | 0.0900->0.0900 |
| 36 | `2a25d39d-ab50-4fe5-a178-3075833e120b` | Finance Controller | Month 36 gross revenue will be >= 81905.18. | True | 0.0900->0.0900 |
| 36 | `cd9a911d-fbca-4ca2-8bdb-14589ca55865` | Operations Manager | Month 36 stockout risk will be <= 0.1600. | True | 0.0874->0.0875 |
| 36 | `edc666f4-c068-4730-a658-f28a0b6501a7` | Founder CEO | Month 36 strategy will improve business health score. | False | 0.0051->0.0050 |

## Actual Market Outcomes
Actuals came only from `market_oracle_monthly_actual` rows in `pawdent_monthly_financials.csv`.

## Circular Verification Rejection
circular verification rejected in month 1: circular resolution rejected: claim source and resolution source are the same URL (https:market_oracle_pre_decision_signal:seed=7319:month=1)

## Product Roadmap Evolution
| Month | Phase | Roadmap | Quality investment | Reminder investment |
|---:|---|---|---:|---:|
| 1 | idea exploration and customer discovery | pilot routine adherence | 4000 | 900 |
| 2 | idea exploration and customer discovery | pilot routine adherence | 4000 | 900 |
| 3 | idea exploration and customer discovery | pilot routine adherence | 4000 | 900 |
| 4 | MVP design and pilot | pilot routine adherence | 4000 | 2500 |
| 5 | MVP design and pilot | pilot routine adherence | 4000 | 2500 |
| 6 | MVP design and pilot | pilot routine adherence | 4000 | 900 |
| 7 | public launch and early growth | retention and vet education | 3000 | 900 |
| 8 | public launch and early growth | retention and vet education | 6500 | 900 |
| 9 | public launch and early growth | retention and vet education | 3000 | 2500 |
| 10 | public launch and early growth | retention and vet education | 3000 | 900 |
| 11 | public launch and early growth | retention and vet education | 3000 | 900 |
| 12 | public launch and early growth | retention and vet education | 3000 | 900 |
| 13 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 14 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 15 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 2500 |
| 16 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 17 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 18 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 19 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 20 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 21 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 2500 |
| 22 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 23 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 24 | scaling, retention, partnerships, and product iterations | retention and vet education | 3000 | 900 |
| 25 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 26 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 27 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 28 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 29 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 30 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 31 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 32 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 33 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 34 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 35 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |
| 36 | maturity, competition, survival, expansion, or shutdown | mature refill experience | 3000 | 900 |

## Marketing Decisions
Marketing decisions are recorded as `ad_budget_and_channel` events with source-tracked inputs.

## Operations Decisions
Operations decisions are recorded as `inventory_and_quality` events and affected stockouts, refunds, support tickets, and margin.

## Finance Decisions
Finance decisions are recorded as `cash_and_unit_economics` events and shaped fixed operating costs, runway, and funding need.

## P&L Summary
- Total revenue: `2733975.00`
- Total operating profit: `-711171.82`
- Final cash balance: `-461171.82`
- Profitable months: `0`

## Customer Growth Chart
| Month | Active subscribers | New paid subscribers | Churned subscribers | CAC | LTV estimate | ARPU |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 53 | 53 | 0 | 56.6 | 41.04 | 22.96 |
| 2 | 119 | 71 | 5 | 42.25 | 49.79 | 22.74 |
| 3 | 171 | 63 | 11 | 47.62 | 48.08 | 22.95 |
| 4 | 340 | 185 | 16 | 48.65 | 78.91 | 26.03 |
| 5 | 525 | 221 | 36 | 40.72 | 72.77 | 26.07 |
| 6 | 747 | 266 | 44 | 33.83 | 89.05 | 25.82 |
| 7 | 1040 | 367 | 74 | 40.87 | 87.1 | 26.15 |
| 8 | 1319 | 371 | 92 | 47.17 | 57.54 | 26.06 |
| 9 | 1595 | 393 | 117 | 50.89 | 95.97 | 26.22 |
| 10 | 1541 | 86 | 140 | 34.88 | 89.37 | 26.19 |
| 11 | 1512 | 92 | 121 | 32.61 | 101.74 | 26.08 |
| 12 | 1514 | 104 | 102 | 28.85 | 120.31 | 26.27 |
| 13 | 1706 | 304 | 112 | 39.47 | 113.98 | 26.04 |
| 14 | 1902 | 290 | 94 | 41.38 | 138.56 | 26.01 |
| 15 | 2105 | 308 | 105 | 38.96 | 143.48 | 26.32 |
| 16 | 2302 | 315 | 118 | 38.1 | 141.95 | 26.22 |
| 17 | 2466 | 327 | 163 | 36.7 | 117.95 | 26.35 |
| 18 | 2569 | 270 | 167 | 44.44 | 116.78 | 26.27 |
| 19 | 2678 | 279 | 170 | 43.01 | 118.4 | 26.16 |
| 20 | 2869 | 325 | 134 | 36.92 | 160.72 | 26.28 |
| 21 | 3024 | 304 | 149 | 39.47 | 155.19 | 26.33 |
| 22 | 3156 | 309 | 177 | 38.83 | 127.42 | 26.15 |
| 23 | 3316 | 270 | 110 | 44.44 | 213.88 | 26.4 |
| 24 | 3430 | 290 | 176 | 41.38 | 146.84 | 26.13 |
| 25 | 3595 | 314 | 149 | 38.22 | 172.49 | 26.3 |
| 26 | 3794 | 353 | 154 | 33.99 | 182.09 | 26.24 |
| 27 | 3971 | 316 | 139 | 37.97 | 208.15 | 26.18 |
| 28 | 4181 | 352 | 142 | 34.09 | 164.24 | 26.5 |
| 29 | 4314 | 330 | 197 | 36.36 | 115.35 | 26.15 |
| 30 | 4500 | 359 | 173 | 33.43 | 194.9 | 26.28 |
| 31 | 4678 | 364 | 186 | 32.97 | 184.55 | 26.49 |
| 32 | 4874 | 336 | 140 | 35.71 | 264.37 | 26.25 |
| 33 | 5050 | 355 | 179 | 33.8 | 203.97 | 26.24 |
| 34 | 5226 | 332 | 156 | 36.14 | 249.77 | 26.13 |
| 35 | 5374 | 283 | 135 | 42.4 | 280.08 | 26.29 |
| 36 | 5520 | 287 | 141 | 41.81 | 294.95 | 26.44 |

## Biggest Correct Call
{"agent": "Growth Marketer", "calibration_delta": 0.1702, "claim": "Month 14 CAC will be <= 43.28.", "claim_source": "market_oracle_pre_decision_signal:seed=7319:month=14", "confidence": 0.62, "explanation": "CAC actual 41.38 <= 43.28", "month": 14, "outcome": true, "prediction_id": "662e6806-c0be-4859-9ac4-fb151c3322fd", "resolution_source": "market_oracle_monthly_actual:seed=7319:month=14", "run_id": "pawdent-0476b188-783f-4265-8a7a-65bfa05a0684", "seed": 7319, "simulated_date": "2028-02-01", "trust_after": 0.5, "trust_before": 0.3298}

## Biggest Wrong Call
{"agent": "Growth Marketer", "calibration_delta": -0.3968, "claim": "Month 5 CAC will be <= 39.72.", "claim_source": "market_oracle_pre_decision_signal:seed=7319:month=5", "confidence": 0.62, "explanation": "CAC actual 40.72 > 39.72", "month": 5, "outcome": false, "prediction_id": "09e1891e-9469-4db0-a016-a88ddc4b573a", "resolution_source": "market_oracle_monthly_actual:seed=7319:month=5", "run_id": "pawdent-0476b188-783f-4265-8a7a-65bfa05a0684", "seed": 7319, "simulated_date": "2027-05-01", "trust_after": 0.0, "trust_before": 0.3968}

## Agent Trust Leaderboard
| Agent | Last trust | Resolved claims |
|---|---:|---:|
| Growth Marketer | 0.6944 | 36 |
| Product Manager | 0.0900 | 36 |
| Finance Controller | 0.0900 | 36 |
| Operations Manager | 0.0875 | 36 |
| Founder CEO | 0.0050 | 36 |

## Final Business Status
failed

## What The Institution Learned
PawDent worked when acquisition was paced by resolved CAC and retention, but stockouts and quality gaps could erase demand gains.

## Next 12-Month Plan
- Keep the subscription live only if cash remains above a six-month operating buffer.
- Expand vet partnerships in markets where churn is below 8%.
- Raise supplier redundancy before increasing paid media.
- Continue monthly preregistered forecasts for CAC, revenue, stockout risk, conversion, and business health.
