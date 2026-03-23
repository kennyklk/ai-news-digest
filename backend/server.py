import os, json, re
import anthropic
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are an AI news curator. Use web search to find today's most relevant AI news articles and return them as a JSON array.

Categories to cover:
1. ai_tools_models — New model releases, feature rollouts (Anthropic, OpenAI, Google, Mistral, etc.)
2. workflow_automation — AI for automating workflows, agents, pipelines, data analysis, BI. PRIORITIZE these.
3. ai_adoption_industry — Enterprise AI adoption, workforce impact, company announcements
4. ai_adoption_travel — Travel/OTA AI news (Skift, PhocusWire, airline/hotel tech)
5. ai_use_cases — How-to guides, build logs, case studies
6. ai_marketing — AI in marketing, ad tech, investment/funding rounds

Search across: TechCrunch, VentureBeat, The Verge, Anthropic/OpenAI/Google blogs, Bloomberg Tech, Skift, PhocusWire, Towards Data Science, Hacker News.

Return ONLY a raw JSON array (no markdown, no backticks, no preamble):
[
  {
    "title": "Article title",
    "source": "Publication name",
    "url": "https://...",
    "summary": "2-3 sentence summary: what happened, what it means, why it matters.",
    "category": "ai_tools_models | workflow_automation | ai_adoption_industry | ai_adoption_travel | ai_use_cases | ai_marketing",
    "highlight": true or false (true only for workflow_automation and data analysis articles),
    "date": "date string"
  }
]

Find 15-20 articles. Include at least 4-5 workflow_automation articles if available."""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/fetch-news")
def fetch_news():
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": f"Find today's AI news articles and return as JSON array. Today is {date.today().strftime('%B %d, %Y')}."
            }]
        )

        # Extract text block from response
        text = ""
        for block in response.content:
            if block.type == "text":
                text = block.text.strip()
                break

        # Strip markdown fences if present
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        # Extract JSON array
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return {"error": "No JSON array found in response", "raw": text[:500]}

        articles = json.loads(text[start:end + 1])
        return {"articles": articles, "count": len(articles)}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
