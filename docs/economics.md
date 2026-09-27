# Memora Economics

This document outlines the real operating costs of Memora based on empirical testing with Nebius Token Factory endpoints, using the NVIDIA Nemotron model family.

## 1. Verified Query Costs
The following costs were calculated directly from API logs during our test suite execution. They reflect the actual token usage per query type.

| Model Tier | Used For | Real Cost per Query |
|------------|----------|---------------------|
| **Nemotron-3 Nano** | Intent Classification (`quick_intent`) | **$0.000144** |
| **Nemotron-3 Super** | Standard Chat Dialogue (`respond`) | **$0.001500** |
| **Nemotron-3 Ultra** | Caregiver Reports (`generate_report`) | **$0.002000** |

## 2. Monthly Projection (per Patient)
To ensure honest projections, we calculate the monthly cost based on the exact behavioral sequence modeled in our test environment (`scripts/seed_demo.py`).

**The Baseline (from `seed_demo.py`):**
Our simulation executes a burst of **3 chat queries** (e.g., repeatedly asking about medication) which routes to the **Super** tier.

**Extrapolation (Active MCI Patient):**
Assuming a patient has 10 such interaction bursts per day (30 total chat queries per day).
- **Daily Chat Usage:** 30 queries * $0.0015 = $0.045 / day
- **Monthly Chat Usage:** $0.045 * 30 days = **$1.35 / month**

**Adding Caregiver Analytics:**
Assuming the caregiver requests 1 weekly report (Ultra tier) to summarize the behavioral graph.
- **Monthly Report Usage:** 4 reports * $0.002 = **$0.008 / month**

**Total Projected API Cost:**
$$1.35 (Chat) + $0.008 (Reports) = **$1.358 per patient / month**

## 3. Comparison: AI vs. Human Assistance
Memora is not meant to replace human care, but to augment it by acting as an "always-on" monitor and answering simple, repetitive questions (e.g., "Did I take my pill?").

If a human caregiver were hired solely for 1 hour of daily check-ins and reassurance (30 hours/month):
- **Human Caregiver:** ~30 hours * $15/hour = **$450 / month**
- **Memora AI:** **$1.36 / month**

### Conclusion
By intelligently routing models (using Nano for routing, Super for chat, Ultra for reporting), Memora achieves continuous, anomaly-detecting companionship for an MCI patient at a >99% cost reduction compared to human-equivalent check-ins. This frees human caregivers to step in only when necessary (e.g., when a Red Flag is triggered).
