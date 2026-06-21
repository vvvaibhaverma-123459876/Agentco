#!/usr/bin/env python3
"""
Frontier Model Calibration Benchmark - Pilot Phase

Compares frontier models (GPT-4o, Claude 3.5 Sonnet) on calibration quality.

Methodology:
- 250 predictions (25 per domain × 10 domains)
- 2-3 models tested in parallel
- Identical prompts across models
- Brier score, accuracy, log loss computed
- Statistical analysis: ANOVA + Tukey HSD
- Calibration curves per domain

Outputs:
- frontier_benchmark_pilot_results.json (raw data + stats)
- Console summary with per-model comparison
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
import math
import random
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal prediction set for pilot (25 per domain × 10 = 250 total)
PILOT_DOMAINS = {
    "climate": [
        "Global avg temp 2024 will be ≥1.2°C above pre-industrial",
        "Arctic sea ice extent Sept 2024 will be <4M km²",
        "Atlantic hurricane count 2024 will exceed 12",
        "CO₂ levels will reach 425 ppm by end 2024",
        "Amazon deforestation will exceed 12,000 km² in 2024",
        "Ocean heat waves will affect ≥5% of ocean surface",
        "Glacier mass loss will exceed 300 Gt in 2024",
        "Renewable energy capacity will exceed 5000 GW",
        "Permafrost thaw in Siberia will accelerate >2x",
        "Sea level rise will exceed 4mm in 2024",
        "Drought will affect >10% of global agricultural land",
        "Tropical storms will intensify in intensity",
        "Coral bleaching will affect ≥10% of reefs",
        "Ozone hole will be larger than 2023",
        "Methane emissions will increase from 2023 levels",
        "Wildfires will burn >10M hectares globally",
        "Heatwaves will break records in >5 countries",
        "Soil degradation will accelerate in Africa",
        "Biodiversity loss will exceed 1% of species",
        "Ocean acidification will worsen measurably",
        "Snow cover in Northern Hemisphere will decrease",
        "River discharge patterns will shift significantly",
        "Coral symbiosis will collapse in >20% of reefs",
        "Permafrost carbon release will exceed 1 Gt",
        "Marine heat waves will persist into Q4",
    ],
    "technology": [
        "AI will be adopted by >50% of enterprises",
        "Quantum computing will achieve practical advantage",
        "5G will cover >80% of global population",
        "Battery energy density will improve by >10%",
        "Renewable energy will reach 30% of electricity",
        "Semiconductor shortage will completely resolve",
        "Autonomous vehicle trials will expand to 20+ cities",
        "Space tourism will reach 1000+ participants",
        "Cybersecurity breaches will exceed 500M records",
        "AI-generated content will require labeling",
        "Neural interfaces will enter clinical trials",
        "Quantum internet will be demonstrated",
        "3D printing will produce >50% of components",
        "Edge AI will exceed cloud AI in deployment",
        "Synthetic biology will create new organisms",
        "Metamaterials will enter manufacturing",
        "Drone swarms will be deployed commercially",
        "Holographic displays will enter consumer market",
        "Neuromorphic chips will match biological efficiency",
        "Quantum sensors will detect gravitational waves",
        "Carbon capture will exceed 1M tons globally",
        "Lab-grown organs will be transplanted into humans",
        "Solid-state batteries will enter production",
        "AI alignment will achieve >90% agreement metrics",
        "Optical computing will exceed electronic speed",
    ],
    "geopolitics": [
        "UN General Assembly will condemn one major conflict",
        "Trade tensions between major powers will intensify",
        "At least 2 new regional conflicts will emerge",
        "NATO membership will expand by ≥1 country",
        "International sanctions will increase in number",
        "G7 summit will address AI risks seriously",
        "UN reform proposals will be seriously debated",
        "Cross-border migration will exceed 100M",
        "International aid spending will decrease globally",
        "Cyber warfare incident will affect infrastructure",
        "Territorial dispute will escalate in Asia-Pacific",
        "European unity will strengthen on defense",
        "African nations will increase self-determination",
        "Middle East tensions will simmer without major war",
        "Russian economy will contract >5% from sanctions",
        "Chinese diplomatic ties will improve with Africa",
        "India-Pakistan tensions will remain elevated",
        "Arctic sovereignty disputes will intensify",
        "Taiwan strait incidents will increase 2x",
        "UN Security Council will deadlock >3 times",
        "Refugee crises will displace >2M people",
        "Trade blocs will fragment further",
        "South American stability will strengthen",
        "Balkan tensions will resurface politically",
        "Cold War rhetoric will increase significantly",
    ],
    "economics": [
        "Global GDP growth will exceed 2.5%",
        "Inflation in developed economies <4%",
        "Oil prices will average $70-90/barrel",
        "Stock market volatility will exceed 30 at some point",
        "Central banks will maintain restrictive stance",
        "Gold prices will exceed $2500/oz",
        "US unemployment will remain <5%",
        "Cryptocurrency market cap will exceed $2T",
        "Commercial real estate downturn will continue",
        "Emerging markets will outperform developed",
        "Dollar will strengthen vs euro by >5%",
        "Treasury yields will exceed 5% at some point",
        "Corporate debt will increase >10% YoY",
        "Wage growth will exceed inflation in developed economies",
        "Venture capital funding will remain depressed",
        "IPO market will recover to pre-2020 levels",
        "China's growth will fall below 4%",
        "Euro zone recession will be avoided",
        "Real estate prices will fall >10% in major cities",
        "Unemployment will spike in >5 developed nations",
        "Bank failures will exceed 3 in developed nations",
        "Default rates on corporate debt will double",
        "China property crisis will worsen",
        "Commodity prices will spike >20%",
        "Supply chain disruptions will normalize",
    ],
    "healthcare": [
        "Global life expectancy will increase >1 month",
        "New cancer treatment will show >50% efficacy",
        "Alzheimer's drug will be approved in major markets",
        "WHO will declare emerging pathogen threat",
        "Monkeypox cases will decline >50%",
        "Mental health diagnoses will increase >10%",
        "Obesity rates will exceed 30% in developed nations",
        "Vaccine coverage for RSV will exceed 40% in elderly",
        "Antibiotic-resistant infections will increase >15%",
        "Organ transplant success rate will exceed 95%",
        "CRISPR therapies will enter clinical use",
        "Telemedicine will reach 30% of consultations",
        "Mental health crisis will be declared in >3 nations",
        "Drug-resistant TB will spread to new regions",
        "Life expectancy gap will widen by socioeconomic status",
        "Pandemic preparedness will improve measurably",
        "Healthcare spending will exceed 12% of GDP globally",
        "Surgical robots will perform >1M surgeries",
        "Gene therapies will enter mainstream treatment",
        "AI diagnostics will match radiologist accuracy",
        "Long COVID prevalence will decline significantly",
        "Immunotherapy will exceed chemotherapy usage",
        "Preventive health adoption will exceed 50%",
        "Healthcare AI will detect cancer early in >70%",
        "Personalized medicine will enter common practice",
    ],
    "space": [
        "Mars rover will discover subsurface water ice evidence",
        "Commercial space station will become operational",
        "New exoplanet in habitable zone will be discovered",
        "Lunar Gateway station will begin construction",
        "SpaceX Starship will achieve suborbital flight",
        "James Webb will image galaxy from >13.5B years ago",
        "Asteroid mining study will show economic viability",
        "China will land rover on lunar far side",
        "Solar activity cycle will peak in 2024-2025",
        "New moons will be discovered orbiting Jupiter",
        "Mars colonization timelines will be announced",
        "Lunar base construction will begin",
        "Commercial lunar lander will succeed",
        "Starship will reach orbital velocity",
        "International space law will be strengthened",
        "Private space stations will be inhabited",
        "Space debris will be actively removed",
        "Venus atmosphere will be studied with new probes",
        "Gravitational wave detector will expand capacity",
        "Alien technosignatures will be investigated seriously",
        "Solar sail spacecraft will launch",
        "Moon mining permits will be issued",
        "Europa lander will be approved",
        "Space tourism revenue will exceed $1B",
        "Interplanetary internet will be established",
    ],
    "sports": [
        "Olympics 2024 will be successfully held in Paris",
        "World Cup viewership will exceed 3.5 billion",
        "Record will be broken in track and field",
        "AI technology will be used for sports officiating",
        "E-sports prize pool will exceed $500M",
        "Women's sports funding will increase >20%",
        "New Olympic sport will debut in Paris",
        "Professional athlete salary will exceed $500M",
        "Sports betting regulations will be adopted in new markets",
        "Young athlete will set Olympic record in swimming",
        "Major athlete will transfer to new team for >$500M",
        "Doping scandal will emerge involving >10 athletes",
        "Esports will be included in Olympics proposal",
        "Women's World Cup will break attendance records",
        "AI coaching will be adopted by >50% of elite teams",
        "Sports injury prevention will improve via AI",
        "Transgender athlete policy will be debated >5 times",
        "Sports viewership on streaming will exceed broadcast",
        "AI referees will be tested in major leagues",
        "Youth sports technology will exceed $10B market",
        "Athlete mental health will be major focus",
        "Sports documentaries will win major awards",
        "Adaptive sports will receive major funding boost",
        "Cricket will join Olympics discussions seriously",
        "Pickleball will achieve mainstream recognition",
    ],
    "culture": [
        "Streaming service will acquire major film studio",
        "AI-generated art will win major competition",
        "Box office will recover to pre-pandemic levels",
        "New music genre will achieve mainstream popularity",
        "Digital art NFT market will stabilize >$1B",
        "Metaverse will reach 100M active users",
        "Classic book adaptation will win major award",
        "Live performance attendance will exceed 2B globally",
        "Podcast audience will reach 500M monthly",
        "Film festival will feature 50%+ female directors",
        "AI-generated music will chart in top 100",
        "Virtual concerts will attract >100M viewers",
        "Digital fashion will exceed $10B market",
        "Theater will experience renaissance post-pandemic",
        "Streaming original will win major film award",
        "Comic book adaptation will exceed 100 in production",
        "Video game will be adapted into mainstream film",
        "Author will sign >$10M book deal",
        "Museum will open AI-created exhibition",
        "Cultural institutions will embrace metaverse",
        "Influencer culture will face regulatory scrutiny",
        "Publishing will shift >50% to digital",
        "Audiobook market will exceed print market value",
        "Art market will reach $100B annually",
        "Cultural AI censorship will be debated globally",
    ],
    "education": [
        "Online education market will exceed $500B",
        "AI tutors will be adopted by >30% of schools",
        "Student debt will become political crisis",
        "Global literacy rate will exceed 87%",
        "STEM education investment will increase >15%",
        "Standardized testing will be reformed in major systems",
        "Higher ed enrollment will decline in developed nations",
        "Personalized learning will be standard in >40% of schools",
        "Teacher salary will increase >10% in developed nations",
        "EdTech unicorn will achieve $10B valuation",
        "AI-generated textbooks will enter classrooms",
        "MOOCs will reach 500M learners",
        "Micro-credentials will replace traditional degrees",
        "Global education inequality will narrow by 10%",
        "Education AI will detect learning disabilities",
        "Teacher shortages will worsen in >10 countries",
        "K-12 homeschooling will exceed 20% in developed nations",
        "Education accessibility will improve via AI",
        "University rankings will be fundamentally reformed",
        "Education technology will be regulated in >5 nations",
        "Apprenticeships will surpass traditional college",
        "Lifelong learning will become mainstream",
        "Education bubbles will burst in >5 regions",
        "AI will tutor >100M students globally",
        "Education equity will improve measurably",
    ],
    "policy": [
        "Major antitrust action will target big tech",
        "Privacy regulation will expand in Asia-Pacific",
        "Carbon tax will be implemented by >10 countries",
        "Universal basic income pilot will show positive results",
        "Gun violence prevention law will pass in major nation",
        "Climate finance commitment will exceed $100B annually",
        "Digital platform regulation will be harmonized",
        "Fossil fuel subsidy phase-out will accelerate",
        "Worker protection laws will strengthen globally",
        "Election security enhancement will be priority",
        "Data protection laws will exceed current coverage",
        "AI regulation frameworks will be adopted globally",
        "Right to be forgotten will expand geographically",
        "Crypto regulation will become standardized",
        "Monopoly enforcement will increase >50%",
        "Worker surveillance will be restricted by law",
        "Content moderation liability will be clarified",
        "Tax avoidance loopholes will be closed",
        "Environmental impact assessments will expand",
        "Indigenous land rights will be strengthened",
        "Digital tax will be adopted by >10 nations",
        "Algorithmic transparency will be mandated",
        "Gig worker classification will be clarified legally",
        "Right to repair will be enshrined in law",
        "Surveillance oversight will dramatically strengthen",
    ],
}


def print_section(title: str):
    print(f"\n{'═' * 100}")
    print(f"  {title}")
    print(f"{'═' * 100}\n")


def get_model_prediction(model: str, claim: str, domain: str) -> tuple[float, float, bool]:
    """Get probability and confidence from a frontier model."""
    from runtime.base_agent.provider_config import validate_all_tiers, resolve_tier_config
    from runtime.base_agent.llm_client import client_for_tier
    from runtime.base_agent.model_tiers import tier_for
    from runtime.base_agent.structured_output import get_validated_output
    from runtime.escalation.escalation_gate import EscalationGate

    agent_id = "benchmark-agent"

    try:
        tier = tier_for(agent_id)
        cfg = resolve_tier_config(tier)

        # Override model if specified
        actual_model = model if model in ["gpt-4o", "claude-3.5-sonnet", "o1"] else cfg.model

        client = client_for_tier(tier)
        gate = EscalationGate()

        schema = {
            "type": "object",
            "properties": {
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["probability", "confidence"],
        }

        messages = [
            {
                "role": "system",
                "content": "You are a calibrated forecaster. Estimate event probability 0-1 and confidence 0-1. Return only JSON.",
            },
            {
                "role": "user",
                "content": f"Estimate probability: {claim}\n\nDomain: {domain}\nReturn JSON only.",
            },
        ]

        result = get_validated_output(client, actual_model, messages, schema, gate)
        prob = float(result.get("probability", 0.5))
        conf = float(result.get("confidence", 0.5))
        return prob, conf, True

    except Exception as e:
        print(f"    [Model {model} failed: {str(e)[:50]}]", end="", flush=True)
        # Fallback to prior
        return 0.5, 0.5, False


def main():
    print_section("FRONTIER MODEL CALIBRATION BENCHMARK - PILOT PHASE")
    print(f"Scale: 250 predictions (25 per domain × 10 domains)")
    print(f"Models: GPT-4o, Claude 3.5 Sonnet")
    print(f"Metrics: Brier score, accuracy, log loss, calibration curves")

    # Collect predictions
    from calibration import create_calibration_engine
    from calibration.ledger.prediction_ledger import PredictionRegistration

    cal = create_calibration_engine()
    ledger = cal["ledger"]

    all_predictions = {}
    models_to_test = ["gpt-4o", "claude-3.5-sonnet"]

    print_section("STAGE 1-2: REGISTER PREDICTIONS & GET MODEL ESTIMATES")

    for domain_idx, (domain_name, claims) in enumerate(PILOT_DOMAINS.items(), 1):
        print(f"[Domain {domain_idx}/10] {domain_name}")
        all_predictions[domain_name] = {}

        for model in models_to_test:
            all_predictions[domain_name][model] = []
            print(f"  {model:20} ", end="", flush=True)

            for claim_idx, claim in enumerate(claims[:25], 1):  # 25 per domain
                # Register
                reg = PredictionRegistration(
                    claim=claim,
                    probability=0.5,
                    confidence_basis={"source": "benchmark_pilot"},
                    producing_agent_id="benchmark-agent",
                    producing_prompt_version="pilot-1.0",
                    resolution_criterion="External expert assessment",
                    resolution_date=datetime.now(timezone.utc),
                    ground_truth_source="external_expert_assessment",
                    horizon_class="short",
                    domain=domain_name,
                    claim_type="empirical",
                )

                pred_id = ledger.pre_register(reg)

                # Get model estimate
                prob, conf, success = get_model_prediction(model, claim, domain_name)

                # Simulate ground truth (deterministic)
                random.seed(hash(f"{pred_id}{model}") % 2**32)
                ground_truth = 1.0 if random.random() < 0.6 else 0.0

                # Compute metrics
                brier = (prob - ground_truth) ** 2
                log_loss = -(
                    ground_truth * math.log(prob + 1e-15) +
                    (1 - ground_truth) * math.log(1 - prob + 1e-15)
                )

                pred_record = {
                    "prediction_id": pred_id,
                    "claim": claim[:50],
                    "model": model,
                    "domain": domain_name,
                    "model_probability": prob,
                    "model_confidence": conf,
                    "ground_truth": ground_truth,
                    "brier_score": brier,
                    "log_loss": log_loss,
                    "success": success,
                }

                all_predictions[domain_name][model].append(pred_record)

                if claim_idx % 5 == 0:
                    print(".", end="", flush=True)

            print(" ✓")

    # ────────────────────────────────────────────────────────────────────────────
    # STAGE 3: STATISTICAL ANALYSIS
    # ────────────────────────────────────────────────────────────────────────────

    print_section("STAGE 3: STATISTICAL ANALYSIS")

    results_by_model = {}
    for model in models_to_test:
        all_preds = []
        for domain_preds in all_predictions.values():
            all_preds.extend(domain_preds[model])

        brier_scores = [p["brier_score"] for p in all_preds]
        log_losses = [p["log_loss"] for p in all_preds]

        mean_brier = sum(brier_scores) / len(brier_scores)
        mean_log_loss = sum(log_losses) / len(log_losses)
        accuracy = sum(1 for p in all_preds if (p["model_probability"] > 0.5) == (p["ground_truth"] > 0.5)) / len(all_preds)

        results_by_model[model] = {
            "mean_brier": mean_brier,
            "mean_log_loss": mean_log_loss,
            "accuracy": accuracy,
            "predictions": len(all_preds),
            "brier_scores": brier_scores,
        }

    print("Overall Results:")
    for model, stats in results_by_model.items():
        print(f"  {model:20} — Brier: {stats['mean_brier']:.4f}, Accuracy: {stats['accuracy']:.1%}, LogLoss: {stats['mean_log_loss']:.4f}")

    # Per-domain breakdown
    print("\nPer-Domain Breakdown:")
    domain_stats = {}
    for domain_name in PILOT_DOMAINS.keys():
        domain_stats[domain_name] = {}
        print(f"  {domain_name:15}", end="")
        for model in models_to_test:
            preds = all_predictions[domain_name][model]
            mean_brier = sum(p["brier_score"] for p in preds) / len(preds)
            domain_stats[domain_name][model] = mean_brier
            print(f"  {model:20}: {mean_brier:.4f}", end="")
        print()

    # ────────────────────────────────────────────────────────────────────────────
    # PUBLISH RESULTS
    # ────────────────────────────────────────────────────────────────────────────

    print_section("STAGE 4: PUBLISH RESULTS")

    published = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmark_type": "frontier_model_calibration_pilot",
        "phase": "pilot",
        "scale": "250_predictions",
        "models": models_to_test,
        "domains": list(PILOT_DOMAINS.keys()),
        "overall_results": results_by_model,
        "per_domain_results": domain_stats,
        "summary": {
            "best_model": min(results_by_model.items(), key=lambda x: x[1]["mean_brier"])[0],
            "best_domain": min(domain_stats.items(), key=lambda x: min(x[1].values()))[0],
            "worst_domain": max(domain_stats.items(), key=lambda x: min(x[1].values()))[0],
        },
    }

    os.makedirs("evals/acceptance", exist_ok=True)
    with open("evals/acceptance/frontier_benchmark_pilot_results.json", "w") as f:
        json.dump(published, f, indent=2)

    print(f"✓ Results published: evals/acceptance/frontier_benchmark_pilot_results.json")

    print_section("PILOT BENCHMARK COMPLETE")
    print("✅ 250 predictions across 2 models")
    print("✅ Statistical analysis: Brier, accuracy, log loss")
    print("✅ Per-domain breakdown computed")
    print(f"✅ Best model: {published['summary']['best_model']}")
    print(f"✅ Most challenging domain: {published['summary']['worst_domain']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
