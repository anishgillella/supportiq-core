"""Website scraping service using Parallel AI Task API"""
import httpx
from typing import List, Dict, Any
from app.core.config import settings


async def scrape_website_with_parallel(website_url: str) -> Dict[str, Any]:
    """
    Use Parallel AI Task API to research and extract information from a company website.
    Uses the lite-fast processor for quick results.
    Returns structured data about the company's products, services, FAQs, etc.
    """
    if not settings.parallel_api_key:
        raise ValueError("Parallel AI API key not configured")

    from parallel import Parallel

    client = Parallel(api_key=settings.parallel_api_key)

    # Create task to extract comprehensive company information
    task_run = client.task_run.create(
        input=f"Research the company at {website_url}",
        task_spec={
            "output_schema": {
                "type": "json",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string", "description": "The name of the company"},
                        "company_description": {"type": "string", "description": "A comprehensive description of what the company does"},
                        "products_and_services": {"type": "string", "description": "Detailed description of products or services offered"},
                        "pricing_info": {"type": "string", "description": "Any pricing information available"},
                        "key_features": {"type": "string", "description": "Main features or benefits of the product/service"},
                        "target_customers": {"type": "string", "description": "Who the product/service is for"},
                        "support_info": {"type": "string", "description": "Customer support information and policies"},
                        "faqs": {"type": "string", "description": "Common questions and answers about the company/product"},
                        "contact_info": {"type": "string", "description": "Contact information like email, phone, address"}
                    }
                }
            }
        },
        processor="lite-fast"
    )

    # Wait for result (with timeout)
    run_result = client.task_run.result(task_run.run_id, api_timeout=120)

    return {
        "success": True,
        "data": run_result.output,
        "run_id": task_run.run_id
    }


async def scrape_website_simple(website_url: str) -> List[Dict[str, str]]:
    """
    Scrape website using Parallel AI if available, fallback to simple HTTP scraping.
    Returns list of page content dictionaries.
    """
    pages = []

    # Try Parallel AI first
    if settings.parallel_api_key:
        try:
            from parallel import Parallel

            client = Parallel(api_key=settings.parallel_api_key)

            # Create task to extract comprehensive company information
            task_run = client.task_run.create(
                input=f"Research the company at {website_url} and provide comprehensive information about their products, services, pricing, features, FAQs, and support policies.",
                task_spec={
                    "output_schema": {
                        "type": "text"  # Get a comprehensive text report
                    }
                },
                processor="lite-fast"
            )

            # Wait for result
            run_result = client.task_run.result(task_run.run_id, api_timeout=120)

            if run_result.output:
                pages.append({
                    "url": website_url,
                    "title": f"Company Research: {website_url}",
                    "content": run_result.output if isinstance(run_result.output, str) else str(run_result.output)
                })
                return pages

        except Exception as e:
            print(f"Parallel AI scraping failed: {e}, falling back to simple scraper")

    # Fallback to simple HTTP scraping
    import re
    from bs4 import BeautifulSoup

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(website_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Get text content
            text = soup.get_text(separator='\n', strip=True)

            # Clean up whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r' +', ' ', text)

            # Get title
            title = soup.title.string if soup.title else website_url

            pages.append({
                "url": website_url,
                "title": title,
                "content": text[:50000]  # Limit content size
            })

        except Exception as e:
            print(f"Error scraping {website_url}: {e}")

    return pages


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending punctuation
            for punct in ['. ', '! ', '? ', '\n\n', '\n']:
                last_punct = text[start:end].rfind(punct)
                if last_punct > chunk_size // 2:
                    end = start + last_punct + len(punct)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks
