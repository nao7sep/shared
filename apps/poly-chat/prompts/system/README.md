# System Prompt Personas

PolyChat offers distinct AI personas, each with a unique communication style and approach.

## Available Personas

### 📚 **default** (Default)
Balanced, helpful assistant. Clear and accurate answers with thoughtful explanations.
- **Use when**: You want standard, reliable assistance
- **Style**: Neutral, balanced, accessible

### 🎭 **socrates**
Teaches through Socratic questioning. Guides you to discover insights yourself.
- **Use when**: You want to develop critical thinking
- **Style**: Inquisitive, patient, educational
- **Example**: Responds to questions with clarifying questions that expose assumptions

### ⚡ **spark**
Energetic creative catalyst. Brainstorms wildly and makes unexpected connections.
- **Use when**: You need creative ideation or fresh perspectives
- **Style**: Enthusiastic, imaginative, unconventional
- **Example**: Generates multiple creative alternatives with vivid language

### 🔪 **razor**
Ultra-concise and direct. Cuts through noise, no fluff.
- **Use when**: You need quick, precise answers without elaboration
- **Style**: Minimal, direct, efficient
- **Example**: One-sentence answers, bullet points, numbered lists

### 😈 **devil**
Devil's advocate. Challenges assumptions and stress-tests ideas.
- **Use when**: You need critical review or want to find flaws
- **Style**: Skeptical, challenging, risk-focused
- **Example**: Points out downsides, worst-case scenarios, and blind spots

### ♟️ **strategist**
Systems thinker focused on long-term planning and frameworks.
- **Use when**: You need structured planning or strategic analysis
- **Style**: Systematic, analytical, framework-driven
- **Example**: Breaks goals into milestones, considers dependencies and time horizons

### 🎓 **scholar**
Comprehensive and rigorous. Provides well-researched, authoritative responses.
- **Use when**: You need depth, accuracy, and thorough exploration
- **Style**: Detailed, precise, encyclopedic
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
