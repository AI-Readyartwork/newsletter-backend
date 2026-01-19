"""
AI Service using LangChain for newsletter content generation
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import json

from app.config import settings


def get_current_date_context() -> str:
    """Get current date context string for prompts"""
    now = datetime.now()
    return f"CURRENT DATE: {now.strftime('%B %d, %Y')} (Year: {now.year}). All content should be relevant to {now.year}, not past years."


# Output schemas for structured responses
class NewsImpactOutput(BaseModel):
    whyItMatters: str = Field(description="Why this news matters to business owners")
    actionItems: List[str] = Field(description="Action items for business owners")


class HookTitleOutput(BaseModel):
    title: str = Field(description="Catchy hook-style title")


class StoryOutput(BaseModel):
    story: str = Field(description="Full story content in 400-500 words")


class OneLinerOutput(BaseModel):
    text: str = Field(description="One-liner summary")


class AIService:
    def __init__(self):
        # Using gpt-4.1-mini for production - optimal balance of speed, cost, and quality
        self.llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        self.str_parser = StrOutputParser()
        self.json_parser = JsonOutputParser()
    
    async def generate_hook_title(self, original_title: str) -> str:
        """Generate a catchy hook-style title using LangChain"""
        date_context = get_current_date_context()
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are an expert copywriter specializing in hook-style headlines for digital marketing newsletters. 
Transform headlines into magnetic, click-worthy titles using power words, drama, intrigue, numbers, or questions. Keep under 10 words. 
Use current year ({datetime.now().year}) if mentioning dates. 

Return ONLY the new headline, nothing else."""),
            ("user", "Rewrite this headline to be more catchy and attention-grabbing:\n\n{title}")
        ])
        
        chain = prompt | self.llm | self.str_parser
        result = await chain.ainvoke({"title": original_title})
        return result.strip().strip('"')

    async def generate_description(self, title: str) -> str:
        """Generate a compelling description/intro for the newsletter"""
        date_context = get_current_date_context()
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a digital marketing newsletter writer. Create a compelling 1-2 sentence description that hooks the reader.
Write clearly and simply. Use active voice. Avoid corporate buzzwords, —  dashes, and phrases like "delve into" or "furthermore." Every sentence should add value, not filler.
GUIDELINES:
- Be intriguing and create curiosity
- Reference the main topic
- Use active voice
- Keep it under 20 words"""),
            ("user", "Write a compelling description for a newsletter with this main story:\n\n{title}")
        ])
        
        chain = prompt | self.llm | self.str_parser
        result = await chain.ainvoke({"title": title})
        return result.strip()

    async def generate_summary(self, title: str, existing_summary: Optional[str] = None) -> str:
        """Generate a comprehensive summary (150-200 words) from news title and content"""
        date_context = get_current_date_context()
        current_year = datetime.now().year
        
        # Build context from title and any existing content
        news_context = f"Title: {title}"
        if existing_summary and len(existing_summary.strip()) > 10:
            news_context += f"\n\nOriginal Content/Context: {existing_summary}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a senior digital marketing journalist. Write a comprehensive, detailed summary of 150-200 words.
Write clearly and simply. Use active voice. Avoid corporate buzzwords, —  dashes, and phrases like "delve into" or "furthermore." Every sentence should add value, not filler.
REQUIREMENTS:
- Write EXACTLY 100-130 words (this is critical - count your words!)
- Expand on the news with relevant context and analysis
- Explain the business impact for digital marketers
- Include specific insights, data points, or examples where relevant
- Use engaging, professional language
- Format with 2-3 short paragraphs for readability
- Use **bold** for key terms

IMPORTANT: 
- We are in {current_year}. Do NOT reference 2024 or past years as current.
- If the content is brief, expand it with relevant industry context and implications.
- The summary should be substantial and informative, NOT just 2-3 sentences."""),
            ("user", f"Write a detailed 150-200 word summary based on this news:\n\n{news_context}")
        ])
        
        chain = prompt | self.llm | self.str_parser
        result = await chain.ainvoke({})
        return result.strip()

    async def generate_full_story(self, title: str, summary: str = "") -> str:
        """Generate a full 400-500 word story for second/third story sections"""
        date_context = get_current_date_context()
        current_year = datetime.now().year
        
        # Build the content directly in the prompt
        story_context = f"Title: {title}\nContext: {summary or 'No additional context'}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a senior digital marketing journalist writing for a B2B newsletter.
Write clearly and simply. Use active voice. Avoid corporate buzzwords, —  dashes, and phrases like "delve into" or "furthermore." Every sentence should add value, not filler.
Write a compelling 400-500 word article that:
- Opens with a strong hook
- Explains the news and its context
- Discusses the business implications
- Provides actionable insights for marketers
- Ends with a forward-looking statement

IMPORTANT: We are in {current_year}. Do NOT reference 2024 or past years as current.

TONE: Professional but engaging, informative but not dry.
FORMAT: Use short paragraphs (2-3 sentences each) for readability."""),
            ("user", f"Write a 400-500 word article about:\n\n{story_context}")
        ])
        
        chain = prompt | self.llm | self.str_parser
        result = await chain.ainvoke({})
        return result.strip()

    async def generate_main_article(self, title: str, summary: str = "") -> str:
        """Generate the main article (250-350 words) for after Trendsetter section"""
        date_context = get_current_date_context()
        current_year = datetime.now().year
        
        # Build the content directly in the prompt
        article_context = f"Title: {title}\nContext: {summary or 'No additional context'}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a senior digital marketing thought leader writing the main feature article for a prestigious B2B newsletter.
Write clearly and simply. Use active voice. Avoid corporate buzzwords, —  dashes, and phrases like "delve into" or "furthermore." Every sentence should add value, not filler.
Write a polished, newsletter-ready 250-350 word article that flows naturally.

STRUCTURE:
1. OPENING (2-3 sentences): Hook the reader with a compelling statement about the topic's significance
2. ANALYSIS (2 paragraphs): Provide insights and industry context for {current_year}. Use **bold** sparingly for 2-3 key terms only
3. ACTIONABLE TAKEAWAYS: Include a brief section with 2-3 bullet points starting with action verbs
4. CLOSING (1-2 sentences): End with a forward-looking statement

FORMATTING RULES:
- Write in flowing paragraphs, NOT a wall of text
- Use ### only once for the "Actionable Takeaways" section heading
- Use **bold** for max 2-3 key phrases per paragraph (don't over-bold)
- Use bullet points (- ) ONLY for the takeaways section
- Keep paragraphs short: 2-4 sentences each
- NO excessive formatting or markdown headers throughout

STYLE:
- Professional yet conversational tone
- Avoid jargon overload
- Be specific with examples when possible
- Sound authoritative but accessible

IMPORTANT: We are in {current_year}. Reference {current_year} trends, not past years."""),
            ("user", f"Write a polished 250-350 word newsletter feature article about:\n\n{article_context}")
        ])
        
        chain = prompt | self.llm | self.str_parser
        result = await chain.ainvoke({})
        return result.strip()

    async def generate_one_liner(self, title: str) -> str:
        """Generate a one-liner summary for Trendsetter/Top News sections"""
        date_context = get_current_date_context()
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a digital marketing editor. Write a punchy one-liner (max 15 words) that captures the essence of this news.

STYLE: Concise, impactful, informative. No fluff."""),
            ("user", "Write a one-liner for:\n\n{title}")
        ])
        
        chain = prompt | self.llm | self.str_parser
        result = await chain.ainvoke({"title": title})
        return result.strip()

    async def generate_news_impact(
        self,
        title: str,
        description: str,
        source: str,
        category: str
    ) -> Dict[str, any]:
        """Generate business impact analysis for a news article"""
        date_context = get_current_date_context()
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a digital marketing expert. Analyze news impact for business owners.
Write clearly and simply. Use active voice. Avoid corporate buzzwords, —  dashes, and phrases like "delve into" or "furthermore." Every sentence should add value, not filler.
Provide:
1. whyItMatters: 1-2 sentence explanation of business impact
2. actionItems: Array of 1-2 specific actions

Respond in valid JSON with keys whyItMatters and actionItems.
Keep under 80 words total."""),
            ("user", """News Article:
Title: {title}
Description: {description}
Source: {source}
Category: {category}

Analyze the business impact:""")
        ])
        
        chain = prompt | self.llm | self.json_parser
        
        try:
            result = await chain.ainvoke({
                "title": title,
                "description": description,
                "source": source,
                "category": category
            })
            
            return {
                "whyItMatters": result.get("whyItMatters", ""),
                "actionItems": result.get("actionItems", []),
                "tokens_used": 0
            }
        except Exception as e:
            print(f"Error parsing impact JSON: {e}")
            return {
                "whyItMatters": "Unable to generate impact analysis.",
                "actionItems": ["Please try again."],
                "tokens_used": 0
            }

    async def rewrite_title(self, title: str) -> str:
        """Alias for generate_hook_title for backward compatibility"""
        return await self.generate_hook_title(title)
