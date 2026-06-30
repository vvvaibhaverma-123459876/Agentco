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
| 1 | `d3a4da45-9560-42b5-8ebd-c1fca18a8e0b` | Growth Marketer | Month 1 CAC will be <= 38.68. | False | 0.4960->0.4712 |
| 1 | `71bcdf70-fcea-464e-acb6-30721c8d3472` | Product Manager | Month 1 conversion rate will be >= 0.0401. | True | 0.4640->0.4408 |
| 1 | `c9e81b51-e7cf-47cf-9c7f-f8943b729b22` | Finance Controller | Month 1 gross revenue will be >= 500.00. | True | 0.4800->0.4560 |
| 1 | `b873a83c-eb2c-4586-b28f-bc3a71c425ee` | Operations Manager | Month 1 stockout risk will be <= 0.1000. | True | 0.5120->0.4864 |
| 1 | `f5ce0bad-3c72-4048-b5dc-bd3f26ca8b3b` | Founder CEO | Month 1 strategy will improve business health score. | True | 0.4480->0.4256 |
| 2 | `7164d16a-77e5-4d04-8145-522f6a37553a` | Growth Marketer | Month 2 CAC will be <= 36.38. | False | 0.4712->0.4464 |
| 2 | `22d4491b-23db-433d-bb8b-474f339f9330` | Product Manager | Month 2 conversion rate will be >= 0.0420. | True | 0.4408->0.4176 |
| 2 | `4f6c821f-eb63-47ae-a1cb-966bd5457747` | Finance Controller | Month 2 gross revenue will be >= 699.60. | True | 0.4560->0.4320 |
| 2 | `d4be9418-c098-4e2d-9861-7853159e7c00` | Operations Manager | Month 2 stockout risk will be <= 0.1000. | False | 0.4864->0.4608 |
| 2 | `c4521f72-3731-4af1-9eb2-02e19e9363f3` | Founder CEO | Month 2 strategy will improve business health score. | False | 0.4256->0.4032 |
| 3 | `2e0d2f2b-9a7a-4948-818d-88ba69109c7c` | Growth Marketer | Month 3 CAC will be <= 38.61. | False | 0.4464->0.4216 |
| 3 | `fc480a63-6fbf-49c3-8081-c4412064a8cc` | Product Manager | Month 3 conversion rate will be >= 0.0377. | True | 0.4176->0.3944 |
| 3 | `8321b6a5-33d6-4a7c-8851-d640eb8a089c` | Finance Controller | Month 3 gross revenue will be >= 1570.80. | True | 0.4320->0.4080 |
| 3 | `11ced137-1d6a-460d-bacf-7bceba9b3487` | Operations Manager | Month 3 stockout risk will be <= 0.1000. | True | 0.4608->0.4352 |
| 3 | `fc7f66fc-3357-4cdd-85af-d3c5737eb35d` | Founder CEO | Month 3 strategy will improve business health score. | True | 0.4032->0.3808 |
| 4 | `9b72df9c-91b8-466d-b3c8-b33334cfa1c9` | Growth Marketer | Month 4 CAC will be <= 39.83. | False | 0.4216->0.3968 |
| 4 | `f78316d4-a166-41da-92a7-21358021c13b` | Product Manager | Month 4 conversion rate will be >= 0.0416. | True | 0.3944->0.3712 |
| 4 | `854c9ba4-4ba5-496e-b7b4-5b91104a0a69` | Finance Controller | Month 4 gross revenue will be >= 3578.85. | True | 0.4080->0.3840 |
| 4 | `d55bca7f-61b2-451e-aecb-19e7c13b9153` | Operations Manager | Month 4 stockout risk will be <= 0.1000. | True | 0.4352->0.4096 |
| 4 | `30c811bd-97b1-4464-8ee7-d8ce3b9ec927` | Founder CEO | Month 4 strategy will improve business health score. | False | 0.3808->0.3584 |
| 5 | `e31d6a9d-7c70-487b-b320-a1914ae87e54` | Growth Marketer | Month 5 CAC will be <= 39.72. | False | 0.3968->0.0000 |
| 5 | `23051dcc-abe2-4316-a551-4f3af40e427e` | Product Manager | Month 5 conversion rate will be >= 0.0407. | True | 0.3712->0.0900 |
| 5 | `0447628a-62bf-49bc-9c72-c22fe57b02c9` | Finance Controller | Month 5 gross revenue will be >= 6088.50. | True | 0.3840->0.0900 |
| 5 | `0db23b16-d251-4ccf-9ebc-94707a9aa03e` | Operations Manager | Month 5 stockout risk will be <= 0.1600. | True | 0.4096->0.2800 |
| 5 | `b9a722f2-073a-4485-be85-e5029dce1b3c` | Founder CEO | Month 5 strategy will improve business health score. | False | 0.3584->0.3584 |
| 6 | `264d0e66-0de6-44ca-b400-f8a3edcf550b` | Growth Marketer | Month 6 CAC will be <= 42.34. | True | 0.0000->0.0150 |
| 6 | `7cb54c06-6b18-4423-8766-03d76afec6df` | Product Manager | Month 6 conversion rate will be >= 0.0411. | True | 0.0900->0.0900 |
| 6 | `b165e4c4-320c-4e3e-a236-9e36dd950483` | Finance Controller | Month 6 gross revenue will be >= 8835.75. | True | 0.0900->0.0900 |
| 6 | `75b5485b-77c0-4ef7-925c-01f30cb90300` | Operations Manager | Month 6 stockout risk will be <= 0.1600. | True | 0.2800->0.1667 |
| 6 | `3d9a17dd-dcad-4926-a986-706d8d4e73b4` | Founder CEO | Month 6 strategy will improve business health score. | False | 0.3584->0.1778 |
| 7 | `5c519d6e-1c7d-4ca2-996a-6401c798f524` | Growth Marketer | Month 7 CAC will be <= 43.15. | True | 0.0150->0.0306 |
| 7 | `8cc13573-f2d8-4763-9860-002719bca78d` | Product Manager | Month 7 conversion rate will be >= 0.0407. | True | 0.0900->0.0900 |
| 7 | `2a828f02-97e0-4225-860b-e81c6d3259a8` | Finance Controller | Month 7 gross revenue will be >= 13691.70. | True | 0.0900->0.0900 |
| 7 | `de2b7121-ca72-45ce-bdc4-2b83eceb5c4a` | Operations Manager | Month 7 stockout risk will be <= 0.1000. | True | 0.1667->0.1359 |
| 7 | `8fa30760-2774-43f2-a675-3da58e7ed382` | Founder CEO | Month 7 strategy will improve business health score. | False | 0.1778->0.0805 |
| 8 | `031dacad-7c44-4fe1-a565-d17bf4097d68` | Growth Marketer | Month 8 CAC will be <= 35.72. | False | 0.0306->0.0225 |
| 8 | `26084f2a-3a2c-4662-ae13-d0fed46a2e9b` | Product Manager | Month 8 conversion rate will be >= 0.0435. | True | 0.0900->0.0900 |
| 8 | `2f8245f4-1f2d-4444-8961-5c722eb4c749` | Finance Controller | Month 8 gross revenue will be >= 18376.88. | True | 0.0900->0.0900 |
| 8 | `682712bc-618e-4d02-b83b-d99ad695a10c` | Operations Manager | Month 8 stockout risk will be <= 0.1600. | True | 0.1359->0.1247 |
| 8 | `7f747ff3-2b68-4c45-b6a9-12c718ee5218` | Founder CEO | Month 8 strategy will improve business health score. | False | 0.0805->0.0413 |
| 9 | `229d7fed-a255-4146-abef-2434817073ec` | Growth Marketer | Month 9 CAC will be <= 42.97. | False | 0.0225->0.0200 |
| 9 | `99e4749e-cbe0-4bee-ae3d-d101e9b08fb4` | Product Manager | Month 9 conversion rate will be >= 0.0443. | True | 0.0900->0.0900 |
| 9 | `ecc07285-7ba6-4d9b-b4b2-3ca74fb8f35b` | Finance Controller | Month 9 gross revenue will be >= 22854.15. | True | 0.0900->0.0900 |
| 9 | `565a2186-11d2-4470-9286-2186de4423b2` | Operations Manager | Month 9 stockout risk will be <= 0.1600. | True | 0.1247->0.1156 |
| 9 | `bfcfb142-574f-409a-b46e-9811ec7c3a2a` | Founder CEO | Month 9 strategy will improve business health score. | False | 0.0413->0.0311 |
| 10 | `6303d732-2ab9-4079-93c1-a62e0a78350a` | Growth Marketer | Month 10 CAC will be <= 42.69. | True | 0.0200->0.0360 |
| 10 | `16f91a38-3283-4a87-b3af-6bf8942ceb63` | Product Manager | Month 10 conversion rate will be >= 0.0464. | True | 0.0900->0.0900 |
| 10 | `0ed388b5-7bdb-47cd-b32a-8d83b860d519` | Finance Controller | Month 10 gross revenue will be >= 27286.88. | True | 0.0900->0.0900 |
| 10 | `d125f5a5-2ecb-4032-a9cf-cbc05886f763` | Operations Manager | Month 10 stockout risk will be <= 0.1600. | True | 0.1156->0.1080 |
| 10 | `2773e58c-727b-4c5a-80aa-33ebae15c36c` | Founder CEO | Month 10 strategy will improve business health score. | False | 0.0311->0.0240 |
| 11 | `a934b51c-97a6-4ff5-bf32-d79ba14a538d` | Growth Marketer | Month 11 CAC will be <= 35.97. | True | 0.0360->0.0684 |
| 11 | `58f5ead1-8f1f-4b2a-91b9-4dd30e482d63` | Product Manager | Month 11 conversion rate will be >= 0.0487. | True | 0.0900->0.0900 |
| 11 | `8576898d-5d2f-47fa-8bf8-ce1545e5b80e` | Finance Controller | Month 11 gross revenue will be >= 26819.10. | True | 0.0900->0.0900 |
| 11 | `671f5d85-db32-4836-8c25-6c9e482568ab` | Operations Manager | Month 11 stockout risk will be <= 0.1600. | True | 0.1080->0.1017 |
| 11 | `148a1555-fea6-4ec7-8046-c1c56d5806c8` | Founder CEO | Month 11 strategy will improve business health score. | False | 0.0240->0.0188 |
| 12 | `f6c7dc02-37d8-40d2-806d-b73450a68647` | Growth Marketer | Month 12 CAC will be <= 40.82. | True | 0.0684->0.1823 |
| 12 | `f97ac02d-5148-4b28-b8c7-d20dac5e6bd0` | Product Manager | Month 12 conversion rate will be >= 0.0439. | True | 0.0900->0.0900 |
| 12 | `fea35187-5ef6-4fa8-a3d6-5df641da1bf5` | Finance Controller | Month 12 gross revenue will be >= 26722.58. | True | 0.0900->0.0900 |
| 12 | `ce5fdd01-562c-4c36-83b8-8330ea10d374` | Operations Manager | Month 12 stockout risk will be <= 0.1600. | True | 0.1017->0.0963 |
| 12 | `ae8504f2-c2b2-4211-a630-12741dd7104d` | Founder CEO | Month 12 strategy will improve business health score. | False | 0.0188->0.0150 |
| 13 | `c0fc360e-8845-4b49-a860-a73f8012630f` | Growth Marketer | Month 13 CAC will be <= 41.48. | True | 0.1823->0.3298 |
| 13 | `70ac8072-57fb-4560-9998-01ecdca62d18` | Product Manager | Month 13 conversion rate will be >= 0.0495. | True | 0.0900->0.0900 |
| 13 | `cfa076ca-9d33-4e5f-9975-01351171372a` | Finance Controller | Month 13 gross revenue will be >= 25022.25. | True | 0.0900->0.0900 |
| 13 | `4070f13b-a20f-41cd-8fb5-1ca5ad2d450b` | Operations Manager | Month 13 stockout risk will be <= 0.1600. | True | 0.0963->0.0916 |
| 13 | `288bfcff-f7c9-4a2f-b77b-c25958c04761` | Founder CEO | Month 13 strategy will improve business health score. | False | 0.0150->0.0138 |
| 14 | `c1368392-446d-44c9-a288-6c5cf798b398` | Growth Marketer | Month 14 CAC will be <= 43.28. | True | 0.3298->0.5000 |
| 14 | `e6ef0054-715a-4930-8f1e-c7dd36c9e1f7` | Product Manager | Month 14 conversion rate will be >= 0.0486. | True | 0.0900->0.0900 |
| 14 | `72ad85f8-52ad-4b8e-96b9-df856a5728b8` | Finance Controller | Month 14 gross revenue will be >= 27591.30. | True | 0.0900->0.0900 |
| 14 | `19db6e1d-abba-4e55-bd1c-5108fd91d426` | Operations Manager | Month 14 stockout risk will be <= 0.1600. | True | 0.0916->0.0876 |
| 14 | `19ca5f21-5709-4a48-b155-447382f36d47` | Founder CEO | Month 14 strategy will improve business health score. | False | 0.0138->0.0129 |
| 15 | `f0c10583-2be8-4230-b121-b68472043442` | Growth Marketer | Month 15 CAC will be <= 37.24. | False | 0.5000->0.3500 |
| 15 | `6d980e9e-9d57-41ff-9555-6341d2691c15` | Product Manager | Month 15 conversion rate will be >= 0.0454. | True | 0.0900->0.0900 |
| 15 | `6b799513-f782-4227-b98a-83f989e692f8` | Finance Controller | Month 15 gross revenue will be >= 30390.53. | True | 0.0900->0.0900 |
| 15 | `b5e696a3-710a-48c6-8977-4f372429474f` | Operations Manager | Month 15 stockout risk will be <= 0.1600. | True | 0.0876->0.0840 |
| 15 | `579267cb-6358-49a9-b7fc-ac80d66d8734` | Founder CEO | Month 15 strategy will improve business health score. | False | 0.0129->0.0120 |
| 16 | `75506a16-d885-411d-b11c-10b52b587eac` | Growth Marketer | Month 16 CAC will be <= 43.05. | True | 0.3500->0.5000 |
| 16 | `0311dc60-438f-412c-84b2-80e701f7717f` | Product Manager | Month 16 conversion rate will be >= 0.0464. | True | 0.0900->0.0900 |
| 16 | `de5766ac-52c3-4c51-aa45-a14bca40d71d` | Finance Controller | Month 16 gross revenue will be >= 33546.15. | True | 0.0900->0.0900 |
| 16 | `1d64c5b6-cea9-4b80-8755-56a97ea49289` | Operations Manager | Month 16 stockout risk will be <= 0.1600. | True | 0.0840->0.0844 |
| 16 | `c6e53ecb-1523-4317-a438-c6fcf2bdd4fa` | Founder CEO | Month 16 strategy will improve business health score. | False | 0.0120->0.0112 |
| 17 | `dd6e03e6-6d60-4bf0-8df9-f5dddb1d0f2f` | Growth Marketer | Month 17 CAC will be <= 42.95. | True | 0.5000->0.5294 |
| 17 | `9f686515-b234-4828-b819-f68423bc64d6` | Product Manager | Month 17 conversion rate will be >= 0.0471. | True | 0.0900->0.0900 |
| 17 | `6ae93221-16b4-4a79-b963-b6176c3a6a5e` | Finance Controller | Month 17 gross revenue will be >= 36516.15. | True | 0.0900->0.0900 |
| 17 | `5b9696e4-3e0c-44a3-9d64-d61487ae5885` | Operations Manager | Month 17 stockout risk will be <= 0.1600. | True | 0.0844->0.0847 |
| 17 | `38709da3-039d-438e-a31d-3990b7855503` | Founder CEO | Month 17 strategy will improve business health score. | False | 0.0112->0.0106 |
| 18 | `33e5c0db-6b6a-4bf6-8613-c89fe2110aff` | Growth Marketer | Month 18 CAC will be <= 38.07. | False | 0.5294->0.5000 |
| 18 | `58bdffbe-9615-40a3-859b-25b431990d96` | Product Manager | Month 18 conversion rate will be >= 0.0477. | True | 0.0900->0.0900 |
| 18 | `7b53a0c7-3140-459f-ab9c-2b1670b902ca` | Finance Controller | Month 18 gross revenue will be >= 39040.65. | True | 0.0900->0.0900 |
| 18 | `2a61d478-2dad-46d7-96f2-2474ce2b9b42` | Operations Manager | Month 18 stockout risk will be <= 0.1600. | True | 0.0847->0.0850 |
| 18 | `9b4375e4-c535-4157-9db2-fe4848afe286` | Founder CEO | Month 18 strategy will improve business health score. | False | 0.0106->0.0100 |
| 19 | `3636e387-d641-4b23-8e76-6a8b96a62b50` | Growth Marketer | Month 19 CAC will be <= 42.04. | False | 0.5000->0.3789 |
| 19 | `9863fb31-02ca-41aa-94c5-08bc6d8723b4` | Product Manager | Month 19 conversion rate will be >= 0.0459. | True | 0.0900->0.0900 |
| 19 | `1dbfe97f-7db3-4231-9de8-e08b1d9bcac9` | Finance Controller | Month 19 gross revenue will be >= 40154.40. | True | 0.0900->0.0900 |
| 19 | `b720adf5-1763-4f42-bb9a-827fcf53d0f3` | Operations Manager | Month 19 stockout risk will be <= 0.1600. | True | 0.0850->0.0853 |
| 19 | `d91882e0-9c12-495b-9f39-b306948966bb` | Founder CEO | Month 19 strategy will improve business health score. | False | 0.0100->0.0095 |
| 20 | `df2047f7-bc81-424f-b3c4-5629136354ab` | Growth Marketer | Month 20 CAC will be <= 40.82. | True | 0.3789->0.5000 |
| 20 | `e2231da2-cc7e-49b7-b41d-83aa3284e758` | Product Manager | Month 20 conversion rate will be >= 0.0505. | True | 0.0900->0.0900 |
| 20 | `ec6c4c70-c680-4bed-8fb0-5ec2d6919e8d` | Finance Controller | Month 20 gross revenue will be >= 41839.88. | True | 0.0900->0.0900 |
| 20 | `18b7abb9-d7d9-4179-8edb-01c76d94eceb` | Operations Manager | Month 20 stockout risk will be <= 0.1600. | True | 0.0853->0.0855 |
| 20 | `58e6a3ee-7dfd-4601-9805-068b219bfc4c` | Founder CEO | Month 20 strategy will improve business health score. | False | 0.0095->0.0090 |
| 21 | `403ba72a-2704-443c-8fe8-acb29d1caa14` | Growth Marketer | Month 21 CAC will be <= 41.78. | True | 0.5000->0.5238 |
| 21 | `576a16ef-770b-4a31-b1b5-05750f95bd3f` | Product Manager | Month 21 conversion rate will be >= 0.0497. | True | 0.0900->0.0900 |
| 21 | `baf83323-956e-4609-a2d7-42f72eba9bca` | Finance Controller | Month 21 gross revenue will be >= 45017.78. | True | 0.0900->0.0900 |
| 21 | `4494fbe9-1b82-4b84-a6a4-b04c0d17217e` | Operations Manager | Month 21 stockout risk will be <= 0.1600. | True | 0.0855->0.0857 |
| 21 | `5c790032-1fb9-4ae5-9f90-601b806bccc4` | Founder CEO | Month 21 strategy will improve business health score. | False | 0.0090->0.0086 |
| 22 | `31e22fb1-cd79-462e-b0c0-52146a69db50` | Growth Marketer | Month 22 CAC will be <= 46.73. | True | 0.5238->0.5455 |
| 22 | `c638a88e-6ce2-414b-8e18-03f4d7aed861` | Product Manager | Month 22 conversion rate will be >= 0.0514. | True | 0.0900->0.0900 |
| 22 | `e5835aaf-3b1e-4b20-bb5f-d9d0ece235e7` | Finance Controller | Month 22 gross revenue will be >= 47163.60. | True | 0.0900->0.0900 |
| 22 | `1bf92166-1609-4c7f-b49f-83b361bfc449` | Operations Manager | Month 22 stockout risk will be <= 0.1600. | True | 0.0857->0.0859 |
| 22 | `8c02699d-2187-4f2e-ac6b-6dd37dd911de` | Founder CEO | Month 22 strategy will improve business health score. | False | 0.0086->0.0082 |
| 23 | `ea6d2862-b98f-4030-bbaa-691b2e809781` | Growth Marketer | Month 23 CAC will be <= 41.83. | False | 0.5455->0.5217 |
| 23 | `3dc3905b-cee4-4e24-9171-6e200872c9fd` | Product Manager | Month 23 conversion rate will be >= 0.0502. | True | 0.0900->0.0900 |
| 23 | `478c6dc5-0c8b-4103-bfb2-897211c9a31c` | Finance Controller | Month 23 gross revenue will be >= 49160.93. | True | 0.0900->0.0900 |
| 23 | `e47cdac5-311a-4e8e-98b7-6561f0ed89b1` | Operations Manager | Month 23 stockout risk will be <= 0.1600. | True | 0.0859->0.0861 |
| 23 | `77073447-b1c4-44bf-b152-ca53e93bd0d1` | Founder CEO | Month 23 strategy will improve business health score. | False | 0.0082->0.0078 |
| 24 | `11063e67-539d-4529-9231-ed2c73a12fbd` | Growth Marketer | Month 24 CAC will be <= 45.06. | True | 0.5217->0.5417 |
| 24 | `0c4816b4-b716-45cf-a931-01893822a5ea` | Product Manager | Month 24 conversion rate will be >= 0.0530. | True | 0.0900->0.0900 |
| 24 | `d2268763-609c-4863-a74a-13d1bbe00574` | Finance Controller | Month 24 gross revenue will be >= 51247.35. | True | 0.0900->0.0900 |
| 24 | `d241374f-00cb-4fe9-a0c4-10c14dc6225d` | Operations Manager | Month 24 stockout risk will be <= 0.1600. | True | 0.0861->0.0862 |
| 24 | `f272099d-0090-4a11-8677-7660ad7c6331` | Founder CEO | Month 24 strategy will improve business health score. | False | 0.0078->0.0075 |
| 25 | `d62c565f-641e-4eff-8ce3-396c03afdf20` | Growth Marketer | Month 25 CAC will be <= 46.38. | True | 0.5417->0.5600 |
| 25 | `8c0c6f3b-0eb3-4404-b150-35a1ae547195` | Product Manager | Month 25 conversion rate will be >= 0.0514. | True | 0.0900->0.0900 |
| 25 | `452d101c-0cdf-449d-81b5-23a49a9cb6af` | Finance Controller | Month 25 gross revenue will be >= 53081.33. | True | 0.0900->0.0900 |
| 25 | `b124dfd3-3f62-4997-870f-db54e9ce6f0c` | Operations Manager | Month 25 stockout risk will be <= 0.1600. | True | 0.0862->0.0864 |
| 25 | `76f9ceae-9073-4eda-a9ba-e7ed6d85c54f` | Founder CEO | Month 25 strategy will improve business health score. | False | 0.0075->0.0072 |
| 26 | `cebcb450-40f3-4304-9be9-9b93ccf426ef` | Growth Marketer | Month 26 CAC will be <= 45.89. | True | 0.5600->0.5769 |
| 26 | `610a1d6b-9625-4278-8c6b-2dcfa402d181` | Product Manager | Month 26 conversion rate will be >= 0.0506. | True | 0.0900->0.0900 |
| 26 | `2feb045c-8c2b-4ded-91cb-93890d9b5706` | Finance Controller | Month 26 gross revenue will be >= 55709.78. | True | 0.0900->0.0900 |
| 26 | `c4f8dcb2-fef4-49ec-9edf-7ab0378e38fd` | Operations Manager | Month 26 stockout risk will be <= 0.1600. | True | 0.0864->0.0865 |
| 26 | `4dfaf18e-913a-4e32-b59e-0bd6d4939dd3` | Founder CEO | Month 26 strategy will improve business health score. | False | 0.0072->0.0069 |
| 27 | `ecbc859d-ee49-45a4-bd8e-db1c08bb0011` | Growth Marketer | Month 27 CAC will be <= 41.00. | True | 0.5769->0.5926 |
| 27 | `1f72fc9f-7dcc-4287-84bb-6829d6eb5b48` | Product Manager | Month 27 conversion rate will be >= 0.0528. | True | 0.0900->0.0900 |
| 27 | `3cf2740c-c7eb-4b26-8e68-a0b60d71a405` | Finance Controller | Month 27 gross revenue will be >= 58880.25. | True | 0.0900->0.0900 |
| 27 | `6ccbf9c0-a7b1-4910-a79a-aef1c2e34159` | Operations Manager | Month 27 stockout risk will be <= 0.1600. | True | 0.0865->0.0867 |
| 27 | `cc3ebc1c-db6c-4b55-80a1-17be480b6e5c` | Founder CEO | Month 27 strategy will improve business health score. | False | 0.0069->0.0067 |
| 28 | `b8fc3766-3b99-48df-b985-a0cbce64b7fd` | Growth Marketer | Month 28 CAC will be <= 47.19. | True | 0.5926->0.6071 |
| 28 | `0ae8801a-1ba6-4dc0-8c5a-2a0c76c0a9c2` | Product Manager | Month 28 conversion rate will be >= 0.0471. | True | 0.0900->0.0900 |
| 28 | `5b18a6fd-5cb4-49e3-b24d-38fe7a36a233` | Finance Controller | Month 28 gross revenue will be >= 61315.65. | True | 0.0900->0.0900 |
| 28 | `84ae59fe-70f4-4da4-943e-a1231b322596` | Operations Manager | Month 28 stockout risk will be <= 0.1600. | True | 0.0867->0.0868 |
| 28 | `8e0f38f6-4280-482a-a56a-bf2b97ca5ac4` | Founder CEO | Month 28 strategy will improve business health score. | False | 0.0067->0.0064 |
| 29 | `2d70404f-4144-42db-8483-2be0670d8371` | Growth Marketer | Month 29 CAC will be <= 47.29. | True | 0.6071->0.6207 |
| 29 | `cf52945c-7b1f-483a-baf6-c0654cebcf40` | Product Manager | Month 29 conversion rate will be >= 0.0473. | True | 0.0900->0.0900 |
| 29 | `34c12bd0-6e1e-40a7-9b6a-9485b7312538` | Finance Controller | Month 29 gross revenue will be >= 64627.20. | True | 0.0900->0.0900 |
| 29 | `cd63d296-222c-409b-8ff5-48fcc440d1c1` | Operations Manager | Month 29 stockout risk will be <= 0.1600. | True | 0.0868->0.0869 |
| 29 | `696399c2-8e8b-4d6f-bbe4-3e3c58b456de` | Founder CEO | Month 29 strategy will improve business health score. | False | 0.0064->0.0062 |
| 30 | `8082e55a-5787-4921-8c1b-eeb2c60318df` | Growth Marketer | Month 30 CAC will be <= 46.84. | True | 0.6207->0.6333 |
| 30 | `e4ab9f9d-9fdf-4e41-90c2-155d24993a50` | Product Manager | Month 30 conversion rate will be >= 0.0509. | True | 0.0900->0.0900 |
| 30 | `988a2000-bc59-4769-bc5f-2a7dbad69eab` | Finance Controller | Month 30 gross revenue will be >= 66513.15. | True | 0.0900->0.0900 |
| 30 | `4a0497e2-d82a-4b01-9b3f-f5b6ea8bedce` | Operations Manager | Month 30 stockout risk will be <= 0.1600. | True | 0.0869->0.0870 |
| 30 | `888bef01-9521-4ca6-8ee9-cf1114978841` | Founder CEO | Month 30 strategy will improve business health score. | False | 0.0062->0.0060 |
| 31 | `0d274b62-dd22-4c71-82f4-bc25af48674f` | Growth Marketer | Month 31 CAC will be <= 49.10. | True | 0.6333->0.6452 |
| 31 | `4ea4b5d9-ad73-431d-9507-fcad1cf6d785` | Product Manager | Month 31 conversion rate will be >= 0.0482. | True | 0.0900->0.0900 |
| 31 | `b923a1fb-58ce-4f1f-9095-3874fcc42ce3` | Finance Controller | Month 31 gross revenue will be >= 69364.35. | True | 0.0900->0.0900 |
| 31 | `ded8bc32-9299-4cb6-9da9-8ba0be09a0ad` | Operations Manager | Month 31 stockout risk will be <= 0.1600. | True | 0.0870->0.0871 |
| 31 | `9dcbda9c-94ed-4a08-89d0-3a2a254e8366` | Founder CEO | Month 31 strategy will improve business health score. | False | 0.0060->0.0058 |
| 32 | `700db71e-6290-402a-8d46-6256755f65af` | Growth Marketer | Month 32 CAC will be <= 49.07. | True | 0.6452->0.6562 |
| 32 | `e878c75a-d30d-4075-bac9-d12467ed9883` | Product Manager | Month 32 conversion rate will be >= 0.0459. | True | 0.0900->0.0900 |
| 32 | `6165dc89-720e-4c29-ae4e-d9360b039b54` | Finance Controller | Month 32 gross revenue will be >= 72007.65. | True | 0.0900->0.0900 |
| 32 | `23ac4ec3-6ef4-4257-854d-b97c7b3f4c2a` | Operations Manager | Month 32 stockout risk will be <= 0.1600. | True | 0.0871->0.0872 |
| 32 | `322cd802-e698-4841-aa57-fca8806aabb4` | Founder CEO | Month 32 strategy will improve business health score. | False | 0.0058->0.0056 |
| 33 | `072e81aa-c04a-4f8a-9918-46787d377583` | Growth Marketer | Month 33 CAC will be <= 46.55. | True | 0.6562->0.6667 |
| 33 | `02d2d786-ec6d-40e8-86bc-c62e8587ec28` | Product Manager | Month 33 conversion rate will be >= 0.0469. | True | 0.0900->0.0900 |
| 33 | `8e054b82-908c-414e-9e3b-59414f69bb5b` | Finance Controller | Month 33 gross revenue will be >= 74873.70. | True | 0.0900->0.0900 |
| 33 | `88fc712c-dff2-4e8e-afdc-6f808a3be2f1` | Operations Manager | Month 33 stockout risk will be <= 0.1600. | True | 0.0872->0.0873 |
| 33 | `a0f27807-9590-46fd-8648-efdc63b42c48` | Founder CEO | Month 33 strategy will improve business health score. | False | 0.0056->0.0055 |
| 34 | `2f9a6560-2a4c-43b9-9f77-37689cab9d1c` | Growth Marketer | Month 34 CAC will be <= 46.10. | True | 0.6667->0.6765 |
| 34 | `2dbf2970-bb98-4b20-9e10-df7cfb344b83` | Product Manager | Month 34 conversion rate will be >= 0.0510. | True | 0.0900->0.0900 |
| 34 | `4488c134-c752-4612-98a5-299fbe99f3da` | Finance Controller | Month 34 gross revenue will be >= 77531.85. | True | 0.0900->0.0900 |
| 34 | `5b25810e-4e23-4ca7-b52e-688d56e57fcf` | Operations Manager | Month 34 stockout risk will be <= 0.1600. | True | 0.0873->0.0874 |
| 34 | `e6b05e77-a313-4019-aecc-36d93cf3dfd6` | Founder CEO | Month 34 strategy will improve business health score. | False | 0.0055->0.0053 |
| 35 | `84604f92-ecc8-4de7-adf2-ba2cb114240b` | Growth Marketer | Month 35 CAC will be <= 45.16. | True | 0.6765->0.6857 |
| 35 | `5f6c1749-a3dc-4ecb-9e1d-c34462a8c4a6` | Product Manager | Month 35 conversion rate will be >= 0.0486. | True | 0.0900->0.0900 |
| 35 | `b008940e-c1ad-421b-bb0d-1ddbee8f5e96` | Finance Controller | Month 35 gross revenue will be >= 80071.20. | True | 0.0900->0.0900 |
| 35 | `edde0939-cdbb-4a20-baee-576de02c1e21` | Operations Manager | Month 35 stockout risk will be <= 0.1600. | True | 0.0874->0.0874 |
| 35 | `14ed802c-e46f-412b-8c99-6f49f8812857` | Founder CEO | Month 35 strategy will improve business health score. | False | 0.0053->0.0051 |
| 36 | `3b3cf4df-1587-480c-a309-0d6326bb5b19` | Growth Marketer | Month 36 CAC will be <= 44.95. | True | 0.6857->0.6944 |
| 36 | `c1f04387-59c7-4d11-b426-80166207a90f` | Product Manager | Month 36 conversion rate will be >= 0.0521. | True | 0.0900->0.0900 |
| 36 | `6e63e5f2-e1a5-4478-9f92-e97f3b0ba457` | Finance Controller | Month 36 gross revenue will be >= 81905.18. | True | 0.0900->0.0900 |
| 36 | `b66bf3de-2ae1-48d6-9e68-4769ac29c2ef` | Operations Manager | Month 36 stockout risk will be <= 0.1600. | True | 0.0874->0.0875 |
| 36 | `af67eb07-f618-4e64-af40-6479bf463bea` | Founder CEO | Month 36 strategy will improve business health score. | False | 0.0051->0.0050 |

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
{"agent": "Growth Marketer", "calibration_delta": 0.1702, "claim": "Month 14 CAC will be <= 43.28.", "claim_source": "market_oracle_pre_decision_signal:seed=7319:month=14", "confidence": 0.62, "explanation": "CAC actual 41.38 <= 43.28", "month": 14, "outcome": true, "prediction_id": "c1368392-446d-44c9-a288-6c5cf798b398", "resolution_source": "market_oracle_monthly_actual:seed=7319:month=14", "run_id": "pawdent-bd40112b-810c-4361-8d4a-c347efd2c8cd", "seed": 7319, "simulated_date": "2028-02-01", "trust_after": 0.5, "trust_before": 0.3298}

## Biggest Wrong Call
{"agent": "Growth Marketer", "calibration_delta": -0.3968, "claim": "Month 5 CAC will be <= 39.72.", "claim_source": "market_oracle_pre_decision_signal:seed=7319:month=5", "confidence": 0.62, "explanation": "CAC actual 40.72 > 39.72", "month": 5, "outcome": false, "prediction_id": "e31d6a9d-7c70-487b-b320-a1914ae87e54", "resolution_source": "market_oracle_monthly_actual:seed=7319:month=5", "run_id": "pawdent-bd40112b-810c-4361-8d4a-c347efd2c8cd", "seed": 7319, "simulated_date": "2027-05-01", "trust_after": 0.0, "trust_before": 0.3968}

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
