const path = require('path')
const dotenv = require('dotenv')

// Load .env from workspace root folder
dotenv.config({ path: '/Users/anishgillella/conductor/workspaces/supportiq-core/.env' })

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    NEXT_PUBLIC_VAPI_PUBLIC_KEY: process.env.VAPI_PUBLIC_KEY || '',
    NEXT_PUBLIC_VAPI_ASSISTANT_ID: process.env.VAPI_ASSISTANT_ID || '',
  },
}

module.exports = nextConfig
