import logging
from openai import AsyncOpenAI

from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS,
)

logger = logging.getLogger(__name__)

# Initialize the AsyncOpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def ask_llm(question: str, context: str, mode: str = "qa") -> str:
    """
    Sends a prompt and context to the OpenAI LLM. 
    Supports 'qa' for strict document answering and 'cost' for generative estimation.
    """
    logger.info(f"Processing query | Mode: {mode}")

    try:
        # Truncate context to avoid token limit errors
        safe_context = context[:12000] if context else ""
        
        # 🛡️ BUG FIX: Set a default system prompt to prevent UnboundLocalError
        system_prompt = "You are a helpful engineering assistant."

        # ======================================================
        # 🧠 QA MODE (STRICT RAG)
        # ======================================================
        if mode == "qa":
            # If there's no context, don't even waste money calling the API
            if not safe_context or len(safe_context.strip()) < 20:
                return "No relevant information found in the uploaded documents."

            system_prompt = """
You are an RFQ analysis assistant.

STRICT RULES:
- Use ONLY the provided context to answer the user's question.
- If the answer is not in the context, say "The information is not available."
- Do not hallucinate or guess.
"""

        # ======================================================
        # 💰 COST MODE (GENERATION MODE)
        # ======================================================
        elif mode == "cost":
            system_prompt = """
You are a professional estimation engineer.

Generate a complete quotation using the available context.

RULES:
- DO NOT say "information not available"
- Use standard engineering assumptions where data is missing
- Always produce:
  - Project Overview
  - Scope
  - BOQ Pricing
  - Total Cost
  - Assumptions
  - Risks
- Be realistic with pricing. Fill missing gaps intelligently.
"""

        # ======================================================
        # USER PROMPT
        # ======================================================
        user_prompt = f"""
### RFQ DATA CONTEXT:
{safe_context}

### TASK:
{question}

Generate your response based on the instructions and context above.
"""

        # ======================================================
        # LLM CALL
        # ======================================================
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # Use a lower temperature for cost to make it more analytical/deterministic
            temperature=0.3 if mode == "cost" else OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS,
        )

        answer = response.choices[0].message.content

        if not answer or not answer.strip():
            return "❌ Failed to generate response."

        return answer.strip()

    except Exception as e:
        logger.error(f"LLM Error: {str(e)}", exc_info=True)
        return "❌ LLM processing failed. Please check your API keys and connection."