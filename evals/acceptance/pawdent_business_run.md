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
| 1 | `241cd765-0ef1-49e9-a364-06a42a39746c` | Growth Marketer | Month 1 CAC will be <= 38.68. | False | 0.4960->0.4712 |
| 1 | `b6b8a9fe-a783-4c13-99be-9ab5cb7a4bd5` | Product Manager | Month 1 conversion rate will be >= 0.0401. | True | 0.4640->0.4408 |
| 1 | `162fcd0e-cd41-4bff-86a3-10d88bf2c518` | Finance Controller | Month 1 gross revenue will be >= 500.00. | True | 0.4800->0.4560 |
| 1 | `dd0c7c14-9302-4c34-9959-755bcb847d9f` | Operations Manager | Month 1 stockout risk will be <= 0.1000. | True | 0.5120->0.4864 |
| 1 | `c23dc630-c09e-4fc0-903b-03c99e7ef16b` | Founder CEO | Month 1 strategy will improve business health score. | True | 0.4480->0.4256 |
| 2 | `bf0ed614-636b-41d0-9719-cf9f216fdf41` | Growth Marketer | Month 2 CAC will be <= 36.38. | False | 0.4712->0.4464 |
| 2 | `f9dd9ab6-85fe-44c9-ac51-cea91feb80f5` | Product Manager | Month 2 conversion rate will be >= 0.0420. | True | 0.4408->0.4176 |
| 2 | `ca9763f2-feef-456f-8147-08728c8b9f5b` | Finance Controller | Month 2 gross revenue will be >= 699.60. | True | 0.4560->0.4320 |
| 2 | `d342b944-e38e-4a5c-a57e-a24df524c9d3` | Operations Manager | Month 2 stockout risk will be <= 0.1000. | False | 0.4864->0.4608 |
| 2 | `09584332-03a1-437e-b1e5-731c04a935d2` | Founder CEO | Month 2 strategy will improve business health score. | False | 0.4256->0.4032 |
| 3 | `76b5c942-691e-4ef2-9ffd-365a6d531c81` | Growth Marketer | Month 3 CAC will be <= 38.61. | False | 0.4464->0.4216 |
| 3 | `af1de8fb-ba5d-44dc-9127-89a9fc8249c4` | Product Manager | Month 3 conversion rate will be >= 0.0377. | True | 0.4176->0.3944 |
| 3 | `418d3a7c-6711-4c71-962d-0ffd1dc07b53` | Finance Controller | Month 3 gross revenue will be >= 1570.80. | True | 0.4320->0.4080 |
| 3 | `7fad3a40-2848-45bf-8db0-d5f9215d5cd5` | Operations Manager | Month 3 stockout risk will be <= 0.1000. | True | 0.4608->0.4352 |
| 3 | `ded4eccb-3d6c-4ab9-922a-01b19d321041` | Founder CEO | Month 3 strategy will improve business health score. | True | 0.4032->0.3808 |
| 4 | `b67d3a93-3db5-42ac-b589-b4b0fcdd02cb` | Growth Marketer | Month 4 CAC will be <= 39.83. | False | 0.4216->0.3968 |
| 4 | `938b5403-e647-4f3b-8b33-614bd0c2653a` | Product Manager | Month 4 conversion rate will be >= 0.0416. | True | 0.3944->0.3712 |
| 4 | `b7e59120-dfea-428f-83e9-381f7b3b698e` | Finance Controller | Month 4 gross revenue will be >= 3578.85. | True | 0.4080->0.3840 |
| 4 | `db83aa13-8e98-4d23-8976-c4cedfa9e2e0` | Operations Manager | Month 4 stockout risk will be <= 0.1000. | True | 0.4352->0.4096 |
| 4 | `8a5cdcbe-4bf5-4b95-88d9-ecd658658c3c` | Founder CEO | Month 4 strategy will improve business health score. | False | 0.3808->0.3584 |
| 5 | `e48409df-7057-44d2-9bac-d8fdc8dbb0e2` | Growth Marketer | Month 5 CAC will be <= 39.72. | False | 0.3968->0.0000 |
| 5 | `b85c68e1-9d4f-403e-8432-159cada11569` | Product Manager | Month 5 conversion rate will be >= 0.0407. | True | 0.3712->0.0900 |
| 5 | `23db4b36-0106-429b-b43b-518ee3382e9f` | Finance Controller | Month 5 gross revenue will be >= 6088.50. | True | 0.3840->0.0900 |
| 5 | `65379f94-3d8b-4859-babe-829f9dc8baed` | Operations Manager | Month 5 stockout risk will be <= 0.1600. | True | 0.4096->0.2800 |
| 5 | `3ace9666-7c3a-49c6-884c-2531ed11cbc7` | Founder CEO | Month 5 strategy will improve business health score. | False | 0.3584->0.3584 |
| 6 | `c10ba9bd-533c-4842-97a6-0965c5139866` | Growth Marketer | Month 6 CAC will be <= 42.34. | True | 0.0000->0.0150 |
| 6 | `2039fd69-aa2b-4f5c-b622-726e9950fe4a` | Product Manager | Month 6 conversion rate will be >= 0.0411. | True | 0.0900->0.0900 |
| 6 | `47afd7e0-6bcc-4db4-8b75-b5afd2c0337c` | Finance Controller | Month 6 gross revenue will be >= 8835.75. | True | 0.0900->0.0900 |
| 6 | `96189c3b-baf2-4256-9503-b1911cdf69fe` | Operations Manager | Month 6 stockout risk will be <= 0.1600. | True | 0.2800->0.1667 |
| 6 | `402f04f3-affc-4844-88a1-bf754027f8bd` | Founder CEO | Month 6 strategy will improve business health score. | False | 0.3584->0.1778 |
| 7 | `9a181f9c-f813-4d51-a27f-2be5643f1dd8` | Growth Marketer | Month 7 CAC will be <= 43.15. | True | 0.0150->0.0306 |
| 7 | `d771f9fc-6da6-41f6-8ffc-3b229bdc10f5` | Product Manager | Month 7 conversion rate will be >= 0.0407. | True | 0.0900->0.0900 |
| 7 | `aebb2f1b-2343-4b2d-a99c-a6d9f99c3567` | Finance Controller | Month 7 gross revenue will be >= 13691.70. | True | 0.0900->0.0900 |
| 7 | `37e96bc6-a7ca-49ea-b2bc-d9ba79dc5f6b` | Operations Manager | Month 7 stockout risk will be <= 0.1000. | True | 0.1667->0.1359 |
| 7 | `23215334-ba7c-4c53-9282-926b84c573e8` | Founder CEO | Month 7 strategy will improve business health score. | False | 0.1778->0.0805 |
| 8 | `b0bb6cac-2a58-4a45-9be7-9e6f382ec5a6` | Growth Marketer | Month 8 CAC will be <= 35.72. | False | 0.0306->0.0225 |
| 8 | `e4449879-0d0e-4065-a510-9c19e91cace4` | Product Manager | Month 8 conversion rate will be >= 0.0435. | True | 0.0900->0.0900 |
| 8 | `859ce7e2-3700-40ab-bacf-bf9b68b1d731` | Finance Controller | Month 8 gross revenue will be >= 18376.88. | True | 0.0900->0.0900 |
| 8 | `1b73ec78-f733-45d3-8aaf-1844464c2ac6` | Operations Manager | Month 8 stockout risk will be <= 0.1600. | True | 0.1359->0.1247 |
| 8 | `7329dc84-8668-404b-a0d1-ae58408ce4b4` | Founder CEO | Month 8 strategy will improve business health score. | False | 0.0805->0.0413 |
| 9 | `c893d95a-cc14-4080-9650-cfee6b472dc4` | Growth Marketer | Month 9 CAC will be <= 42.97. | False | 0.0225->0.0200 |
| 9 | `6718db3e-64e8-4f8f-ac51-b193dd036398` | Product Manager | Month 9 conversion rate will be >= 0.0443. | True | 0.0900->0.0900 |
| 9 | `f1dd8506-3bd1-4a5b-80ea-52a44d202a06` | Finance Controller | Month 9 gross revenue will be >= 22854.15. | True | 0.0900->0.0900 |
| 9 | `e9a30e53-e538-46de-9a06-3850081df39d` | Operations Manager | Month 9 stockout risk will be <= 0.1600. | True | 0.1247->0.1156 |
| 9 | `1506d510-731f-472a-bd7e-0d472e15b877` | Founder CEO | Month 9 strategy will improve business health score. | False | 0.0413->0.0311 |
| 10 | `7342cb51-1e62-428c-b773-418c7425dfe6` | Growth Marketer | Month 10 CAC will be <= 42.69. | True | 0.0200->0.0360 |
| 10 | `510c5f03-d16c-4909-8536-6ca5d3fc1be0` | Product Manager | Month 10 conversion rate will be >= 0.0464. | True | 0.0900->0.0900 |
| 10 | `eb6419b1-d8c2-41f6-870f-31973964bffc` | Finance Controller | Month 10 gross revenue will be >= 27286.88. | True | 0.0900->0.0900 |
| 10 | `ded64f5b-e828-4357-b203-dcaef62e714a` | Operations Manager | Month 10 stockout risk will be <= 0.1600. | True | 0.1156->0.1080 |
| 10 | `8464cd0a-54a3-4af4-9c43-cbd901e1a6ce` | Founder CEO | Month 10 strategy will improve business health score. | False | 0.0311->0.0240 |
| 11 | `c4df92f7-cc4f-4daa-a105-51c31bd76eda` | Growth Marketer | Month 11 CAC will be <= 35.97. | True | 0.0360->0.0684 |
| 11 | `63431bd7-d236-4f8c-89d8-1512e95d68c6` | Product Manager | Month 11 conversion rate will be >= 0.0487. | True | 0.0900->0.0900 |
| 11 | `f373de96-6ef0-4f95-9371-a5946784b385` | Finance Controller | Month 11 gross revenue will be >= 26819.10. | True | 0.0900->0.0900 |
| 11 | `52f3c063-ba06-4b88-9197-c72e733afcba` | Operations Manager | Month 11 stockout risk will be <= 0.1600. | True | 0.1080->0.1017 |
| 11 | `ebb569db-3c6d-48ff-b2ce-c36460700856` | Founder CEO | Month 11 strategy will improve business health score. | False | 0.0240->0.0188 |
| 12 | `b021ef50-acd7-4022-9979-9fc12c30dc40` | Growth Marketer | Month 12 CAC will be <= 40.82. | True | 0.0684->0.1823 |
| 12 | `f9811ba4-da2a-4cd5-8e7e-91f2fff1ce1d` | Product Manager | Month 12 conversion rate will be >= 0.0439. | True | 0.0900->0.0900 |
| 12 | `bec39f4b-a845-432c-93ed-921e7aa1abb0` | Finance Controller | Month 12 gross revenue will be >= 26722.58. | True | 0.0900->0.0900 |
| 12 | `f7d36074-af61-401d-b92d-4906bccb7f10` | Operations Manager | Month 12 stockout risk will be <= 0.1600. | True | 0.1017->0.0963 |
| 12 | `23d2a603-4a7b-44ed-a3e8-d62a36d58be1` | Founder CEO | Month 12 strategy will improve business health score. | False | 0.0188->0.0150 |
| 13 | `b24ee37b-52b1-446f-9257-f09c2c8f4b33` | Growth Marketer | Month 13 CAC will be <= 41.48. | True | 0.1823->0.3298 |
| 13 | `6b621ae0-fca5-4352-9b5a-0647b5903a15` | Product Manager | Month 13 conversion rate will be >= 0.0495. | True | 0.0900->0.0900 |
| 13 | `2542192a-8575-47df-a7d1-0e9a27998c94` | Finance Controller | Month 13 gross revenue will be >= 25022.25. | True | 0.0900->0.0900 |
| 13 | `4a622978-9c04-4375-bfee-69bbdb52ed7d` | Operations Manager | Month 13 stockout risk will be <= 0.1600. | True | 0.0963->0.0916 |
| 13 | `8a177764-ec43-49a7-9da1-cc93df3d9c9b` | Founder CEO | Month 13 strategy will improve business health score. | False | 0.0150->0.0138 |
| 14 | `7e0c4f07-8715-4354-9d11-16fdce47daf8` | Growth Marketer | Month 14 CAC will be <= 43.28. | True | 0.3298->0.5000 |
| 14 | `7db9ae4c-28cc-4924-9b7a-cce9b2516bd8` | Product Manager | Month 14 conversion rate will be >= 0.0486. | True | 0.0900->0.0900 |
| 14 | `33450051-fc38-4e0d-8b35-a1f4652f322b` | Finance Controller | Month 14 gross revenue will be >= 27591.30. | True | 0.0900->0.0900 |
| 14 | `b754559c-883f-401e-94ac-fbaafde94cf7` | Operations Manager | Month 14 stockout risk will be <= 0.1600. | True | 0.0916->0.0876 |
| 14 | `f7ecb384-a0fb-4c41-b090-dae5f5ea244d` | Founder CEO | Month 14 strategy will improve business health score. | False | 0.0138->0.0129 |
| 15 | `51133026-717e-4152-8e4d-aff5323cde9c` | Growth Marketer | Month 15 CAC will be <= 37.24. | False | 0.5000->0.3500 |
| 15 | `e3acdeb2-08fe-459c-940a-25f4b9d7768a` | Product Manager | Month 15 conversion rate will be >= 0.0454. | True | 0.0900->0.0900 |
| 15 | `0bcb8c5d-5fa0-4d13-865e-9ffb0ad2cae2` | Finance Controller | Month 15 gross revenue will be >= 30390.53. | True | 0.0900->0.0900 |
| 15 | `187b42af-a209-4c91-b43b-9cd29153a865` | Operations Manager | Month 15 stockout risk will be <= 0.1600. | True | 0.0876->0.0840 |
| 15 | `23330ffc-f554-4372-8062-e012e85f5add` | Founder CEO | Month 15 strategy will improve business health score. | False | 0.0129->0.0120 |
| 16 | `6e8a48d3-9ef1-4bb3-b620-49d6b403ad52` | Growth Marketer | Month 16 CAC will be <= 43.05. | True | 0.3500->0.5000 |
| 16 | `d82225d0-817e-42e5-a685-a7e99384a023` | Product Manager | Month 16 conversion rate will be >= 0.0464. | True | 0.0900->0.0900 |
| 16 | `03b958fd-e422-48d6-a137-a275203a49c2` | Finance Controller | Month 16 gross revenue will be >= 33546.15. | True | 0.0900->0.0900 |
| 16 | `4c242839-bddb-4c69-bff8-d899cdd0d4bf` | Operations Manager | Month 16 stockout risk will be <= 0.1600. | True | 0.0840->0.0844 |
| 16 | `b2b42796-0f77-462a-88e9-bd30a6514edb` | Founder CEO | Month 16 strategy will improve business health score. | False | 0.0120->0.0112 |
| 17 | `13d9b190-4246-4520-8563-cfea339c806c` | Growth Marketer | Month 17 CAC will be <= 42.95. | True | 0.5000->0.5294 |
| 17 | `82161929-b3a5-4ce3-a57f-5849106c4b5b` | Product Manager | Month 17 conversion rate will be >= 0.0471. | True | 0.0900->0.0900 |
| 17 | `9bfc188c-dc72-4b5e-9f8f-2f3450e032b4` | Finance Controller | Month 17 gross revenue will be >= 36516.15. | True | 0.0900->0.0900 |
| 17 | `ba59b4e2-5111-4437-8fe5-31e0fa1371c4` | Operations Manager | Month 17 stockout risk will be <= 0.1600. | True | 0.0844->0.0847 |
| 17 | `a19398ec-2664-4665-8d00-e87110150a36` | Founder CEO | Month 17 strategy will improve business health score. | False | 0.0112->0.0106 |
| 18 | `1e8a83b6-75d0-4a6d-acdf-9dbf8c1e7fd8` | Growth Marketer | Month 18 CAC will be <= 38.07. | False | 0.5294->0.5000 |
| 18 | `7bc97304-d57d-4b7f-afa5-c22a76de6b0d` | Product Manager | Month 18 conversion rate will be >= 0.0477. | True | 0.0900->0.0900 |
| 18 | `27913a0b-4763-42a7-b295-6755a9a7473a` | Finance Controller | Month 18 gross revenue will be >= 39040.65. | True | 0.0900->0.0900 |
| 18 | `a0ac40b5-07f3-4e92-bd9e-62fdc383ccec` | Operations Manager | Month 18 stockout risk will be <= 0.1600. | True | 0.0847->0.0850 |
| 18 | `898f56d8-fa78-49f0-8a8b-de046479e7f7` | Founder CEO | Month 18 strategy will improve business health score. | False | 0.0106->0.0100 |
| 19 | `1afd0293-aca1-4f30-9a28-a888b714d885` | Growth Marketer | Month 19 CAC will be <= 42.04. | False | 0.5000->0.3789 |
| 19 | `841947b7-f5b8-4581-8d99-aad6c2967787` | Product Manager | Month 19 conversion rate will be >= 0.0459. | True | 0.0900->0.0900 |
| 19 | `049821fb-1c39-4149-b090-8f024f2e742a` | Finance Controller | Month 19 gross revenue will be >= 40154.40. | True | 0.0900->0.0900 |
| 19 | `8f80f141-dbf2-450d-9d65-5a41eba712fe` | Operations Manager | Month 19 stockout risk will be <= 0.1600. | True | 0.0850->0.0853 |
| 19 | `43876e38-9a2f-4875-82ec-1a0314963f99` | Founder CEO | Month 19 strategy will improve business health score. | False | 0.0100->0.0095 |
| 20 | `43cbd26b-3fae-4362-9740-00d83bc9014f` | Growth Marketer | Month 20 CAC will be <= 40.82. | True | 0.3789->0.5000 |
| 20 | `f5f89604-8cc5-466f-b953-e1abf5aef94d` | Product Manager | Month 20 conversion rate will be >= 0.0505. | True | 0.0900->0.0900 |
| 20 | `ee172130-e2aa-49df-a79a-2f65fce6ce40` | Finance Controller | Month 20 gross revenue will be >= 41839.88. | True | 0.0900->0.0900 |
| 20 | `6130377c-66a4-4f28-9d5f-de8ac1de3548` | Operations Manager | Month 20 stockout risk will be <= 0.1600. | True | 0.0853->0.0855 |
| 20 | `fada2e9e-b1ec-454e-9fd5-8959ece6779d` | Founder CEO | Month 20 strategy will improve business health score. | False | 0.0095->0.0090 |
| 21 | `9cc58bc2-9d5c-42c7-96fa-f44a977fc855` | Growth Marketer | Month 21 CAC will be <= 41.78. | True | 0.5000->0.5238 |
| 21 | `03df5615-320f-4006-a606-d6488884a340` | Product Manager | Month 21 conversion rate will be >= 0.0497. | True | 0.0900->0.0900 |
| 21 | `2e3409e2-cc98-4a4f-8859-926cf00d27f7` | Finance Controller | Month 21 gross revenue will be >= 45017.78. | True | 0.0900->0.0900 |
| 21 | `ca136d3e-0e27-4abc-9b71-1a5028c059af` | Operations Manager | Month 21 stockout risk will be <= 0.1600. | True | 0.0855->0.0857 |
| 21 | `2da4ec82-6720-43f7-81d5-9b6ca2dd817f` | Founder CEO | Month 21 strategy will improve business health score. | False | 0.0090->0.0086 |
| 22 | `1a9f448c-ff70-4758-9693-15db9a0bbe60` | Growth Marketer | Month 22 CAC will be <= 46.73. | True | 0.5238->0.5455 |
| 22 | `71900ca9-4ad0-4770-bbbc-dffefe5cbcff` | Product Manager | Month 22 conversion rate will be >= 0.0514. | True | 0.0900->0.0900 |
| 22 | `f1be422c-c62d-4962-b901-af29cacdf30e` | Finance Controller | Month 22 gross revenue will be >= 47163.60. | True | 0.0900->0.0900 |
| 22 | `d7b1dcb3-e428-463a-8668-402659a3907d` | Operations Manager | Month 22 stockout risk will be <= 0.1600. | True | 0.0857->0.0859 |
| 22 | `7f0ec989-c66b-40d6-b08f-ecec4881ffc4` | Founder CEO | Month 22 strategy will improve business health score. | False | 0.0086->0.0082 |
| 23 | `b3812729-4b5d-4f03-890b-6109b501cf21` | Growth Marketer | Month 23 CAC will be <= 41.83. | False | 0.5455->0.5217 |
| 23 | `e961e1df-d7ae-4462-84f4-09271befd27d` | Product Manager | Month 23 conversion rate will be >= 0.0502. | True | 0.0900->0.0900 |
| 23 | `9fe02699-168f-45d9-b512-1bf1e71935f2` | Finance Controller | Month 23 gross revenue will be >= 49160.93. | True | 0.0900->0.0900 |
| 23 | `2e1b0e25-12a7-4a81-affa-7943b492d0ca` | Operations Manager | Month 23 stockout risk will be <= 0.1600. | True | 0.0859->0.0861 |
| 23 | `98a0d80c-8590-49db-a5ea-0d475622754b` | Founder CEO | Month 23 strategy will improve business health score. | False | 0.0082->0.0078 |
| 24 | `8bdd4cdb-aa60-45b4-86c2-09933bf956ac` | Growth Marketer | Month 24 CAC will be <= 45.06. | True | 0.5217->0.5417 |
| 24 | `08ed21f0-2cfa-4484-af29-9edc4a04a4e8` | Product Manager | Month 24 conversion rate will be >= 0.0530. | True | 0.0900->0.0900 |
| 24 | `b8a2ae92-38c4-43b3-b478-5f3ad1a1bcd2` | Finance Controller | Month 24 gross revenue will be >= 51247.35. | True | 0.0900->0.0900 |
| 24 | `513e1929-946c-4bf7-a78e-37d5573506a7` | Operations Manager | Month 24 stockout risk will be <= 0.1600. | True | 0.0861->0.0862 |
| 24 | `87344b6e-ce93-4ee6-8308-c91dcf015430` | Founder CEO | Month 24 strategy will improve business health score. | False | 0.0078->0.0075 |
| 25 | `8e8a92b3-494e-4fdd-9524-0ec0dcdb3d85` | Growth Marketer | Month 25 CAC will be <= 46.38. | True | 0.5417->0.5600 |
| 25 | `d730f1c5-0ab7-4690-b308-36b5cab915b9` | Product Manager | Month 25 conversion rate will be >= 0.0514. | True | 0.0900->0.0900 |
| 25 | `e834cd84-e6ff-4633-8d66-f7ccba44a0c7` | Finance Controller | Month 25 gross revenue will be >= 53081.33. | True | 0.0900->0.0900 |
| 25 | `49d14fd6-c688-496e-af51-5a8d67aa226e` | Operations Manager | Month 25 stockout risk will be <= 0.1600. | True | 0.0862->0.0864 |
| 25 | `3cce486d-4be3-4caa-a224-44a5a078503c` | Founder CEO | Month 25 strategy will improve business health score. | False | 0.0075->0.0072 |
| 26 | `5a0fd72b-1b0b-4725-80f8-05ad1424d48f` | Growth Marketer | Month 26 CAC will be <= 45.89. | True | 0.5600->0.5769 |
| 26 | `1b3b7c06-040b-4aa5-a3b0-e12bd67cd334` | Product Manager | Month 26 conversion rate will be >= 0.0506. | True | 0.0900->0.0900 |
| 26 | `fd9b50e2-ba10-488e-b4e3-8a7897862f92` | Finance Controller | Month 26 gross revenue will be >= 55709.78. | True | 0.0900->0.0900 |
| 26 | `6a2981d1-7cf5-4ec6-911b-de50e779407c` | Operations Manager | Month 26 stockout risk will be <= 0.1600. | True | 0.0864->0.0865 |
| 26 | `c37d1228-75ad-41b3-87b9-ed4c234396f1` | Founder CEO | Month 26 strategy will improve business health score. | False | 0.0072->0.0069 |
| 27 | `3d10badc-a14d-4eb9-941b-bc472810fa75` | Growth Marketer | Month 27 CAC will be <= 41.00. | True | 0.5769->0.5926 |
| 27 | `6b0be219-6500-428c-9e2c-71e43f2f2161` | Product Manager | Month 27 conversion rate will be >= 0.0528. | True | 0.0900->0.0900 |
| 27 | `e2de7e22-3be9-4828-babe-820dfb99245c` | Finance Controller | Month 27 gross revenue will be >= 58880.25. | True | 0.0900->0.0900 |
| 27 | `b473f31a-ecf2-4fdc-b41d-ccae260a0d1f` | Operations Manager | Month 27 stockout risk will be <= 0.1600. | True | 0.0865->0.0867 |
| 27 | `beef5117-3712-43c4-94a1-89fc0e94b2a2` | Founder CEO | Month 27 strategy will improve business health score. | False | 0.0069->0.0067 |
| 28 | `e60a053b-5aaf-4724-982a-08de51f4b703` | Growth Marketer | Month 28 CAC will be <= 47.19. | True | 0.5926->0.6071 |
| 28 | `0e1b3367-1074-4631-bbd9-d8871a3d1723` | Product Manager | Month 28 conversion rate will be >= 0.0471. | True | 0.0900->0.0900 |
| 28 | `da3cb82c-a789-456b-aa20-c5a9f813a7cd` | Finance Controller | Month 28 gross revenue will be >= 61315.65. | True | 0.0900->0.0900 |
| 28 | `dc545fd2-274e-4c92-abbc-b1a8f80ff525` | Operations Manager | Month 28 stockout risk will be <= 0.1600. | True | 0.0867->0.0868 |
| 28 | `0ea62413-ab15-47c0-8139-190c8e16e409` | Founder CEO | Month 28 strategy will improve business health score. | False | 0.0067->0.0064 |
| 29 | `121e3b19-bb49-4ed3-b38e-46696dcf281d` | Growth Marketer | Month 29 CAC will be <= 47.29. | True | 0.6071->0.6207 |
| 29 | `8898fdc8-5a1f-4a63-bd25-f1ff8db28d60` | Product Manager | Month 29 conversion rate will be >= 0.0473. | True | 0.0900->0.0900 |
| 29 | `825bd5fe-a116-47ce-8cb6-5d421a470366` | Finance Controller | Month 29 gross revenue will be >= 64627.20. | True | 0.0900->0.0900 |
| 29 | `03784f32-8272-4d4d-8a77-3ba86540c79a` | Operations Manager | Month 29 stockout risk will be <= 0.1600. | True | 0.0868->0.0869 |
| 29 | `4b615dbe-7542-49b9-b74b-11c4bad77def` | Founder CEO | Month 29 strategy will improve business health score. | False | 0.0064->0.0062 |
| 30 | `c7b38e12-b9a7-4f33-b8b6-fbb80230bf87` | Growth Marketer | Month 30 CAC will be <= 46.84. | True | 0.6207->0.6333 |
| 30 | `a95d06d9-d5e5-43bd-8915-49c02c4ecbcf` | Product Manager | Month 30 conversion rate will be >= 0.0509. | True | 0.0900->0.0900 |
| 30 | `019708a2-d95a-443a-a65c-5e99e42fedd2` | Finance Controller | Month 30 gross revenue will be >= 66513.15. | True | 0.0900->0.0900 |
| 30 | `c8430cad-d974-4ff4-ae7e-51e961235c12` | Operations Manager | Month 30 stockout risk will be <= 0.1600. | True | 0.0869->0.0870 |
| 30 | `9a77accb-fa5b-4891-a825-52b6b6dc30d3` | Founder CEO | Month 30 strategy will improve business health score. | False | 0.0062->0.0060 |
| 31 | `88e70a6e-b1a5-408e-abc9-2a3132d42eb0` | Growth Marketer | Month 31 CAC will be <= 49.10. | True | 0.6333->0.6452 |
| 31 | `b4e8644e-461d-4a3d-a215-ea96e9b5d6ff` | Product Manager | Month 31 conversion rate will be >= 0.0482. | True | 0.0900->0.0900 |
| 31 | `d891dad9-0021-47bc-8e4b-54612bf4b4bc` | Finance Controller | Month 31 gross revenue will be >= 69364.35. | True | 0.0900->0.0900 |
| 31 | `855dd716-f6bb-4968-88d1-4103e9dc7876` | Operations Manager | Month 31 stockout risk will be <= 0.1600. | True | 0.0870->0.0871 |
| 31 | `c8cdfd03-0085-4d14-aad9-df590e50c713` | Founder CEO | Month 31 strategy will improve business health score. | False | 0.0060->0.0058 |
| 32 | `20964cbb-74fb-455c-a856-2c7fb1ceb1d9` | Growth Marketer | Month 32 CAC will be <= 49.07. | True | 0.6452->0.6562 |
| 32 | `8a57cdd9-2e18-479a-98e2-9ad8e37d6ae1` | Product Manager | Month 32 conversion rate will be >= 0.0459. | True | 0.0900->0.0900 |
| 32 | `adcd2e7e-81b2-49e5-8c62-2e2b3988a001` | Finance Controller | Month 32 gross revenue will be >= 72007.65. | True | 0.0900->0.0900 |
| 32 | `f77d2fa9-3ae1-4f67-9278-5111edf4f3a6` | Operations Manager | Month 32 stockout risk will be <= 0.1600. | True | 0.0871->0.0872 |
| 32 | `0c329186-51e3-42ea-9165-ecc13f2eacf3` | Founder CEO | Month 32 strategy will improve business health score. | False | 0.0058->0.0056 |
| 33 | `7aabaa7d-916c-4743-aefa-5625a68938be` | Growth Marketer | Month 33 CAC will be <= 46.55. | True | 0.6562->0.6667 |
| 33 | `dab33504-3dad-4e16-aa53-cc40f6305b23` | Product Manager | Month 33 conversion rate will be >= 0.0469. | True | 0.0900->0.0900 |
| 33 | `90f7dc89-c969-498a-90a2-020e74415746` | Finance Controller | Month 33 gross revenue will be >= 74873.70. | True | 0.0900->0.0900 |
| 33 | `ef8ec6c3-def5-4756-b65b-052fcceab6de` | Operations Manager | Month 33 stockout risk will be <= 0.1600. | True | 0.0872->0.0873 |
| 33 | `4c336178-efe3-44b4-ae36-024b8c8bf803` | Founder CEO | Month 33 strategy will improve business health score. | False | 0.0056->0.0055 |
| 34 | `a7a89b4b-453d-410a-9f0d-be47a900fc2a` | Growth Marketer | Month 34 CAC will be <= 46.10. | True | 0.6667->0.6765 |
| 34 | `079f6406-42f6-4651-81db-da7a0d663cf7` | Product Manager | Month 34 conversion rate will be >= 0.0510. | True | 0.0900->0.0900 |
| 34 | `3839481b-414c-4a58-8a4c-15e6ca03b20c` | Finance Controller | Month 34 gross revenue will be >= 77531.85. | True | 0.0900->0.0900 |
| 34 | `13302027-7b0f-4354-afa2-b7ae0acb4efc` | Operations Manager | Month 34 stockout risk will be <= 0.1600. | True | 0.0873->0.0874 |
| 34 | `4268d22c-9a37-447a-89d2-4271e284c3b9` | Founder CEO | Month 34 strategy will improve business health score. | False | 0.0055->0.0053 |
| 35 | `b653f1e9-38b3-4648-8271-648a25475c46` | Growth Marketer | Month 35 CAC will be <= 45.16. | True | 0.6765->0.6857 |
| 35 | `c4480afd-c29f-4377-8fd5-59b4c5d4e19b` | Product Manager | Month 35 conversion rate will be >= 0.0486. | True | 0.0900->0.0900 |
| 35 | `2da66598-1626-4dfa-a9d1-feb499ef5457` | Finance Controller | Month 35 gross revenue will be >= 80071.20. | True | 0.0900->0.0900 |
| 35 | `2b5f1a32-4a95-438f-a28b-44afd7a6e3a9` | Operations Manager | Month 35 stockout risk will be <= 0.1600. | True | 0.0874->0.0874 |
| 35 | `9b3b9c05-7a1f-4539-a4c7-b1a2fc8e5e3b` | Founder CEO | Month 35 strategy will improve business health score. | False | 0.0053->0.0051 |
| 36 | `de4b559a-770c-42d3-9ca6-5ed0da4aa881` | Growth Marketer | Month 36 CAC will be <= 44.95. | True | 0.6857->0.6944 |
| 36 | `970bcdb0-f9c9-4cd0-9bb9-e26709892d43` | Product Manager | Month 36 conversion rate will be >= 0.0521. | True | 0.0900->0.0900 |
| 36 | `17c8c045-24ee-49aa-b1e0-30b6d8b0457d` | Finance Controller | Month 36 gross revenue will be >= 81905.18. | True | 0.0900->0.0900 |
| 36 | `eb9bd592-3d09-4d13-acbf-9985a27e880a` | Operations Manager | Month 36 stockout risk will be <= 0.1600. | True | 0.0874->0.0875 |
| 36 | `d13efe58-e4fa-4f12-9603-ac3486fd54ee` | Founder CEO | Month 36 strategy will improve business health score. | False | 0.0051->0.0050 |

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
{"agent": "Growth Marketer", "calibration_delta": 0.1702, "claim": "Month 14 CAC will be <= 43.28.", "claim_source": "market_oracle_pre_decision_signal:seed=7319:month=14", "confidence": 0.62, "explanation": "CAC actual 41.38 <= 43.28", "month": 14, "outcome": true, "prediction_id": "7e0c4f07-8715-4354-9d11-16fdce47daf8", "resolution_source": "market_oracle_monthly_actual:seed=7319:month=14", "run_id": "pawdent-c74782ee-9211-4d3a-bc65-e8fa8eee54f5", "seed": 7319, "simulated_date": "2028-02-01", "trust_after": 0.5, "trust_before": 0.3298}

## Biggest Wrong Call
{"agent": "Growth Marketer", "calibration_delta": -0.3968, "claim": "Month 5 CAC will be <= 39.72.", "claim_source": "market_oracle_pre_decision_signal:seed=7319:month=5", "confidence": 0.62, "explanation": "CAC actual 40.72 > 39.72", "month": 5, "outcome": false, "prediction_id": "e48409df-7057-44d2-9bac-d8fdc8dbb0e2", "resolution_source": "market_oracle_monthly_actual:seed=7319:month=5", "run_id": "pawdent-c74782ee-9211-4d3a-bc65-e8fa8eee54f5", "seed": 7319, "simulated_date": "2027-05-01", "trust_after": 0.0, "trust_before": 0.3968}

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
