import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def call_groq(system_prompt: str, user_prompt: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=1000
    )
    return json.loads(response.choices[0].message.content)


async def interpret_segment_intent(intent: str) -> dict:
    system = """You are a CRM segmentation engine for Indian D2C beauty brands.
Convert natural language campaign intent into a segment query JSON.
Available fields: days_inactive (int, days since last order), total_orders (int), total_spend (float INR), channel_preference (string: WhatsApp/Email/SMS).
Operators: gt (greater than), lt (less than), gte (>=), lte (<=), eq (equals).
Respond with valid JSON only. No explanation. No markdown.
Return format: {"rules": [{"field": "...", "op": "...", "value": ...}], "logic": "AND"}"""

    user = f"Campaign intent: {intent}"

    try:
        return call_groq(system, user)
    except Exception as e:
        print(f"Segment AI error: {e}")
        return {
            "rules": [{"field": "days_inactive", "op": "gt", "value": 30}],
            "logic": "AND"
        }


async def generate_confidence_card(
    intent: str,
    audience_size: int,
    channel: str,
    overlap_count: int = 0
) -> dict:
    system = """You are a senior CRM strategist scoring campaign confidence for Indian D2C beauty brands.

You must calculate a confidence score by reasoning through 5 factors:

FACTOR 1 - Audience Clarity (0-25 points)
- Is the segment well defined with specific behaviour? (high score)
- Is it vague like "all customers"? (low score)
- audience_size 5-30: max 18 points (too small = risky)
- audience_size 30-150: max 22 points (good size)
- audience_size 150+: max 25 points (strong reach)

FACTOR 2 - Channel Match (0-25 points)  
- WhatsApp for win-back/personal: 22-25
- WhatsApp for promotions: 18-22
- Email for newsletters/content: 20-24
- Email for urgent offers: 14-18
- SMS for reminders: 16-20
- SMS for rich content: 10-14

FACTOR 3 - Message Relevance (0-20 points)
- Specific product mentioned in intent: 17-20
- General category mentioned: 12-16
- No product context: 6-11

FACTOR 4 - Overlap Risk (0-20 points)
- overlap_count = 0: 20 points
- overlap_count 1-5: 15 points
- overlap_count 6-20: 10 points
- overlap_count 20+: 4 points

FACTOR 5 - Timing Score (0-10 points)
- Win-back after 60-90 days: 9-10 (optimal window)
- Win-back after 30-60 days: 7-8 (slightly early)
- Win-back after 90+ days: 5-6 (may be too late)
- No timing context: 6

Add all 5 factors. That is your confidence_score.
Never return the same score twice — reason freshly each time.

Write messages that are 2-3 sentences, persuasive, product-specific, with discount codes.

Respond with valid JSON only. No explanation. No markdown.
Return exactly:
{
  "segment_description": "specific description of target audience",
  "channel_reasoning": "why this channel fits this specific segment",
  "predicted_open_rate": 0.35,
  "predicted_click_rate": 0.12,
  "predicted_revenue": 25000.0,
  "confidence_score": 74,
  "confidence_factors": [
    {"factor": "Audience clarity", "score": 20, "max_score": 25, "explanation": "specific reason"},
    {"factor": "Channel match", "score": 18, "max_score": 25, "explanation": "specific reason"},
    {"factor": "Message relevance", "score": 16, "max_score": 20, "explanation": "specific reason"},
    {"factor": "Overlap risk", "score": 12, "max_score": 20, "explanation": "specific reason"},
    {"factor": "Timing", "score": 8, "max_score": 10, "explanation": "specific reason"}
  ],
  "message_variant_a": {
    "text": "Hi {name}! 2-3 sentence urgency message with discount code specific to this campaign",
    "tone": "urgency"
  },
  "message_variant_b": {
    "text": "Hi {name}, 2-3 sentence value message with product benefit specific to this campaign", 
    "tone": "value"
  }
}"""

    user = f"""Campaign intent: {intent}
Audience size: {audience_size} customers matched this segment
Channel: {channel}
Customers already in active campaigns: {overlap_count}

Reason through each factor carefully based on this specific intent.
Generate messages that specifically reference: {intent}"""

    try:
        return call_groq(system, user)
        
    except Exception as e:
        print(f"Confidence card AI error: {e}")
        return {
            "segment_description": f"Targeting {audience_size} customers based on purchase behaviour",
            "channel_reasoning": f"{channel} recommended for high engagement with this segment",
            "predicted_open_rate": 0.30,
            "predicted_click_rate": 0.10,
            "predicted_revenue": float(audience_size * 200),
            "confidence_score": 65,
            "confidence_factors": [
                {"factor": "Audience clarity", "score": 18, "max_score": 25, "explanation": "Segment is well defined"},
                {"factor": "Channel match", "score": 17, "max_score": 25, "explanation": "Good channel fit"},
                {"factor": "Message relevance", "score": 14, "max_score": 20, "explanation": "Relevant to segment"},
                {"factor": "Overlap risk", "score": 10, "max_score": 20, "explanation": "Low overlap"},
                {"factor": "Timing", "score": 6, "max_score": 10, "explanation": "Neutral timing"}
            ],
            "message_variant_a": {
                "text": "Hi {name}, we miss you! Come back and discover our latest skincare collection. Use code BACK15 for 15% off.",
                "tone": "urgency"
            },
            "message_variant_b": {
                "text": "Hi {name}, your skin deserves the best. Explore our new arrivals curated just for you.",
                "tone": "value"
            }
        }


async def personalize_message(template: str, customer: dict) -> str:
    first_name = customer.get("name", "Friend").split()[0]
    return template.replace("{name}", first_name)


async def generate_postmortem(
    intent: str,
    predictions: dict,
    actuals: dict
) -> dict:
    system = """You are a senior CRM analyst for Indian D2C beauty brands.
Write a sharp, specific campaign post-mortem using the exact numbers provided.

STRICT RULES:
- root_cause MUST be 2-3 complete sentences. Reference the audience, channel, and exact metrics. NEVER empty.
- next_action MUST start with a verb. Be specific about who to target next and how. NEVER empty.
- headline MUST include actual numbers like open rate percentage or revenue. NEVER empty.
- exceeded: list every metric where actual >= predicted
- missed: list every metric where actual < predicted
- Never return empty strings for any field
- Never say "technical issue" unless told there was one
- Be direct and business-focused — every sentence must reference specific numbers

Respond with valid JSON only. No explanation. No markdown.
Return exactly this structure:
{
  "headline": "one punchy sentence with actual numbers e.g. WhatsApp win-back hit 60% open rate beating prediction by 18pp but revenue missed at zero",
  "exceeded": [
    {"metric": "Open Rate", "predicted": "42%", "actual": "60%", "explanation": "specific reason with numbers"}
  ],
  "missed": [
    {"metric": "Revenue", "predicted": "₹32,000", "actual": "₹0", "explanation": "specific reason with numbers"}
  ],
  "root_cause": "2-3 sentences. Be specific. Reference the audience segment, channel behaviour, and timing. Explain why the gap between prediction and reality occurred.",
  "next_action": "One sentence starting with a verb. Name the specific audience to target next and what offer or message to use."
}"""

    open_diff = actuals["open_rate"] - predictions["open_rate"]
    click_diff = actuals["click_rate"] - predictions["click_rate"]
    rev_diff = actuals["revenue"] - predictions["revenue"]

    pred_open = f"{predictions['open_rate']:.0%}"
    pred_click = f"{predictions['click_rate']:.0%}"
    pred_rev = f"₹{predictions['revenue']:,.0f}"
    act_open = f"{actuals['open_rate']:.0%}"
    act_click = f"{actuals['click_rate']:.0%}"
    act_rev = f"₹{actuals['revenue']:,.0f}"

    user = f"""Campaign intent: {intent}

EXACT NUMBERS TO USE:
- Open rate: predicted {pred_open} → actual {act_open} ({'+' if open_diff >= 0 else ''}{open_diff:.0%} vs prediction)
- Click rate: predicted {pred_click} → actual {act_click} ({'+' if click_diff >= 0 else ''}{click_diff:.0%} vs prediction)
- Revenue: predicted {pred_rev} → actual {act_rev} ({'+' if rev_diff >= 0 else ''}₹{abs(rev_diff):,.0f} {'above' if rev_diff >= 0 else 'below'} prediction)
- Total sent: {actuals['total_sent']} messages
- Conversions: {actuals['converted']} orders

Write the post-mortem using these exact numbers.
root_cause and next_action must never be empty strings."""

    try:
        result = call_groq(system, user)
        
        # Safety fallbacks — never show empty sections
        if not result.get("root_cause"):
            result["root_cause"] = f"The campaign sent {actuals['total_sent']} messages via the selected channel. Open rate of {act_open} was {'above' if open_diff >= 0 else 'below'} the predicted {pred_open}, suggesting the audience-message fit was {'strong' if open_diff >= 0 else 'weaker than expected'}. Revenue of {act_rev} {'exceeded' if rev_diff >= 0 else 'fell short of'} the predicted {pred_rev}, indicating {'strong purchase intent' if rev_diff >= 0 else 'drop-off between engagement and purchase'}."
        
        if not result.get("next_action"):
            if actuals["converted"] > 0:
                result["next_action"] = f"Target the customers who opened but did not convert with a stronger discount offer within the next 48 hours while intent is still warm."
            else:
                result["next_action"] = f"Re-engage the {actuals['total_sent']} customers who received this campaign with a follow-up message featuring a time-limited offer to drive first conversion."
        
        if not result.get("headline"):
            result["headline"] = f"Campaign reached {actuals['total_sent']} customers — {act_open} open rate vs predicted {pred_open}, {actuals['converted']} conversions, {act_rev} revenue."
        
        return result
        
    except Exception as e:
        print(f"Post-mortem AI error: {e}")
        return {
            "headline": f"Campaign reached {actuals['total_sent']} customers with {act_open} open rate vs predicted {pred_open}",
            "exceeded": [{"metric": "Open Rate", "predicted": pred_open, "actual": act_open, "explanation": "Strong audience-message fit drove higher than expected engagement"}] if open_diff > 0 else [],
            "missed": [{"metric": "Revenue", "predicted": pred_rev, "actual": act_rev, "explanation": "Conversion funnel needs optimization — engagement did not translate to purchases"}] if rev_diff < 0 else [],
            "root_cause": f"The campaign achieved {act_open} open rate against a prediction of {pred_open}. Click-through rate of {act_click} suggests the message resonated but the offer or landing experience may have caused drop-off before purchase. Revenue of {act_rev} against predicted {pred_rev} indicates an opportunity to strengthen the conversion path.",
            "next_action": f"Re-target the customers who opened but did not purchase with a stronger limited-time offer and a direct purchase link within 24 hours."
        }