# 🤖 N8N Telegram to MagicLamp AI Chatbot

**Omnichannel AI Chatbot Workflow for N8N**

This N8N workflow connects Telegram messaging to the MagicLamp AI backend, creating an intelligent chatbot that can answer questions and interact with users automatically.

---

## 📋 Overview

This workflow implements a complete Telegram chatbot integration with the MagicLamp AI reasoning engine. When users send messages to your Telegram bot, the workflow:

1. Receives the message via Telegram webhook
2. Sends the message to MagicLamp AI backend for processing
3. Returns the AI-generated response back to the user on Telegram

---

## 🏗️ Workflow Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│  Telegram User  │──────▶│  N8N Workflow    │──────▶│  MagicLamp API  │
│  Sends Message  │       │  (This JSON)     │       │  /reason/ask    │
└─────────────────┘       └──────────────────┘       └─────────────────┘
                                   │                           │
                                   │        Response           │
                                   │◀──────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Telegram User  │
                          │  Gets Response  │
                          └─────────────────┘
```

---

## 📦 Workflow Nodes

### Node 1: Telegram Trigger
- **Type**: `n8n-nodes-base.telegramTrigger`
- **Purpose**: Listens for incoming Telegram messages
- **Configuration**: Updates on `message` events
- **Required Credential**: Telegram Bot API Token

### Node 2: MagicLamp API Request
- **Type**: `n8n-nodes-base.httpRequest`
- **Purpose**: Sends user message to MagicLamp AI for processing
- **Endpoint**: `POST https://YOUR_REPLIT_URL_HERE/api/v1/brain/reason/ask`
- **Body**: `{ "question": "{{ $json.message.text }}" }`
- **Required Credential**: MagicLamp API Key (via HTTP Header Auth)

### Node 3: Send Telegram Response
- **Type**: `n8n-nodes-base.telegram`
- **Purpose**: Sends AI response back to user
- **Configuration**:
  - Chat ID: Extracted from trigger node
  - Text: AI response from HTTP request
  - Parse Mode: Markdown (for formatting)
- **Required Credential**: Telegram Bot API Token (same as trigger)

---

## 🚀 Installation

### 1. Import Workflow to N8N

1. Open your N8N instance
2. Click **Workflows** → **Import from File**
3. Select `telegram_to_magiclamp_workflow.json`
4. Click **Import**

### 2. Configure Credentials

You need to set up two credentials in N8N:

#### A. Telegram Bot Credentials

1. Create a bot with [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot` to BotFather
   - Follow the prompts to get your bot token
2. In N8N, go to **Credentials** → **Create New**
3. Select **Telegram API**
4. Enter your **Bot Token**
5. Save as "Telegram Bot Account"

#### B. MagicLamp API Key

1. In N8N, go to **Credentials** → **Create New**
2. Select **HTTP Header Auth**
3. Configure:
   - **Name**: `Authorization`
   - **Value**: `Bearer YOUR_MAGICLAMP_JWT_TOKEN`
4. Save as "MagicLamp API Key"

**Note**: You can get a JWT token by logging into MagicLamp:
```bash
curl -X POST https://your-backend.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@example.com", "password": "your_password"}'
```

### 3. Update Backend URL

1. Open the workflow in N8N
2. Click on the **MagicLamp API Request** node
3. Update the URL field: Replace `YOUR_REPLIT_URL_HERE` with your actual backend URL
4. Save the workflow

### 4. Activate Workflow

1. Toggle the **Active** switch in the top-right corner
2. The workflow is now live and listening for Telegram messages

---

## 🔧 Configuration

### Environment Variables (N8N)

Ensure your N8N instance has these environment variables set:

```env
N8N_HOST=your-n8n-domain.com
N8N_PROTOCOL=https
WEBHOOK_URL=https://your-n8n-domain.com
```

### MagicLamp Backend Requirements

Your MagicLamp backend must:
- Be publicly accessible (or accessible from N8N instance)
- Have the `/api/v1/brain/reason/ask` endpoint enabled
- Accept POST requests with JSON body: `{ "question": "text" }`
- Return responses in format: `{ "response": { "text": "answer" } }` or `{ "answer": "text" }`

---

## 📊 Payload Mapping

### Telegram → MagicLamp

When a user sends a message, the workflow extracts:

```javascript
// From Telegram Trigger
{
  "message": {
    "text": "User's question here",
    "chat": {
      "id": 123456789
    }
  }
}

// Mapped to MagicLamp API
{
  "question": "{{ $json.message.text }}"
}
```

### MagicLamp → Telegram

The AI response is mapped back:

```javascript
// From MagicLamp API
{
  "response": {
    "text": "AI generated answer"
  }
}

// Or alternative format
{
  "answer": "AI generated answer"
}

// Sent to Telegram
{
  "chat_id": "{{ $('Telegram Trigger').item.json.message.chat.id }}",
  "text": "AI generated answer",
  "parse_mode": "Markdown"
}
```

---

## 🔐 Security Best Practices

1. **Keep Tokens Secret**: Never expose your Telegram Bot Token or MagicLamp API Key
2. **Use HTTPS**: Always use HTTPS for your N8N instance and MagicLamp backend
3. **Rate Limiting**: Implement rate limiting on your MagicLamp API
4. **Input Validation**: Sanitize user input before processing
5. **Token Rotation**: Regularly rotate your API tokens

---

## 🧪 Testing

### Manual Testing

1. Send a message to your Telegram bot
2. Check N8N workflow execution logs
3. Verify the bot responds correctly

### Test Message Examples

- "Hello, how are you?"
- "What are the eligibility criteria for SME loans?"
- "Tell me about your services"

### Debugging

If the workflow fails:

1. Check **Executions** tab in N8N
2. Click on failed execution to see error details
3. Common issues:
   - Invalid API URL
   - Missing or expired credentials
   - Backend not responding (timeout)
   - Incorrect response format

---

## 📈 Monitoring

### N8N Metrics

Monitor these in N8N dashboard:

- **Execution Success Rate**: Should be >95%
- **Average Execution Time**: Typically 2-5 seconds
- **Error Rate**: Monitor for spikes

### MagicLamp Backend

Check backend logs for:

- API request volume
- Response times
- Error rates
- Token usage

---

## 🛠️ Customization

### Modify AI Behavior

Edit the HTTP Request node to change:

- **Endpoint**: Use `/reason/lead` for lead analysis
- **Body Parameters**: Add context or additional fields
- **Headers**: Add custom headers for tracking

### Enhance Response Formatting

Edit the Telegram Send node:

- Change `parse_mode` to `HTML` for HTML formatting
- Add reply keyboards for interactive responses
- Include inline buttons for actions

### Add Error Handling

1. Add a **Function** node after HTTP Request
2. Check for errors in response
3. Send fallback message if AI fails

---

## 🚢 Deployment Checklist

- [ ] Telegram bot created with BotFather
- [ ] Bot token saved as N8N credential
- [ ] MagicLamp API key/JWT token obtained
- [ ] API key saved as N8N credential (HTTP Header Auth)
- [ ] Backend URL updated in workflow (replace YOUR_REPLIT_URL_HERE)
- [ ] Workflow imported to N8N
- [ ] All nodes configured with correct credentials
- [ ] Test message sent and response received
- [ ] Workflow activated
- [ ] Monitoring set up

---

## 🆘 Troubleshooting

### Bot Not Responding

1. Check workflow is **Active**
2. Verify Telegram credentials are correct
3. Check N8N webhook is reachable
4. Test backend API directly with curl

### API Errors

1. Verify backend URL is correct
2. Check API key is valid and not expired
3. Ensure backend accepts the request format
4. Check CORS settings if applicable

### Timeout Errors

1. Increase timeout in HTTP Request node
2. Optimize MagicLamp AI response time
3. Add retry logic for failed requests

---

## 📚 Additional Resources

- [N8N Documentation](https://docs.n8n.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [MagicLamp API Documentation](../README.md)
- [N8N Workflow Examples](https://n8n.io/workflows/)

---

## 🔄 Updates & Maintenance

### Updating the Workflow

1. Export current workflow as backup
2. Make changes in N8N editor
3. Test with sample messages
4. Save and reactivate

### Token Refresh

If using JWT tokens:
1. Generate new token from MagicLamp
2. Update HTTP Header Auth credential in N8N
3. No workflow restart needed

---

## 📄 Workflow JSON Summary

**File**: `telegram_to_magiclamp_workflow.json`

**Status**: ✅ Ready for import

**Required Credentials**:
1. Telegram Bot Token (for Trigger and Send nodes)
2. MagicLamp API Key (for HTTP Request node)

**Manual Setup Required**:
1. Replace `YOUR_REPLIT_URL_HERE` with your actual backend URL
2. Add Telegram Bot Token credential in N8N
3. Add MagicLamp API Key credential in N8N (format: `Bearer YOUR_JWT_TOKEN`)

---

**Built with ❤️ for SpreadVerse AI Integration**
