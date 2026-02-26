# API Key Configuration Guide

## Overview

AlgoDraft supports **ANY API key** that users provide. The system accepts user-provided credentials for all major cloud AI providers.

## Supported Providers

### 1. **OpenAI** (Recommended)
- **Website**: https://platform.openai.com/account/api-keys
- **Key Format**: `sk-proj-...`
- **Models**: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`

### 2. **Anthropic**
- **Website**: https://console.anthropic.com/
- **Key Format**: `sk-ant-...`
- **Models**: `claude-3-opus`, `claude-3-sonnet-20240229`, `claude-3-haiku`

### 3. **Hugging Face**
- **Website**: https://huggingface.co/settings/tokens
- **Key Format**: `hf_...`
- **Models**: Any HF model ID (e.g., `meta-llama/Llama-2-70b-chat-hf`)

### 4. **Local (Ollama)** - No API Key Needed
- **Website**: https://ollama.com
- **Installation**: Download and install Ollama locally
- **No API key required** - runs completely offline

## How to Set Your API Key

### Option 1: Via Environment Variable (Automatic)

```bash
export ALGODRAFT_API_KEY=your_actual_api_key_here
```

The system will automatically use this environment variable for any cloud provider.

### Option 2: Via Configuration Endpoint

Send a POST request to `/config`:

```bash
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "cloud",
    "cloud_provider": "openai",
    "cloud_model": "gpt-4o",
    "api_key": "sk-proj-your_actual_key_here"
  }'
```

### Option 3: Direct File Edit

Edit `backend/config.json`:

```json
{
  "mode": "cloud",
  "cloud_provider": "openai",
  "cloud_model": "gpt-4o",
  "api_key": "sk-proj-your_actual_key_here"
}
```

## How It Works

1. **User Provides API Key**: Any valid API key from supported providers
2. **System Accepts It**: The backend accepts the key without validation of format
3. **Used on Every Request**: The provided key is used for all API calls to cloud providers
4. **Fallback to Environment Variable**: If no key in config.json, checks `ALGODRAFT_API_KEY` env var

## Security Best Practices

⚠️ **IMPORTANT**: Never commit `backend/config.json` with your actual API key!

- ✅ Store API keys in environment variables
- ✅ Use `.env` file (which is git-ignored)
- ✅ Keep `config.json` clean in version control
- ✅ Rotate API keys regularly
- ✅ Use separate API keys for development/production

## Example Workflows

### Using OpenAI with API Key

```bash
# Set environment variable
export ALGODRAFT_API_KEY=sk-proj-your_openai_key

# Start the backend
cd backend
uvicorn main:app --reload

# Use the API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is quicksort?"}'
```

### Switching Between Providers

```bash
# Switch to Anthropic
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "cloud",
    "cloud_provider": "anthropic",
    "cloud_model": "claude-3-sonnet-20240229",
    "api_key": "sk-ant-xxxxx"
  }'

# Verify the configuration
curl http://localhost:8000/config
```

### Using Local AI (No Key Needed)

```bash
# Install and run Ollama
ollama serve

# In another terminal, pull a model
ollama pull mistral

# Configure AlgoDraft for local mode
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "local",
    "local_model": "mistral",
    "local_code_model": "deepseek-coder:6.7b",
    "api_key": ""
  }'
```

## Troubleshooting

### "API key not configured" Error
- Ensure you've provided an API key via environment variable or config endpoint
- Check that the key format matches the provider (e.g., `sk-` for OpenAI)

### "Unsupported cloud provider" Error
- Verify provider is one of: `openai`, `anthropic`, `huggingface`
- Check spelling in the config request

### Connection Timeout
- For cloud providers: Check internet connection
- For Ollama: Ensure Ollama is running (`ollama serve`)
- For Ollama: Ensure model is pulled (`ollama pull mistral`)

## Current Configuration

To see your current configuration (without exposing the API key):

```bash
curl http://localhost:8000/config
```

This shows:
- Current mode (local or cloud)
- Selected provider
- Selected model
- Available cloud providers

(API key is not displayed in responses for security)

---

**Remember**: AlgoDraft accepts **ANY** API key you provide and uses it exactly as you configure it.
