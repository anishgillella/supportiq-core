# Phase 2: VAPI Agent Configuration

## Overview

This guide walks you through setting up the VAPI voice agent that connects to your SupportIQ knowledge base.

## Prerequisites

1. VAPI account at https://vapi.ai
2. VAPI API key
3. Backend server running and accessible (for webhooks)

## Step 1: Create Assistant in VAPI Dashboard

### 1.1 Navigate to Assistants

1. Log into https://dashboard.vapi.ai
2. Click "Assistants" in the left sidebar
3. Click "Create Assistant"

### 1.2 Basic Configuration

```
Name: SupportIQ Customer Support
Description: AI-powered customer support agent with knowledge base integration
```

### 1.3 Model Configuration

| Setting | Value |
|---------|-------|
| Provider | OpenRouter (or your preferred provider) |
| Model | google/gemini-2.5-flash-preview |
| Temperature | 0.7 |
| Max Tokens | 1024 |

### 1.4 System Prompt

Copy this system prompt for your VAPI assistant:

```
You are a friendly and professional customer support AI for SupportIQ. Your job is to help customers with their questions using the company's knowledge base.

GUIDELINES:
1. Be warm, professional, and conversational
2. Listen carefully to the customer's question before responding
3. Provide accurate information based on your knowledge base
4. If you don't know the answer, be honest and offer to escalate
5. Keep responses concise - this is a voice call, not text chat
6. Use natural speech patterns, avoid bullet points in spoken responses
7. Confirm understanding by briefly restating the customer's question
8. End each response with a follow-up: "Is there anything else I can help you with?"

TONE:
- Friendly but professional
- Patient and understanding
- Clear and concise (avoid jargon)
- Empathetic when dealing with frustrated customers

HANDLING EDGE CASES:
- If customer is frustrated: Acknowledge their feelings first
- If question is unclear: Ask clarifying questions
- If you can't help: Offer to take a message or transfer to human support
- If customer wants to speak to human: Respect their request immediately

Remember: You represent the company. Every interaction is an opportunity to build trust.
```

### 1.5 Voice Configuration

| Setting | Recommended Value |
|---------|-------------------|
| Voice Provider | 11Labs or PlayHT |
| Voice | Pick a natural-sounding voice (e.g., "Rachel" for 11Labs) |
| Speed | 1.0 (normal) |
| Stability | 0.7 |

### 1.6 Transcription Settings

| Setting | Value |
|---------|-------|
| Provider | Deepgram |
| Model | nova-2 |
| Language | en |

## Step 2: Configure Server URL (Webhook)

### 2.1 Set Server URL

In VAPI Assistant settings, configure the Server URL:

```
https://your-backend-url.com/api/v1/vapi/webhook
```

For local development with ngrok:
```
https://your-ngrok-id.ngrok.io/api/v1/vapi/webhook
```

### 2.2 Webhook Events

Enable these webhook events:
- [x] `assistant-request` - For RAG context injection
- [x] `end-of-call-report` - To receive transcript after call
- [x] `status-update` - For real-time call status

## Step 3: Configure Function Calling (RAG Integration)

### 3.1 Add Custom Function

In VAPI Assistant > Functions, add:

```json
{
  "name": "search_knowledge_base",
  "description": "Search the company knowledge base to find relevant information to answer the customer's question",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query based on what the customer is asking about"
      }
    },
    "required": ["query"]
  }
}
```

### 3.2 Function URL

Set the function server URL to:
```
https://your-backend-url.com/api/v1/vapi/function
```

## Step 4: Web SDK Integration

### 4.1 Get Web Token

For web-based calling (click-to-call), you need a web token:

1. Go to VAPI Dashboard > Settings > API Keys
2. Create a "Public Key" for web use
3. Copy the public key (starts with `vapi_`)

### 4.2 Frontend Integration

The frontend will use the VAPI Web SDK:

```javascript
import Vapi from "@vapi-ai/web";

const vapi = new Vapi("your-public-key");

// Start a call
vapi.start(assistantId);

// Listen for events
vapi.on("call-start", () => console.log("Call started"));
vapi.on("call-end", () => console.log("Call ended"));
vapi.on("message", (message) => console.log("Message:", message));
```

## Step 5: Test the Agent

### 5.1 Test in VAPI Dashboard

1. Go to your Assistant
2. Click "Test" button
3. Speak a test question
4. Verify the agent responds correctly

### 5.2 Test Questions

Try these test questions:

| Question | Expected Behavior |
|----------|-------------------|
| "Hi, how are you?" | Friendly greeting, asks how to help |
| "What are your business hours?" | Searches knowledge base, provides answer |
| "I need help with billing" | Acknowledges, asks for specifics |
| "I want to talk to a human" | Offers to transfer, doesn't argue |

## Step 6: Environment Variables

Add these to your `.env` file:

```bash
# VAPI Configuration
VAPI_API_KEY=your_private_api_key_here
VAPI_PUBLIC_KEY=your_public_key_for_web
VAPI_ASSISTANT_ID=your_assistant_id_here

# Webhook secret (optional, for signature verification)
VAPI_WEBHOOK_SECRET=your_webhook_secret
```

## VAPI Assistant JSON Export

For reference, here's the complete assistant configuration as JSON:

```json
{
  "name": "SupportIQ Customer Support",
  "model": {
    "provider": "openrouter",
    "model": "google/gemini-2.5-flash-preview",
    "temperature": 0.7,
    "maxTokens": 1024,
    "systemPrompt": "You are a friendly and professional customer support AI for SupportIQ..."
  },
  "voice": {
    "provider": "11labs",
    "voiceId": "rachel"
  },
  "transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en"
  },
  "serverUrl": "https://your-backend-url.com/api/v1/vapi/webhook",
  "functions": [
    {
      "name": "search_knowledge_base",
      "description": "Search the company knowledge base",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "The search query"
          }
        },
        "required": ["query"]
      }
    }
  ]
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent not responding | Check API key and model configuration |
| No transcript received | Verify webhook URL is accessible |
| RAG not working | Check function URL and Pinecone connection |
| Voice sounds robotic | Try different voice provider or settings |
| High latency | Use faster model (gemini-flash) or reduce max tokens |

## Next Steps

After VAPI is configured:
1. Set up backend webhook handlers (Phase 3)
2. Implement transcript analysis (Phase 4)
3. Build the frontend dashboard (Phase 5)
