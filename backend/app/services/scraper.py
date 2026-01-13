"""Website scraping service using Parallel AI Task API"""
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
    Scrape website using Parallel AI.
    Raises an error if Parallel AI is not configured or fails.
    Returns list of page content dictionaries.
    """
    if not settings.parallel_api_key:
        raise ValueError("Parallel AI API key not configured. Please set PARALLEL_API_KEY in your environment.")

    try:
        from parallel import Parallel

        client = Parallel(api_key=settings.parallel_api_key)

        # Create task to extract actual content from the website using thorough processor
        task_run = client.task_run.create(
            input=f"""Navigate to {website_url} and thoroughly extract ALL information from the website.

Visit multiple pages including: homepage, products/services pages, about page, pricing page, FAQ page, support/help page, and any other important pages.

Extract and document EVERYTHING you find including:
- All product names, models, and variants
- Detailed product descriptions and specifications
- All features and capabilities
- Pricing information (if available)
- Company information and history
- Customer support options and policies
- FAQs and common questions
- Contact information
- Any other relevant content

Be comprehensive - extract actual content from the website, not summaries.""",
            task_spec={
                "output_schema": {
                    "type": "json",
                    "json_schema": {
                        "type": "object",
                        "properties": {
                            "company_name": {"type": "string", "description": "The name of the company"},
                            "company_description": {"type": "string", "description": "Detailed description of the company, its mission, and what it does"},
                            "products": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Product name"},
                                        "category": {"type": "string", "description": "Product category"},
                                        "description": {"type": "string", "description": "Detailed product description"},
                                        "features": {"type": "string", "description": "Key features and specifications"},
                                        "price": {"type": "string", "description": "Price or pricing information"},
                                        "variants": {"type": "string", "description": "Different models or variants available"}
                                    }
                                },
                                "description": "Complete list of all products found on the website"
                            },
                            "services": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "features": {"type": "string"}
                                    }
                                },
                                "description": "Services offered by the company"
                            },
                            "pricing_info": {"type": "string", "description": "All pricing information, plans, and subscription details"},
                            "faqs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "question": {"type": "string"},
                                        "answer": {"type": "string"}
                                    }
                                },
                                "description": "Frequently asked questions and answers"
                            },
                            "support_info": {"type": "string", "description": "Customer support options, policies, warranty info, return policies"},
                            "contact_info": {"type": "string", "description": "Contact details - email, phone, address, social media"},
                            "additional_content": {"type": "string", "description": "Any other important information from the website"}
                        }
                    }
                }
            },
            processor="core-fast"  # Use 'core-fast' processor for thorough but faster extraction
        )

        # Wait for result (longer timeout for thorough extraction)
        run_result = client.task_run.result(task_run.run_id, api_timeout=300)

        if not run_result.output:
            raise ValueError(f"Parallel AI returned no content for {website_url}")

        # Convert structured output to text for embedding
        output = run_result.output
        if isinstance(output, dict):
            # Build a comprehensive text from the structured data
            content_parts = []

            if output.get("company_name"):
                content_parts.append(f"Company: {output['company_name']}")

            if output.get("company_description"):
                content_parts.append(f"\nAbout: {output['company_description']}")

            # Products section
            if output.get("products"):
                content_parts.append("\n\n=== PRODUCTS ===")
                for product in output["products"]:
                    if isinstance(product, dict):
                        content_parts.append(f"\nProduct: {product.get('name', 'Unknown Product')}")
                        if product.get('category'):
                            content_parts.append(f"Category: {product['category']}")
                        if product.get('description'):
                            content_parts.append(f"Description: {product['description']}")
                        if product.get('features'):
                            content_parts.append(f"Features: {product['features']}")
                        if product.get('variants'):
                            content_parts.append(f"Variants/Models: {product['variants']}")
                        if product.get('price'):
                            content_parts.append(f"Price: {product['price']}")

            # Services section
            if output.get("services"):
                content_parts.append("\n\n=== SERVICES ===")
                if isinstance(output["services"], list):
                    for service in output["services"]:
                        if isinstance(service, dict):
                            content_parts.append(f"\nService: {service.get('name', 'Unknown Service')}")
                            if service.get('description'):
                                content_parts.append(f"Description: {service['description']}")
                            if service.get('features'):
                                content_parts.append(f"Features: {service['features']}")
                else:
                    content_parts.append(str(output["services"]))

            # Pricing section
            if output.get("pricing_info"):
                content_parts.append(f"\n\n=== PRICING ===\n{output['pricing_info']}")

            # FAQs section
            if output.get("faqs"):
                content_parts.append("\n\n=== FREQUENTLY ASKED QUESTIONS ===")
                if isinstance(output["faqs"], list):
                    for faq in output["faqs"]:
                        if isinstance(faq, dict):
                            content_parts.append(f"\nQ: {faq.get('question', '')}")
                            content_parts.append(f"A: {faq.get('answer', '')}")
                else:
                    content_parts.append(str(output["faqs"]))

            # Support section
            if output.get("support_info"):
                content_parts.append(f"\n\n=== SUPPORT & POLICIES ===\n{output['support_info']}")

            # Contact section
            if output.get("contact_info"):
                content_parts.append(f"\n\n=== CONTACT INFORMATION ===\n{output['contact_info']}")

            # Additional content
            if output.get("additional_content"):
                content_parts.append(f"\n\n=== ADDITIONAL INFORMATION ===\n{output['additional_content']}")

            content = "\n".join(content_parts)
        else:
            content = str(output)

        return [{
            "url": website_url,
            "title": output.get("company_name", website_url) if isinstance(output, dict) else website_url,
            "content": content
        }]

    except ImportError:
        raise ValueError("Parallel AI library not installed. Please install with: pip install parallel-web")
    except Exception as e:
        raise ValueError(f"Parallel AI scraping failed: {str(e)}")


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
