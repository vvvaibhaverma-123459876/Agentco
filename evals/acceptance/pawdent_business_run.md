# PawDent Business Simulation

## Institution Charter
**Name:** Pet Care Venture Institution
**Mission:** Launch and operate PawDent for 3 simulated years while improving decisions through verifiable calibration.

## Product Launched
`PawDent`: Monthly dog dental-care kit with dental chews, brushing wipes, breath strips, and a mobile reminder/tracking experience.

## Market Simulator Contract
The market simulator is a deterministic oracle, not an agent. It fabricates market reality only from seed, month, product state, pricing, channel spend, customer satisfaction, competitor pressure, seasonality, supply reliability, and macro shock state. Every monthly actual carries `source_id`, `seed`, `month`, `simulated_date`, and `market_state_hash`.
- Seed: `9999`
- First market_state_hash: `dd14c28764d3688e28acdfd268dd83add0d7c24c3b12ff99e2fb2964bcaa6657`

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
| 1 | 2027-01-01 | idea exploration and customer discovery | 71 | 1704.00 | -20713.15 | 229286.85 | 47 | dd14c28764d3 |
| 2 | 2027-02-01 | idea exploration and customer discovery | 133 | 3154.76 | -20339.78 | 208947.07 | 44 | 920c6b5d6a4d |
| 3 | 2027-03-01 | idea exploration and customer discovery | 187 | 4578.40 | -20025.35 | 188921.72 | 53 | 65e583bdae4a |
| 4 | 2027-04-01 | MVP design and pilot | 352 | 9779.10 | -23924.84 | 164996.88 | 52 | 32bffc3b5546 |
| 5 | 2027-05-01 | MVP design and pilot | 507 | 14254.60 | -22747.24 | 142249.64 | 51 | ddefa17f4134 |
| 6 | 2027-06-01 | MVP design and pilot | 588 | 15890.39 | -19411.70 | 122837.94 | 59 | df85f9fe22f2 |
| 7 | 2027-07-01 | public launch and early growth | 708 | 18840.40 | -37623.24 | 85214.70 | 55 | 21e71885278a |
| 8 | 2027-08-01 | public launch and early growth | 844 | 22484.53 | -27158.35 | 58056.35 | 61 | 4dc551a57ff3 |
| 9 | 2027-09-01 | public launch and early growth | 1005 | 26599.67 | -28047.06 | 30009.29 | 63 | 2f6c780da9f8 |
| 10 | 2027-10-01 | public launch and early growth | 1129 | 29723.21 | -28020.54 | 1988.75 | 67 | 836e85c0091e |
| 11 | 2027-11-01 | public launch and early growth | 1324 | 34978.69 | -27816.16 | -25827.41 | 60 | 2c0bd556ced1 |
| 12 | 2027-12-01 | public launch and early growth | 1480 | 39416.10 | -27670.25 | -53497.66 | 61 | 2e73802fbec2 |
| 13 | 2028-01-01 | scaling, retention, partnerships, and product iterations | 1544 | 39887.11 | -21188.47 | -74686.13 | 61 | f2f78f1aa330 |
| 14 | 2028-02-01 | scaling, retention, partnerships, and product iterations | 1602 | 42614.01 | -21414.20 | -96100.33 | 72 | 61aa539af016 |
| 15 | 2028-03-01 | scaling, retention, partnerships, and product iterations | 1663 | 44349.31 | -19994.24 | -116094.57 | 67 | 23c13545ae79 |
| 16 | 2028-04-01 | scaling, retention, partnerships, and product iterations | 1726 | 45638.39 | -20243.88 | -136338.45 | 73 | 94e68fe1c088 |
| 17 | 2028-05-01 | scaling, retention, partnerships, and product iterations | 1805 | 47200.16 | -20379.22 | -156717.67 | 73 | 4fee7306f8b8 |
| 18 | 2028-06-01 | scaling, retention, partnerships, and product iterations | 1877 | 49381.68 | -20583.72 | -177301.39 | 67 | cd560af77539 |
| 19 | 2028-07-01 | scaling, retention, partnerships, and product iterations | 1940 | 51216.14 | -31552.02 | -208853.41 | 70 | d42ac8aa0397 |
| 20 | 2028-08-01 | scaling, retention, partnerships, and product iterations | 2049 | 51761.52 | -32925.94 | -241779.35 | 76 | 955e7b002766 |
| 21 | 2028-09-01 | scaling, retention, partnerships, and product iterations | 2181 | 55777.50 | -35094.16 | -276873.51 | 74 | 3a79550374a2 |
| 22 | 2028-10-01 | scaling, retention, partnerships, and product iterations | 2308 | 57810.28 | -32619.25 | -309492.76 | 75 | b01f66522c4e |
| 23 | 2028-11-01 | scaling, retention, partnerships, and product iterations | 2445 | 62371.64 | -33224.67 | -342717.43 | 74 | c38ec276c168 |
| 24 | 2028-12-01 | scaling, retention, partnerships, and product iterations | 2694 | 63883.83 | -34925.60 | -377643.03 | 69 | e5b268d902af |
| 25 | 2029-01-01 | maturity, competition, survival, expansion, or shutdown | 2914 | 74964.96 | -34005.02 | -411648.05 | 72 | b79bcbeb278f |
| 26 | 2029-02-01 | maturity, competition, survival, expansion, or shutdown | 3282 | 75510.34 | -34779.80 | -446427.85 | 69 | 4299e1b248a5 |
| 27 | 2029-03-01 | maturity, competition, survival, expansion, or shutdown | 3543 | 91648.63 | -31404.88 | -477832.73 | 78 | 7cca9f69a198 |
| 28 | 2029-04-01 | maturity, competition, survival, expansion, or shutdown | 3873 | 91152.83 | -40396.21 | -518228.94 | 66 | e481a0c7b586 |
| 29 | 2029-05-01 | maturity, competition, survival, expansion, or shutdown | 4200 | 104762.54 | -37309.27 | -555538.21 | 71 | 1da609038712 |
| 30 | 2029-06-01 | maturity, competition, survival, expansion, or shutdown | 4478 | 108828.10 | -30703.16 | -586241.37 | 69 | 42691816b142 |
| 31 | 2029-07-01 | maturity, competition, survival, expansion, or shutdown | 4783 | 117405.44 | -27214.27 | -613455.64 | 70 | 2b98a1cab5eb |
| 32 | 2029-08-01 | maturity, competition, survival, expansion, or shutdown | 5090 | 123974.79 | -25065.32 | -638520.96 | 69 | a7c748da3133 |
| 33 | 2029-09-01 | maturity, competition, survival, expansion, or shutdown | 5301 | 132056.33 | -23734.98 | -662255.94 | 73 | 148908bfd82b |
| 34 | 2029-10-01 | maturity, competition, survival, expansion, or shutdown | 5535 | 134609.70 | -24605.71 | -686861.65 | 71 | b00d17112cde |
| 35 | 2029-11-01 | maturity, competition, survival, expansion, or shutdown | 5730 | 142691.24 | -19916.19 | -706777.84 | 68 | c4faeb41fd64 |
| 36 | 2029-12-01 | maturity, competition, survival, expansion, or shutdown | 6003 | 144087.09 | -24790.27 | -731568.11 | 72 | a4a8321203e0 |

## Monthly Agent Decision Table
See the call ledger above and `pawdent_agent_decisions.jsonl` for every structured decision event.

## Pre-Registered Claims and Calibration
| Month | Prediction id | Agent | Claim | Outcome | Trust change |
|---:|---|---|---|---|---|
| 1 | `a1412cf9-b941-4ee5-be49-2736e63f4380` | Growth Marketer | Month 1 CAC will be <= 39.47. | False | 0.4960->0.4712 |
| 1 | `897d2fde-48db-4101-9eb9-17070d4ac6fd` | Product Manager | Month 1 conversion rate will be >= 0.0405. | True | 0.4640->0.4408 |
| 1 | `d7442b28-e174-4469-85a1-76c91f36aa74` | Finance Controller | Month 1 gross revenue will be >= 500.00. | True | 0.4800->0.4560 |
| 1 | `53cdae42-fba8-4e52-9cd6-164b3f1c217d` | Operations Manager | Month 1 stockout risk will be <= 0.1000. | True | 0.5120->0.4864 |
| 1 | `ae112ee4-4dd6-463d-bfdc-b30de90fec09` | Founder CEO | Month 1 strategy will improve business health score. | True | 0.4480->0.4256 |
| 2 | `6b5588b3-0143-4a73-b609-f653539e7bb4` | Growth Marketer | Month 2 CAC will be <= 37.24. | False | 0.4712->0.4464 |
| 2 | `58bc6968-7a72-4672-a0f8-0a76baa7571a` | Product Manager | Month 2 conversion rate will be >= 0.0377. | True | 0.4408->0.4176 |
| 2 | `26a0e635-261c-40cf-af8a-cbf06b48601c` | Finance Controller | Month 2 gross revenue will be >= 926.27. | True | 0.4560->0.4320 |
| 2 | `d5606c67-b092-4300-910c-4140d9436731` | Operations Manager | Month 2 stockout risk will be <= 0.1000. | False | 0.4864->0.4608 |
| 2 | `7f0b2296-52c5-4050-b277-eb2ce1a2cb4c` | Founder CEO | Month 2 strategy will improve business health score. | False | 0.4256->0.4032 |
| 3 | `26672176-de84-41a4-8d50-45e2b43afad6` | Growth Marketer | Month 3 CAC will be <= 36.61. | False | 0.4464->0.4216 |
| 3 | `2056f612-f2fc-465d-b98b-3ca71ecca38d` | Product Manager | Month 3 conversion rate will be >= 0.0440. | True | 0.4176->0.3944 |
| 3 | `164a96c9-24fd-42aa-a9ff-7ba1bb0b9c2f` | Finance Controller | Month 3 gross revenue will be >= 1726.34. | True | 0.4320->0.4080 |
| 3 | `b299b6f2-12dc-468b-aa8b-27d14726be37` | Operations Manager | Month 3 stockout risk will be <= 0.1000. | True | 0.4608->0.4352 |
| 3 | `9c9e0609-d295-432f-b76b-3a622a515127` | Founder CEO | Month 3 strategy will improve business health score. | True | 0.4032->0.3808 |
| 4 | `c59a1d55-4a69-45c2-88db-03372ed355e0` | Growth Marketer | Month 4 CAC will be <= 38.30. | False | 0.4216->0.3968 |
| 4 | `eb059729-e486-4eb0-86cb-9c3ca196824e` | Product Manager | Month 4 conversion rate will be >= 0.0402. | True | 0.3944->0.3712 |
| 4 | `b0648a06-328b-4d07-bdf6-95576efc8271` | Finance Controller | Month 4 gross revenue will be >= 3735.88. | True | 0.4080->0.3840 |
| 4 | `d2d17fa7-97ff-45c2-98cb-dd6047c2596a` | Operations Manager | Month 4 stockout risk will be <= 0.1000. | True | 0.4352->0.4096 |
| 4 | `e6252ae6-f6ee-41cd-a1a9-665ed09a5409` | Founder CEO | Month 4 strategy will improve business health score. | False | 0.3808->0.3584 |
| 5 | `b739fc1e-49cc-4fd9-a799-6da82c71ecfd` | Growth Marketer | Month 5 CAC will be <= 35.23. | False | 0.3968->0.0000 |
| 5 | `4607faf9-b366-4d47-afc7-39acf0253c6c` | Product Manager | Month 5 conversion rate will be >= 0.0460. | True | 0.3712->0.0900 |
| 5 | `8f2fc947-8884-4b08-9744-52db51484a46` | Finance Controller | Month 5 gross revenue will be >= 6104.23. | True | 0.3840->0.0900 |
| 5 | `4adeb386-5927-4dab-85a6-ac7ab7f7baa9` | Operations Manager | Month 5 stockout risk will be <= 0.1000. | True | 0.4096->0.2800 |
| 5 | `5acdefe8-b393-4c81-a944-6d5695ab264c` | Founder CEO | Month 5 strategy will improve business health score. | False | 0.3584->0.3584 |
| 6 | `8f2fad0b-5a33-4ae2-8329-226d5ec6a8d2` | Growth Marketer | Month 6 CAC will be <= 42.14. | True | 0.0000->0.0150 |
| 6 | `522fa488-f9f2-4758-b388-61721cee185e` | Product Manager | Month 6 conversion rate will be >= 0.0435. | True | 0.0900->0.0900 |
| 6 | `f8f8f607-34bd-4fb7-a450-0f73be53e75b` | Finance Controller | Month 6 gross revenue will be >= 7867.11. | True | 0.0900->0.0900 |
| 6 | `9f7b75ce-a14e-4d6d-8fcf-76a5a8499c9c` | Operations Manager | Month 6 stockout risk will be <= 0.1000. | True | 0.2800->0.1667 |
| 6 | `e3cabed8-e524-47f5-835b-2e99ce911358` | Founder CEO | Month 6 strategy will improve business health score. | False | 0.3584->0.1778 |
| 7 | `30226ebd-da29-4670-8725-bac52f4bbb8e` | Growth Marketer | Month 7 CAC will be <= 37.01. | False | 0.0150->0.0129 |
| 7 | `607028f9-0b9b-438e-83ae-c6fec5570d04` | Product Manager | Month 7 conversion rate will be >= 0.0397. | True | 0.0900->0.0900 |
| 7 | `2f83139a-4d5e-40e8-9245-2be87664a8e3` | Finance Controller | Month 7 gross revenue will be >= 10403.12. | True | 0.0900->0.0900 |
| 7 | `86b0b2cf-d638-4344-a493-f965bf3704ed` | Operations Manager | Month 7 stockout risk will be <= 0.1600. | True | 0.1667->0.1359 |
| 7 | `3a57b4d4-84aa-44b0-9911-d2af972dc509` | Founder CEO | Month 7 strategy will improve business health score. | False | 0.1778->0.0805 |
| 8 | `8a4b6981-021d-4fb1-8cbf-eaba91bc8b00` | Growth Marketer | Month 8 CAC will be <= 38.63. | False | 0.0129->0.0112 |
| 8 | `3101aa03-d283-443f-b323-70119777dc2c` | Product Manager | Month 8 conversion rate will be >= 0.0437. | True | 0.0900->0.0900 |
| 8 | `4651ed40-2dbc-4844-a7c1-2031e4978862` | Finance Controller | Month 8 gross revenue will be >= 12346.04. | True | 0.0900->0.0900 |
| 8 | `12e8ae8a-3d10-4451-be03-ba74e7b9db3d` | Operations Manager | Month 8 stockout risk will be <= 0.1600. | True | 0.1359->0.1247 |
| 8 | `165d6cf8-1d4b-4760-8f3f-14a969ecba18` | Founder CEO | Month 8 strategy will improve business health score. | False | 0.0805->0.0413 |
| 9 | `858b7265-00ee-4bd8-9aa7-52fe58f010c5` | Growth Marketer | Month 9 CAC will be <= 36.05. | False | 0.0112->0.0100 |
| 9 | `b2dcd952-f495-478a-a2e2-c55b963f36c2` | Product Manager | Month 9 conversion rate will be >= 0.0447. | True | 0.0900->0.0900 |
| 9 | `ac0bcc40-f934-432a-aab6-f82425bdd864` | Finance Controller | Month 9 gross revenue will be >= 14507.11. | True | 0.0900->0.0900 |
| 9 | `10b2a8d3-540f-436c-b9a0-3c9dee34a7f7` | Operations Manager | Month 9 stockout risk will be <= 0.1600. | True | 0.1247->0.1156 |
| 9 | `ed81f0a1-b935-4c6a-b5b1-a987b6b50d83` | Founder CEO | Month 9 strategy will improve business health score. | False | 0.0413->0.0311 |
| 10 | `11fb374a-1dc0-4dec-9c96-3ca29cd32daf` | Growth Marketer | Month 10 CAC will be <= 36.53. | False | 0.0100->0.0090 |
| 10 | `76ceace8-04bb-460d-b612-393da038dd15` | Product Manager | Month 10 conversion rate will be >= 0.0444. | True | 0.0900->0.0900 |
| 10 | `d4825717-efc3-454a-bef8-25470624254c` | Finance Controller | Month 10 gross revenue will be >= 17009.04. | True | 0.0900->0.0900 |
| 10 | `bceedf54-4697-4df4-af37-d151c8d49c94` | Operations Manager | Month 10 stockout risk will be <= 0.1600. | True | 0.1156->0.1080 |
| 10 | `ef0be418-a6b9-4a51-bf7f-f7ab7d9d4033` | Founder CEO | Month 10 strategy will improve business health score. | False | 0.0311->0.0240 |
| 11 | `af8d7495-0ae1-48a2-b05f-53cf6123f7cb` | Growth Marketer | Month 11 CAC will be <= 39.24. | False | 0.0090->0.0082 |
| 11 | `51a4b7e0-4dda-4a87-ba23-22a7721e0b47` | Product Manager | Month 11 conversion rate will be >= 0.0418. | True | 0.0900->0.0900 |
| 11 | `3b1b052b-a817-4b2c-8b59-44d5e22eea3f` | Finance Controller | Month 11 gross revenue will be >= 19006.49. | True | 0.0900->0.0900 |
| 11 | `9dfb4e1c-09c1-4c2d-a2a5-d1c44073f430` | Operations Manager | Month 11 stockout risk will be <= 0.1600. | True | 0.1080->0.1017 |
| 11 | `a0ab3586-0b3c-4590-a234-bfa959f9cba9` | Founder CEO | Month 11 strategy will improve business health score. | False | 0.0240->0.0188 |
| 12 | `a924ecb7-b36c-420d-b208-b3e17d0ea383` | Growth Marketer | Month 12 CAC will be <= 39.96. | False | 0.0082->0.0075 |
| 12 | `47a13bef-64db-4c68-8db6-5038b5032d45` | Product Manager | Month 12 conversion rate will be >= 0.0433. | True | 0.0900->0.0900 |
| 12 | `48fda515-c495-4701-86a3-8be04431d73a` | Finance Controller | Month 12 gross revenue will be >= 21972.00. | True | 0.0900->0.0900 |
| 12 | `0165e09d-e910-4c78-a99a-5edebe34589d` | Operations Manager | Month 12 stockout risk will be <= 0.1600. | True | 0.1017->0.0963 |
| 12 | `40a3ceda-1fd6-433a-9f3b-d88647d51970` | Founder CEO | Month 12 strategy will improve business health score. | False | 0.0188->0.0150 |
| 13 | `70c02615-6f8d-41e9-85d4-ca4ec57755ce` | Growth Marketer | Month 13 CAC will be <= 43.20. | True | 0.0075->0.0138 |
| 13 | `c7bba9fb-8714-47f4-b148-379eab6c794b` | Product Manager | Month 13 conversion rate will be >= 0.0448. | True | 0.0900->0.0900 |
| 13 | `068d9af5-65a4-43a5-a352-ff85d3d47bb5` | Finance Controller | Month 13 gross revenue will be >= 21794.75. | True | 0.0900->0.0900 |
| 13 | `70c69e71-8e11-4cfd-9b1f-6c4fa2e81035` | Operations Manager | Month 13 stockout risk will be <= 0.1600. | True | 0.0963->0.0916 |
| 13 | `5f5c18fc-2fbf-47df-b210-d5e05a613e8e` | Founder CEO | Month 13 strategy will improve business health score. | False | 0.0150->0.0138 |
| 14 | `3e795949-aad4-40bc-8633-d63d0d64c565` | Growth Marketer | Month 14 CAC will be <= 37.08. | True | 0.0138->0.0193 |
| 14 | `0fe6e909-c155-408f-8ca4-68ef63ddab9d` | Product Manager | Month 14 conversion rate will be >= 0.0463. | True | 0.0900->0.0900 |
| 14 | `eb071ef0-9f97-4ae4-aff6-b82853a6efc4` | Finance Controller | Month 14 gross revenue will be >= 23383.17. | True | 0.0900->0.0900 |
| 14 | `d3ca0997-c719-444a-a3a5-161a4dbad1d7` | Operations Manager | Month 14 stockout risk will be <= 0.1600. | True | 0.0916->0.0876 |
| 14 | `f8b1cb79-f8aa-4168-9c4b-d2c6400f7c7c` | Founder CEO | Month 14 strategy will improve business health score. | False | 0.0138->0.0129 |
| 15 | `3244e28a-d8cf-419f-b053-95fbb05ab787` | Growth Marketer | Month 15 CAC will be <= 39.20. | True | 0.0193->0.0240 |
| 15 | `ccab3cd9-bced-425e-b9e9-6e0fca647944` | Product Manager | Month 15 conversion rate will be >= 0.0451. | True | 0.0900->0.0900 |
| 15 | `48f25305-14f1-4a71-8096-a4ae69c3893d` | Finance Controller | Month 15 gross revenue will be >= 24173.97. | True | 0.0900->0.0900 |
| 15 | `ef9e815e-1f0b-4e64-b49e-98dcc20f7231` | Operations Manager | Month 15 stockout risk will be <= 0.1600. | True | 0.0876->0.0840 |
| 15 | `492a9f5d-7a88-43aa-b4bb-838e37313e68` | Founder CEO | Month 15 strategy will improve business health score. | False | 0.0129->0.0120 |
| 16 | `3691eac5-5929-419c-a6b2-334571c1d233` | Growth Marketer | Month 16 CAC will be <= 43.28. | True | 0.0240->0.0410 |
| 16 | `b8ac76be-3aac-4a9c-92b0-1cf74aa96d0a` | Product Manager | Month 16 conversion rate will be >= 0.0483. | True | 0.0900->0.0900 |
| 16 | `f1d2c429-8f12-4f18-bb77-6365eb04b891` | Finance Controller | Month 16 gross revenue will be >= 25005.67. | True | 0.0900->0.0900 |
| 16 | `43bb732a-a990-47f9-a4fe-9cbd2db61cfe` | Operations Manager | Month 16 stockout risk will be <= 0.1600. | True | 0.0840->0.0844 |
| 16 | `c686dec4-a87f-4938-ae5b-1bd746ac1d50` | Founder CEO | Month 16 strategy will improve business health score. | False | 0.0120->0.0112 |
| 17 | `f558402b-20fa-4642-8170-fe02d41a1a3c` | Growth Marketer | Month 17 CAC will be <= 43.66. | True | 0.0410->0.0592 |
| 17 | `fa54499e-8d92-417d-ab9c-1118e021e68b` | Product Manager | Month 17 conversion rate will be >= 0.0447. | True | 0.0900->0.0900 |
| 17 | `836614ab-975d-4c16-8493-d544a465c50d` | Finance Controller | Month 17 gross revenue will be >= 25864.65. | True | 0.0900->0.0900 |
| 17 | `912092ff-23f2-48a4-b0c4-aa01173dc64e` | Operations Manager | Month 17 stockout risk will be <= 0.1600. | True | 0.0844->0.0847 |
| 17 | `881e414d-87be-4b9b-9867-29aebed7188f` | Founder CEO | Month 17 strategy will improve business health score. | False | 0.0112->0.0106 |
| 18 | `f472e6f1-479b-48bc-af87-192aeb5b04d2` | Growth Marketer | Month 18 CAC will be <= 39.65. | True | 0.0592->0.1152 |
| 18 | `02d01537-14f4-4329-a3a2-708374e53a47` | Product Manager | Month 18 conversion rate will be >= 0.0502. | True | 0.0900->0.0900 |
| 18 | `061fb54c-1639-41b3-9f07-7f9d80badd97` | Finance Controller | Month 18 gross revenue will be >= 26866.78. | True | 0.0900->0.0900 |
| 18 | `4cb314f4-8c7c-47cb-913f-82f45fe5cfdc` | Operations Manager | Month 18 stockout risk will be <= 0.1600. | True | 0.0847->0.0850 |
| 18 | `0ec7ccc8-14b2-4e96-b6ce-d05ff7426759` | Founder CEO | Month 18 strategy will improve business health score. | False | 0.0106->0.0100 |
| 19 | `c9e6f35e-3121-4061-8d57-5b829c0c8a32` | Growth Marketer | Month 19 CAC will be <= 45.33. | True | 0.1152->0.1945 |
| 19 | `caec37d5-c68f-4d68-b0ca-636b6c6ea7e5` | Product Manager | Month 19 conversion rate will be >= 0.0515. | True | 0.0900->0.0900 |
| 19 | `78ed2bfa-c7cf-43a3-9be9-e40bc8dd0478` | Finance Controller | Month 19 gross revenue will be >= 27855.28. | True | 0.0900->0.0900 |
| 19 | `274081f1-370c-4f4c-9662-09a12f6b4cca` | Operations Manager | Month 19 stockout risk will be <= 0.1600. | True | 0.0850->0.0853 |
| 19 | `cf00c707-43db-4e7e-aa20-32466edc3be1` | Founder CEO | Month 19 strategy will improve business health score. | False | 0.0100->0.0095 |
| 20 | `48b34da0-9dbc-4d5a-b196-49b11304f82b` | Growth Marketer | Month 20 CAC will be <= 44.65. | True | 0.1945->0.2869 |
| 20 | `81d77621-2cb3-4e4a-962b-ee7af13cdb88` | Product Manager | Month 20 conversion rate will be >= 0.0522. | True | 0.0900->0.0900 |
| 20 | `6d530dd3-711f-493d-a0d1-9cd34b375373` | Finance Controller | Month 20 gross revenue will be >= 28516.56. | True | 0.0900->0.0900 |
| 20 | `34dc9892-b0e0-4111-8adc-ce018fb98378` | Operations Manager | Month 20 stockout risk will be <= 0.1600. | True | 0.0853->0.0855 |
| 20 | `c28a23ca-4e37-40cc-9506-f7a1e738ab31` | Founder CEO | Month 20 strategy will improve business health score. | False | 0.0095->0.0090 |
| 21 | `20629ec0-5299-4d31-890a-566514ca1876` | Growth Marketer | Month 21 CAC will be <= 39.17. | False | 0.2869->0.2165 |
| 21 | `3a57ca23-10c9-4cb5-83aa-3923e8179167` | Product Manager | Month 21 conversion rate will be >= 0.0500. | True | 0.0900->0.0900 |
| 21 | `4cb489a0-97f0-4844-ba69-fb411e4e7c42` | Finance Controller | Month 21 gross revenue will be >= 30016.35. | True | 0.0900->0.0900 |
| 21 | `1b61dc47-2c59-4d12-ac2a-65a0aa5626f2` | Operations Manager | Month 21 stockout risk will be <= 0.1600. | True | 0.0855->0.0857 |
| 21 | `d695038e-8e33-4608-bf56-ebda0a4443ac` | Founder CEO | Month 21 strategy will improve business health score. | False | 0.0090->0.0086 |
| 22 | `d55b3357-8aca-4c00-923c-db13279c2904` | Growth Marketer | Month 22 CAC will be <= 46.96. | True | 0.2165->0.3033 |
| 22 | `13375c3e-2d9e-42d6-a588-1e389de096c1` | Product Manager | Month 22 conversion rate will be >= 0.0526. | True | 0.0900->0.0900 |
| 22 | `7fe26300-8477-4536-b11a-9eb2e7c3ea00` | Finance Controller | Month 22 gross revenue will be >= 31700.21. | True | 0.0900->0.0900 |
| 22 | `898a2442-6bd2-40f9-a2ae-8f5a477c70da` | Operations Manager | Month 22 stockout risk will be <= 0.1600. | True | 0.0857->0.0859 |
| 22 | `b77b9f0a-f994-4ce3-b78c-7fcd371052b6` | Founder CEO | Month 22 strategy will improve business health score. | False | 0.0086->0.0082 |
| 23 | `73c1d7a6-7054-4144-ab99-a0f8e6c9b52d` | Growth Marketer | Month 23 CAC will be <= 43.00. | True | 0.3033->0.3985 |
| 23 | `762dc6b5-fb16-47d1-ae2c-92f981f2cb2e` | Product Manager | Month 23 conversion rate will be >= 0.0525. | True | 0.0900->0.0900 |
| 23 | `e85279e5-b3a3-48e0-a919-42dce4547230` | Finance Controller | Month 23 gross revenue will be >= 33506.78. | True | 0.0900->0.0900 |
| 23 | `a2abe63a-2498-4dc9-9cb9-3d977786c956` | Operations Manager | Month 23 stockout risk will be <= 0.1600. | True | 0.0859->0.0861 |
| 23 | `6e4d3d07-ca89-4d8e-afcc-a3eb407ae551` | Founder CEO | Month 23 strategy will improve business health score. | False | 0.0082->0.0078 |
| 24 | `fa36dde9-02f7-4540-814f-cf148f99d1d6` | Growth Marketer | Month 24 CAC will be <= 46.91. | True | 0.3985->0.5000 |
| 24 | `c29f48c3-6f64-4b04-b106-03cb457db4cd` | Product Manager | Month 24 conversion rate will be >= 0.0527. | True | 0.0900->0.0900 |
| 24 | `72c136ec-e73d-4cba-aa06-7ec9e47f4062` | Finance Controller | Month 24 gross revenue will be >= 35286.09. | True | 0.0900->0.0900 |
| 24 | `257142fc-78c5-458a-8923-7a35579bcfac` | Operations Manager | Month 24 stockout risk will be <= 0.1600. | True | 0.0861->0.0862 |
| 24 | `6950aac7-09a2-4fd7-9d28-a54a3113347f` | Founder CEO | Month 24 strategy will improve business health score. | False | 0.0078->0.0075 |
| 25 | `7de30836-f7ff-4370-b65e-c72047b8063f` | Growth Marketer | Month 25 CAC will be <= 41.40. | True | 0.5000->0.5200 |
| 25 | `139b68b5-a6e4-4830-974a-fbe99920c26b` | Product Manager | Month 25 conversion rate will be >= 0.0516. | True | 0.0900->0.0900 |
| 25 | `9e71cb68-7ee7-4451-aa46-4e2639ffff0d` | Finance Controller | Month 25 gross revenue will be >= 38933.31. | True | 0.0900->0.0900 |
| 25 | `42fd2fd6-41b1-4e3d-ac5c-699ff52c83a5` | Operations Manager | Month 25 stockout risk will be <= 0.1600. | True | 0.0862->0.0864 |
| 25 | `e2aed4bd-de0d-40d2-b64e-9c0692669649` | Founder CEO | Month 25 strategy will improve business health score. | False | 0.0075->0.0072 |
| 26 | `769d8087-7f89-4a63-af11-908e9f410f7b` | Growth Marketer | Month 26 CAC will be <= 44.12. | True | 0.5200->0.5385 |
| 26 | `0d427009-d4f2-4c30-8dcf-f6e790f438a9` | Product Manager | Month 26 conversion rate will be >= 0.0498. | True | 0.0900->0.0900 |
| 26 | `7e7511ef-6f3d-49c2-9529-1c755bc12748` | Finance Controller | Month 26 gross revenue will be >= 41796.56. | True | 0.0900->0.0900 |
| 26 | `64eb3a0a-b08c-466a-ba44-f42b7b44a250` | Operations Manager | Month 26 stockout risk will be <= 0.1600. | True | 0.0864->0.0865 |
| 26 | `25c5ec52-58ea-43a3-9953-b2b7c0386dad` | Founder CEO | Month 26 strategy will improve business health score. | False | 0.0072->0.0069 |
| 27 | `773989e1-fd37-47f2-afd2-300cc85e8882` | Growth Marketer | Month 27 CAC will be <= 46.74. | True | 0.5385->0.5556 |
| 27 | `9fec98ac-011e-4647-86e9-609dedd4e90d` | Product Manager | Month 27 conversion rate will be >= 0.0523. | True | 0.0900->0.0900 |
| 27 | `e9db315c-dc0e-4417-9e33-56bef89a4db2` | Finance Controller | Month 27 gross revenue will be >= 47079.93. | True | 0.0900->0.0900 |
| 27 | `84ca417a-6da3-4c90-ab0e-e89795951f4f` | Operations Manager | Month 27 stockout risk will be <= 0.1600. | True | 0.0865->0.0867 |
| 27 | `294b01a9-68a9-4a35-b7b1-f4457d19e5be` | Founder CEO | Month 27 strategy will improve business health score. | False | 0.0069->0.0067 |
| 28 | `8f1b4f27-b533-4e47-bf60-79534601a6a8` | Growth Marketer | Month 28 CAC will be <= 46.50. | True | 0.5556->0.5714 |
| 28 | `0e8521dd-ae83-43b5-8cca-de798ce5ea93` | Product Manager | Month 28 conversion rate will be >= 0.0477. | True | 0.0900->0.0900 |
| 28 | `c07b37b3-3d28-4135-afbe-59d0e89fb441` | Finance Controller | Month 28 gross revenue will be >= 50570.36. | True | 0.0900->0.0900 |
| 28 | `d6da4e46-7467-41f6-8665-0c4f26d7851f` | Operations Manager | Month 28 stockout risk will be <= 0.1600. | True | 0.0867->0.0868 |
| 28 | `c1f2278b-3d84-4c88-afb8-61554ee5cbfc` | Founder CEO | Month 28 strategy will improve business health score. | False | 0.0067->0.0064 |
| 29 | `e4b0524b-7ee2-4e88-a8af-ff377ac41841` | Growth Marketer | Month 29 CAC will be <= 44.24. | True | 0.5714->0.5862 |
| 29 | `b7c19213-c364-4300-9a31-e121cf8e6474` | Product Manager | Month 29 conversion rate will be >= 0.0522. | True | 0.0900->0.0900 |
| 29 | `bac85c07-c48e-40b1-8e3c-cc6030fc8731` | Finance Controller | Month 29 gross revenue will be >= 55137.92. | True | 0.0900->0.0900 |
| 29 | `929d5157-412f-4ed2-9001-4769a0242800` | Operations Manager | Month 29 stockout risk will be <= 0.1600. | True | 0.0868->0.0869 |
| 29 | `438f943a-2fee-4b15-ad50-2f9f9605a16a` | Founder CEO | Month 29 strategy will improve business health score. | False | 0.0064->0.0062 |
| 30 | `bec9fe38-617c-408e-be71-6a7494f842ce` | Growth Marketer | Month 30 CAC will be <= 44.86. | True | 0.5862->0.6000 |
| 30 | `386e4761-3b2a-4b27-a4cf-faecdf7f3a28` | Product Manager | Month 30 conversion rate will be >= 0.0491. | True | 0.0900->0.0900 |
| 30 | `41dac129-a634-4a8f-8529-25474d3815f9` | Finance Controller | Month 30 gross revenue will be >= 59596.40. | True | 0.0900->0.0900 |
| 30 | `f94579e1-2084-4310-854d-1329907da4d1` | Operations Manager | Month 30 stockout risk will be <= 0.1600. | True | 0.0869->0.0870 |
| 30 | `90e59f98-87db-4f30-b042-43ee124af363` | Founder CEO | Month 30 strategy will improve business health score. | False | 0.0062->0.0060 |
| 31 | `3f1c1cd5-1065-4eff-9697-b4e1e0b1a5f0` | Growth Marketer | Month 31 CAC will be <= 49.25. | True | 0.6000->0.6129 |
| 31 | `0a35fc8d-79f7-43d0-97c2-760ef7039e15` | Product Manager | Month 31 conversion rate will be >= 0.0455. | True | 0.0900->0.0900 |
| 31 | `455b4597-e78f-4806-8332-cf81edad504f` | Finance Controller | Month 31 gross revenue will be >= 63386.79. | True | 0.0900->0.0900 |
| 31 | `3684abf2-d439-4289-ac96-96293e6930c5` | Operations Manager | Month 31 stockout risk will be <= 0.1600. | True | 0.0870->0.0871 |
| 31 | `b2f016ad-4010-42f7-b933-9e715a3f15f3` | Founder CEO | Month 31 strategy will improve business health score. | False | 0.0060->0.0058 |
| 32 | `fa292049-9b36-4899-a9dd-d7f2f4a4d156` | Growth Marketer | Month 32 CAC will be <= 48.15. | True | 0.6129->0.6250 |
| 32 | `9f871fab-f9e2-42d0-9a5e-5f93e53a1b84` | Product Manager | Month 32 conversion rate will be >= 0.0498. | True | 0.0900->0.0900 |
| 32 | `e2e088b1-d131-4208-9f8e-ea149b04330f` | Finance Controller | Month 32 gross revenue will be >= 67477.14. | True | 0.0900->0.0900 |
| 32 | `71c0abdf-9640-4ba4-a793-52851729abeb` | Operations Manager | Month 32 stockout risk will be <= 0.1600. | True | 0.0871->0.0872 |
| 32 | `80b463a4-f3b4-4c3b-a5c3-59d044ff41e7` | Founder CEO | Month 32 strategy will improve business health score. | False | 0.0058->0.0056 |
| 33 | `8647bca4-01c3-4225-a8ef-5838bcb573f4` | Growth Marketer | Month 33 CAC will be <= 44.88. | True | 0.6250->0.6364 |
| 33 | `8871109c-269f-492a-b7ed-1e02d1e06638` | Product Manager | Month 33 conversion rate will be >= 0.0513. | True | 0.0900->0.0900 |
| 33 | `c0241dc2-c8a7-48f0-8c17-ad42a944c52b` | Finance Controller | Month 33 gross revenue will be >= 71601.58. | True | 0.0900->0.0900 |
| 33 | `49f724e2-f797-4330-a77d-2e561dfa51d4` | Operations Manager | Month 33 stockout risk will be <= 0.1600. | True | 0.0872->0.0873 |
| 33 | `7702a3bb-dce7-4dfd-9394-80e989d0300b` | Founder CEO | Month 33 strategy will improve business health score. | False | 0.0056->0.0055 |
| 34 | `c0d4ff71-f54d-4bff-bda7-53bf385824dc` | Growth Marketer | Month 34 CAC will be <= 47.19. | True | 0.6364->0.6471 |
| 34 | `7138dd2e-e3b3-47d8-b0cf-994f47f334a7` | Product Manager | Month 34 conversion rate will be >= 0.0472. | True | 0.0900->0.0900 |
| 34 | `42b399db-abe4-47c2-a5e2-c1fbf65e0661` | Finance Controller | Month 34 gross revenue will be >= 74458.00. | True | 0.0900->0.0900 |
| 34 | `9f32a444-03d9-457e-851d-39cfc55013e0` | Operations Manager | Month 34 stockout risk will be <= 0.1600. | True | 0.0873->0.0874 |
| 34 | `7bed6843-4d0f-488c-8e16-cfc32be2dd06` | Founder CEO | Month 34 strategy will improve business health score. | False | 0.0055->0.0053 |
| 35 | `f3b55a8c-e898-47b6-b1cb-5575059e1988` | Growth Marketer | Month 35 CAC will be <= 44.04. | True | 0.6471->0.6571 |
| 35 | `9407e711-ebb0-4ebe-ae09-f8b60db51200` | Product Manager | Month 35 conversion rate will be >= 0.0520. | False | 0.0900->0.0874 |
| 35 | `1c060446-02d7-4437-9f5a-15fb158e670d` | Finance Controller | Month 35 gross revenue will be >= 77539.40. | True | 0.0900->0.0900 |
| 35 | `64db76a5-85eb-463c-8bad-681c87e3ca91` | Operations Manager | Month 35 stockout risk will be <= 0.1600. | True | 0.0874->0.0874 |
| 35 | `e4a387f0-211d-4bc7-97b1-308f3f242bc1` | Founder CEO | Month 35 strategy will improve business health score. | False | 0.0053->0.0051 |
| 36 | `54b444b4-6e5d-4dca-94ad-385e3899ad76` | Growth Marketer | Month 36 CAC will be <= 50.82. | True | 0.6571->0.6667 |
| 36 | `1844e384-a223-4a77-8137-6dec67f0019e` | Product Manager | Month 36 conversion rate will be >= 0.0526. | True | 0.0874->0.0875 |
| 36 | `f592ff9d-38b0-4b64-b4f4-b62adf9b1646` | Finance Controller | Month 36 gross revenue will be >= 79915.45. | True | 0.0900->0.0900 |
| 36 | `0669f61e-bddf-4a06-aa45-2f8579c755e3` | Operations Manager | Month 36 stockout risk will be <= 0.1600. | True | 0.0874->0.0875 |
| 36 | `47179011-98f1-48e9-9f53-b6a126023069` | Founder CEO | Month 36 strategy will improve business health score. | False | 0.0051->0.0050 |

## Actual Market Outcomes
Actuals came only from `market_oracle_monthly_actual` rows in `pawdent_monthly_financials.csv`.

## Circular Verification Rejection
circular verification rejected in month 1: circular resolution rejected: claim source and resolution source are the same URL (https:market_oracle_pre_decision_signal:seed=9999:month=1)

## Product Roadmap Evolution
| Month | Phase | Roadmap | Quality investment | Reminder investment |
|---:|---|---|---:|---:|
| 1 | idea exploration and customer discovery | pilot routine adherence | 4000 | 900 |
| 2 | idea exploration and customer discovery | pilot routine adherence | 4000 | 900 |
| 3 | idea exploration and customer discovery | pilot routine adherence | 4000 | 900 |
| 4 | MVP design and pilot | pilot routine adherence | 4000 | 2500 |
| 5 | MVP design and pilot | pilot routine adherence | 4000 | 2500 |
| 6 | MVP design and pilot | pilot routine adherence | 4000 | 900 |
| 7 | public launch and early growth | retention and vet education | 6500 | 900 |
| 8 | public launch and early growth | retention and vet education | 3000 | 900 |
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
- Total revenue: `2174987.41`
- Total operating profit: `-981568.11`
- Final cash balance: `-731568.11`
- Profitable months: `0`

## Customer Growth Chart
| Month | Active subscribers | New paid subscribers | Churned subscribers | CAC | LTV estimate | ARPU |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 71 | 71 | 0 | 42.25 | 47.31 | 23.08 |
| 2 | 133 | 69 | 7 | 40.51 | 45.32 | 22.48 |
| 3 | 187 | 65 | 11 | 42.32 | 52.94 | 22.78 |
| 4 | 352 | 183 | 18 | 44.33 | 69.14 | 25.49 |
| 5 | 507 | 190 | 35 | 41.92 | 70.65 | 25.08 |
| 6 | 588 | 134 | 53 | 32.07 | 52.06 | 23.86 |
| 7 | 708 | 172 | 52 | 43.52 | 37.26 | 24.03 |
| 8 | 844 | 199 | 63 | 43.62 | 66.77 | 23.84 |
| 9 | 1005 | 229 | 68 | 43.1 | 68.43 | 23.77 |
| 10 | 1129 | 194 | 70 | 57.04 | 84.37 | 23.95 |
| 11 | 1324 | 282 | 87 | 43.47 | 78.21 | 24.11 |
| 12 | 1480 | 266 | 110 | 50.58 | 75.82 | 24.03 |
| 13 | 1544 | 182 | 118 | 32.19 | 70.27 | 24.01 |
| 14 | 1602 | 175 | 117 | 34.1 | 71.06 | 23.89 |
| 15 | 1663 | 187 | 126 | 32.42 | 75.01 | 24.03 |
| 16 | 1726 | 178 | 115 | 34.51 | 81.76 | 23.97 |
| 17 | 1805 | 178 | 99 | 36.15 | 97.89 | 23.94 |
| 18 | 1877 | 187 | 115 | 36.08 | 84.69 | 24.09 |
| 19 | 1940 | 195 | 132 | 39.54 | 84.39 | 24.1 |
| 20 | 2049 | 231 | 122 | 39.28 | 93.72 | 24.08 |
| 21 | 2181 | 256 | 124 | 41.65 | 86.48 | 24.07 |
| 22 | 2308 | 236 | 109 | 40.05 | 110.35 | 24.19 |
| 23 | 2445 | 261 | 124 | 41.93 | 106.61 | 23.98 |
| 24 | 2694 | 339 | 90 | 37.11 | 148.23 | 24.14 |
| 25 | 2914 | 362 | 142 | 39.57 | 106.57 | 24.17 |
| 26 | 3282 | 457 | 89 | 32.1 | 184.55 | 23.92 |
| 27 | 3543 | 415 | 154 | 36.11 | 117.51 | 24.3 |
| 28 | 3873 | 509 | 179 | 30.02 | 69.78 | 23.96 |
| 29 | 4200 | 456 | 129 | 34.11 | 111.06 | 24.24 |
| 30 | 4478 | 477 | 199 | 33.14 | 112.82 | 23.94 |
| 31 | 4783 | 445 | 140 | 36.05 | 178.59 | 24.24 |
| 32 | 5090 | 438 | 131 | 37.14 | 216.03 | 24.05 |
| 33 | 5301 | 440 | 229 | 37.44 | 127.19 | 24.3 |
| 34 | 5535 | 423 | 189 | 39.41 | 159.63 | 24.02 |
| 35 | 5730 | 383 | 188 | 44.0 | 178.88 | 24.31 |
| 36 | 6003 | 421 | 148 | 40.44 | 202.7 | 24.22 |

## Biggest Correct Call
{"agent": "Growth Marketer", "calibration_delta": 0.1015, "claim": "Month 24 CAC will be <= 46.91.", "claim_source": "market_oracle_pre_decision_signal:seed=9999:month=24", "confidence": 0.62, "explanation": "CAC actual 37.11 <= 46.91", "month": 24, "outcome": true, "prediction_id": "fa36dde9-02f7-4540-814f-cf148f99d1d6", "resolution_source": "market_oracle_monthly_actual:seed=9999:month=24", "run_id": "pawdent-d013b9f2-b8f6-4251-9bac-5869f66d447e", "seed": 9999, "simulated_date": "2028-12-01", "trust_after": 0.5, "trust_before": 0.3985}

## Biggest Wrong Call
{"agent": "Growth Marketer", "calibration_delta": -0.3968, "claim": "Month 5 CAC will be <= 35.23.", "claim_source": "market_oracle_pre_decision_signal:seed=9999:month=5", "confidence": 0.62, "explanation": "CAC actual 41.92 > 35.23", "month": 5, "outcome": false, "prediction_id": "b739fc1e-49cc-4fd9-a799-6da82c71ecfd", "resolution_source": "market_oracle_monthly_actual:seed=9999:month=5", "run_id": "pawdent-d013b9f2-b8f6-4251-9bac-5869f66d447e", "seed": 9999, "simulated_date": "2027-05-01", "trust_after": 0.0, "trust_before": 0.3968}

## Agent Trust Leaderboard
| Agent | Last trust | Resolved claims |
|---|---:|---:|
| Growth Marketer | 0.6667 | 36 |
| Finance Controller | 0.0900 | 36 |
| Product Manager | 0.0875 | 36 |
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
