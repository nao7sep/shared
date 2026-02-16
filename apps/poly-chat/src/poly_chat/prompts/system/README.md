# System Prompt Personas

PolyChat offers distinct AI personas, each with a radically different communication style. No names, no introductions—just pure behavioral differences you'll recognize instantly.

## Available Personas

### 📚 **Default**
Action-first generalist. Leads with answers, ends with next steps.
- **Use when**: You want decisive recommendations and practical execution
- **Style**: Direct, executable, no fence-sitting
- **Example**: "Use PostgreSQL. It handles your scale and has the ecosystem. Next: install with `brew install postgresql`"

### 🎭 **Socrates**
Only asks questions. Never gives direct answers. Relentlessly interrogative.
- **Use when**: You want to clarify your own thinking through inquiry
- **Style**: Pure question mode, exposes assumptions, reveals contradictions
- **Example**: "What are you actually trying to achieve? What happens if that assumption is wrong? How would you know if you succeeded?"

### ⚡ **Spark**
Wild creativity engine. Generates 4-6 unexpected options with vivid metaphors.
- **Use when**: You need unconventional ideas and lateral thinking
- **Style**: "What if...?", cross-domain analogies, absurd-but-viable suggestions
- **Example**: "Think of your database like a library vs a warehouse vs a bazaar. What if you treated writes like composting—slow accumulation then sudden transformation?"

### 🔪 **Razor**
Maximum compression. One sentence when possible. Fragments acceptable.
- **Use when**: You need quick, precise answers without elaboration
- **Style**: No preamble, no pleasantries, stops immediately after answering
- **Example**: "PostgreSQL. Use `brew install postgresql`."

### 😈 **Devil**
Everything fails. Starts with what's wrong. Brutally critical, then grudgingly helpful.
- **Use when**: You need aggressive red-teaming and failure mode analysis
- **Style**: Adversarial, risk-obsessed, "This fails when...", never sugarcoats
- **Example**: "This fails when traffic spikes and your connection pool saturates. You're assuming consistent latency but ignoring retry storms. Fix: Add circuit breakers and..."

### ♟️ **Strategist**
Systems thinking with frameworks. Always structures as: Objective → Constraints → Options → Roadmap.
- **Use when**: You need phased planning and strategic analysis
- **Style**: Consultant-speak, time horizons (Now/Next/Later), dependencies explicit
- **Example**: "The critical path here is... Three strategic options: 1) Quick win... 2) Platform play... Roadmap: Now (0-3mo): Setup. Next (3-12mo): Scale..."

### 🎓 **Scholar**
Academic rigor. Structured sections: Context, Evidence, Analysis, Competing Views, Conclusion.
- **Use when**: You need thorough, nuanced exploration with explicit uncertainty
- **Style**: Hedged language ("suggests", "appears to"), multiple perspectives, peer-reviewed tone
- **Example**: "The evidence suggests PostgreSQL, however alternative interpretations include... This assumes workload patterns remain stable, which may not hold if..."

## How to Use

Set persona in your profile configuration:
```json
{
  "system_prompt": "@/prompts/system/socrates.txt"
}
```

Or switch per-chat using the `/system` command with shorthand names:
```
/system razor
/system socrates
/system spark
```

Or use full paths:
```
/system @/prompts/system/devil.txt
```

## Design Philosophy

Each persona is **highly distinct** with:
- **Unique voice**: Different tone, vocabulary, and communication patterns
- **Clear purpose**: Specific use cases where it excels
- **Behavioral consistency**: Maintains character throughout conversations
- **Complementary strengths**: Together they cover diverse interaction needs
