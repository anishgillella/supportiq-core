# Phase 6: Deployment & Environment Setup

## Overview

This document covers deployment configuration and environment setup for the voice agent feature.

## Environment Variables

### Backend (`backend/.env`)

```bash
# Existing variables
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
JWT_SECRET_KEY=your_jwt_secret
OPENROUTER_API_KEY=your_openrouter_key
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_HOST=your_pinecone_host

# NEW: VAPI Configuration
VAPI_API_KEY=your_vapi_private_api_key
VAPI_PUBLIC_KEY=your_vapi_public_key
VAPI_ASSISTANT_ID=your_assistant_id
VAPI_WEBHOOK_SECRET=optional_webhook_secret

# NEW: Analysis Model
ANALYSIS_MODEL=google/gemini-2.5-flash-preview
```

### Frontend (`frontend/.env.local`)

```bash
# Existing
NEXT_PUBLIC_API_URL=http://localhost:8000

# NEW: VAPI Configuration
NEXT_PUBLIC_VAPI_PUBLIC_KEY=your_vapi_public_key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your_assistant_id
```

## Database Migration

Run this SQL in Supabase SQL Editor to add the voice tables:

```sql
-- See 01-database-schema.md for full schema
-- Or use the migration file: backend/migrations/001_voice_calls.sql
```

## VAPI Configuration Checklist

1. **Create VAPI Account**
   - Sign up at https://vapi.ai
   - Get API keys from Dashboard > Settings

2. **Create Assistant**
   - Use configuration from `02-vapi-configuration.md`
   - Set Server URL to your backend webhook

3. **Configure Webhook URL**
   - Production: `https://your-api.com/api/v1/vapi/webhook`
   - Local dev: Use ngrok or similar tunnel

4. **Add Knowledge Base Function**
   - Configure `search_knowledge_base` function
   - Point to your backend function endpoint

## Local Development

### Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Start Frontend

```bash
cd frontend
npm run dev
```

### Expose Webhook (for VAPI)

```bash
# Using ngrok
ngrok http 8000

# Copy the URL and update VAPI webhook settings
# e.g., https://abc123.ngrok.io/api/v1/vapi/webhook
```

## Production Deployment

### Backend (Render/Railway/Fly.io)

1. Set all environment variables
2. Deploy FastAPI app
3. Update VAPI webhook URL to production endpoint

### Frontend (Vercel)

1. Connect GitHub repo
2. Set environment variables
3. Deploy

### VAPI Production Settings

1. Update Server URL to production backend
2. Enable production mode
3. Configure phone number (if needed)

## Testing Checklist

- [ ] VAPI assistant responds to test calls
- [ ] Webhook receives end-of-call reports
- [ ] Transcripts are stored in database
- [ ] AI analysis runs successfully
- [ ] Dashboard displays analytics
- [ ] Call detail page shows transcript
- [ ] Voice widget connects from frontend

## Monitoring

### Key Metrics to Track

1. **Call Volume**: Total calls per day/week
2. **Webhook Latency**: Time to process end-of-call
3. **Analysis Success Rate**: % of calls with analytics
4. **Error Rate**: Failed webhooks or analysis

### Logs to Monitor

```bash
# Backend logs
tail -f backend/logs/app.log

# VAPI webhook events
# Check VAPI Dashboard > Logs
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Webhook not receiving events | Check ngrok/tunnel is running, verify VAPI URL |
| Transcript not stored | Check Supabase connection, view backend logs |
| Analysis failing | Verify OpenRouter API key, check model availability |
| Dashboard shows no data | Confirm calls exist in database, check API response |
| Voice widget won't connect | Verify VAPI public key, check browser console |

## Cost Considerations

| Service | Estimated Cost |
|---------|---------------|
| VAPI | ~$0.05-0.15 per minute of call |
| OpenRouter (Gemini 2.5 Flash) | ~$0.0001 per 1K tokens |
| Supabase | Free tier sufficient for MVP |
| Pinecone | Free tier sufficient for MVP |

## Security Notes

1. **Never expose VAPI_API_KEY** - Use only on backend
2. **Validate webhook signatures** - If VAPI provides them
3. **Use HTTPS in production** - Required for VAPI webhooks
4. **Rate limit endpoints** - Prevent abuse of analytics API
