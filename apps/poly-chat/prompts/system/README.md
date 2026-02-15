# System Prompt Personas

PolyChat offers distinct AI personas, each with a unique communication style and approach.

## Available Personas

### 📚 **default** (Default)
Execution-first generalist. Gives clear recommendations and practical next steps.
- **Use when**: You want the best default for most tasks
- **Style**: Direct, pragmatic, outcome-oriented

### 🎭 **socrates**
Teaches through Socratic questioning. Guides you to discover insights yourself.
- **Use when**: You want to develop critical thinking
- **Style**: Question-led, reflective, diagnostic
- **Example**: Responds to questions with clarifying questions that expose assumptions

### ⚡ **spark**
High-novelty ideation engine. Explores bold options and unconventional connections.
- **Use when**: You need creative ideation or fresh perspectives
- **Style**: Divergent, imaginative, possibility-driven
- **Example**: Generates multiple creative alternatives with vivid language

### 🔪 **razor**
Ultra-concise and direct. Cuts through noise, no fluff.
- **Use when**: You need quick, precise answers without elaboration
- **Style**: Minimal, compressed, high-signal
- **Example**: One-sentence answers, bullet points, numbered lists

### 😈 **devil**
Constructive red team. Stress-tests ideas and exposes failure modes.
- **Use when**: You need critical review or want to find flaws
- **Style**: Skeptical, adversarial, risk-first
- **Example**: Points out downsides, worst-case scenarios, and blind spots

### ♟️ **strategist**
Systems thinker focused on long-term planning and frameworks.
- **Use when**: You need structured planning or strategic analysis
- **Style**: Systems-level, phased, framework-driven
- **Example**: Breaks goals into milestones, considers dependencies and time horizons

### 🎓 **scholar**
Evidence-driven and rigorous. Prioritizes depth, precision, and uncertainty clarity.
- **Use when**: You need depth, accuracy, and thorough exploration
- **Style**: Analytical, qualified, evidence-centered
- **Example**: Multi-angle analysis with context, nuances, and proper qualifications

## How to Use

Set persona in your profile configuration:
```json
{
  "system_prompt": "@/prompts/system/socrates.txt"
}
```

Or switch per-chat using the `/system` command:
```
/system @/prompts/system/spark.txt
```

## Design Philosophy

Each persona is **highly distinct** with:
- **Unique voice**: Different tone, vocabulary, and communication patterns
- **Clear purpose**: Specific use cases where it excels
- **Behavioral consistency**: Maintains character throughout conversations
- **Complementary strengths**: Together they cover diverse interaction needs
