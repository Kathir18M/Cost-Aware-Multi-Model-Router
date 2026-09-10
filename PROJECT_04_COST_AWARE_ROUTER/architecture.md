# Planned Architecture

Project 04 will route each request to the cheapest capable model, starting with Claude Haiku and escalating to Claude Sonnet when complexity, confidence, validation, or API availability requires it.

```text
User Request
     |
     v
Task Classification
     |
     v
Complexity Analysis
     |
     v
Model Selection
     |
     v
Claude Haiku
     |
     v
Confidence / Validation
     |
     v
 +---------------+
 |               |
PASS            FAIL
 |               |
 v               v
Final        Claude Sonnet
Response        |
                v
          Final Response
                |
                v
        Cost Calculation
                |
                v
             Logging
                |
                v
       Streamlit Dashboard
```

LangGraph will orchestrate the workflow. MCP will expose selected tools and resources for routing, cost tracking, confidence, complexity, evaluation, and statistics.

Implementation is planned for later phases. Coming in later phases.
