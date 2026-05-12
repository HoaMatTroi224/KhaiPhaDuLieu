from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from ..config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import (
    ResourceExhausted,
    ServiceUnavailable,
    DeadlineExceeded
)


class SummaryGenerator:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LARGE_LANGUAGE_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2,
            request_timeout=30
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10), 
        retry=retry_if_exception_type(
            (
                ResourceExhausted,
                ServiceUnavailable,
                DeadlineExceeded
            )
        )
    )
    async def generate_summary(self, context: str) -> str:
        prompt = ChatPromptTemplate.from_template("""
            You are an academic editor specialized in scientific abstract writing.

            Write a concise and information-dense Vietnamese academic abstract based only on the provided paper content.

            Requirements:
            - Preserve the original scientific meaning.
            - Do not add external knowledge.
            - Do not hallucinate missing findings.
            - Maintain an objective academic tone.
            - Preserve important technical terminology.
            - Avoid generic filler sentences.
            - Do not mention citation markers.
            - Focus on:
                - research problem
                - objectives
                - methodology
                - experimental setup/data
                - key findings
                - conclusions and implications

            Output constraints:
            - Single coherent paragraph.
            - 180-250 Vietnamese words.
            - No bullet points.
            - High information density.
            - Avoid repetitive phrasing.

            If information is missing, omit it instead of guessing.

            Paper content:
            {context}
        """)

        chain = prompt | self.llm
        response = await chain.ainvoke({"context": context[:15000]})  

        result = response.strip()
        word_count = len(result.split())
        if word_count < 180 or word_count > 250:
            raise ValueError("Exceed the length limit")
        
        return result