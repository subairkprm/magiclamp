# 🚀 N8N Telegram Chatbot Deployment Checklist

## Prerequisites Verification
- [ ] N8N instance is running and accessible
- [ ] Telegram bot created via @BotFather
- [ ] MagicLamp backend API is live and accessible
- [ ] You have admin access to your N8N dashboard

---

## Step 1: Upload Workflow to N8N

### 1.1 Access N8N Dashboard
1. Open your browser and navigate to your N8N instance
   - Example: `https://your-n8n-domain.com` or `http://localhost:5678`
2. Log in with your N8N credentials

### 1.2 Import Workflow JSON
1. Click on **"Workflows"** in the left sidebar
2. Click the **"+"** button or **"Add Workflow"**
3. In the new workflow, click the **three dots menu** (⋮) in the top-right corner
4. Select **"Import from File"**
5. Navigate to: `/home/runner/work/magiclamp/magiclamp/n8n-workflows/`
6. Select file: **`telegram_to_magiclamp_workflow.json`**
7. Click **"Open"** or **"Import"**
8. ✅ The workflow should now appear with 3 nodes connected

---

## Step 2: Configure Telegram Bot Token

### 2.1 Get Your Telegram Bot Token
1. Open Telegram and search for **@BotFather**
2. If you don't have a bot yet:
   - Send `/newbot` command to BotFather
   - Choose a name for your bot (e.g., "SpreadVerse AI Assistant")
   - Choose a username (must end in 'bot', e.g., "spreadverse_ai_bot")
   - **Copy the HTTP API Token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
3. If you already have a bot:
   - Send `/mybots` to BotFather
   - Select your bot
   - Click **"API Token"**
   - **Copy the token**

### 2.2 Add Telegram Credential to N8N
1. In N8N, click **"Credentials"** in the left sidebar
2. Click **"Add Credential"** or **"Create New"**
3. Search for and select **"Telegram API"**
4. Fill in the credential:
   - **Name**: `Telegram Bot Account` (or any descriptive name)
   - **Access Token**: Paste your bot token from BotFather
5. Click **"Save"**
6. ✅ Credential created successfully

### 2.3 Assign Telegram Credential to Nodes
1. Go back to your workflow
2. Click on the **"Telegram Trigger"** node
3. In the node settings, under **"Credential for Telegram API"**:
   - Select the credential you just created
4. Click on the **"Send Telegram Response"** node
5. Under **"Credential for Telegram API"**:
   - Select the same credential
6. ✅ Both nodes now have Telegram credentials

---

## Step 3: Configure MagicLamp API Key

### 3.1 Obtain JWT Token from MagicLamp
Run this command to get your JWT token (replace with your credentials):

```bash
curl -X POST https://YOUR_REPLIT_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@example.com",
    "password": "your_secure_password"
  }'
```

**Response will contain:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "refresh_token": "..."
}
```

**📋 Copy the `access_token` value**

### 3.2 Create HTTP Header Auth Credential
1. In N8N, go to **"Credentials"** → **"Add Credential"**
2. Search for and select **"HTTP Header Auth"**
3. Fill in the credential:
   - **Name**: `MagicLamp API Key` (or descriptive name)
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
     - ⚠️ **IMPORTANT**: Include the word "Bearer " before the token
     - Format: `Bearer <your_jwt_token>`
4. Click **"Save"**
5. ✅ API credential created

### 3.3 Assign API Credential to HTTP Request Node
1. In your workflow, click on **"MagicLamp API Request"** node
2. Under **"Authentication"**, ensure it's set to **"Generic Credential Type"**
3. Under **"Generic Auth Type"**, select **"HTTP Header Auth"**
4. Under **"Credential for HTTP Header Auth"**:
   - Select the credential you just created (`MagicLamp API Key`)
5. ✅ API authentication configured

---

## Step 4: Update Backend URL

### 4.1 Edit HTTP Request Node
1. Click on the **"MagicLamp API Request"** node
2. Find the **"URL"** field
3. Replace `YOUR_REPLIT_URL_HERE` with your actual backend URL

   **Examples:**
   - Replit: `https://magiclamp-username.repl.co/api/v1/brain/reason/ask`
   - Custom domain: `https://api.yourdomain.com/api/v1/brain/reason/ask`
   - Local dev: `http://localhost:9000/api/v1/brain/reason/ask`

4. Full URL should be: `https://your-backend.com/api/v1/brain/reason/ask`
5. Click outside the field to save
6. ✅ Backend URL configured

---

## Step 5: Test the Workflow

### 5.1 Execute First Test Node
1. Make sure workflow is **NOT active yet** (toggle should be OFF)
2. Click on the **"Telegram Trigger"** node
3. Click **"Listen for Event"** button at the bottom
4. N8N will start listening for Telegram messages
5. Open Telegram and send a message to your bot:
   - Send: `Hello, are you there?`
6. You should see the message appear in the Telegram Trigger node
7. Click **"Stop Listening"**

### 5.2 Test the Full Workflow
1. With test data captured, click **"Execute Workflow"** button (top-right)
2. Watch the execution flow through all 3 nodes:
   - ✅ Telegram Trigger (should show green with your test message)
   - ✅ MagicLamp API Request (should show green with AI response)
   - ✅ Send Telegram Response (should show green)
3. Check your Telegram bot - you should receive an AI-generated response

### 5.3 Troubleshooting Test Failures

**If Telegram Trigger fails:**
- Verify bot token is correct
- Ensure webhook URL is accessible
- Check N8N webhook settings

**If MagicLamp API Request fails:**
- Verify backend URL is correct and accessible
- Check JWT token is valid (not expired)
- Ensure `Authorization` header format is `Bearer <token>`
- Test backend directly with curl

**If Send Telegram Response fails:**
- Verify chat_id is correctly mapped
- Check Telegram credential is assigned
- Ensure response text field has data

---

## Step 6: Activate the Workflow

### 6.1 Final Checks Before Activation
- [ ] All 3 nodes show green (successful execution)
- [ ] Telegram bot responded in your chat
- [ ] Response text makes sense (from MagicLamp AI)
- [ ] No error messages in execution log

### 6.2 Activate Production Mode
1. Click the **"Inactive"** toggle switch in the top-right corner
2. Switch should turn **green** and show **"Active"**
3. A webhook URL will be registered with Telegram
4. ✅ **Workflow is now LIVE!**

### 6.3 Production Test
1. Send a real question to your Telegram bot:
   - Example: `What are the eligibility criteria for SME loans?`
2. Wait 2-5 seconds for AI processing
3. Bot should respond with MagicLamp AI answer
4. ✅ **Chatbot is operational!**

---

## Step 7: Monitoring & Maintenance

### 7.1 Monitor Executions
1. Go to **"Executions"** tab in N8N
2. View recent workflow runs
3. Check for failures (red indicators)
4. Click on any execution to see detailed logs

### 7.2 Common Maintenance Tasks

**JWT Token Expired (401 errors):**
1. Get new token via `/auth/login` endpoint
2. Update HTTP Header Auth credential
3. No need to restart workflow

**Update Backend URL:**
1. Deactivate workflow
2. Edit HTTP Request node URL
3. Test execution
4. Reactivate workflow

**Change Bot Behavior:**
1. Modify HTTP Request body or response mapping
2. Test with sample data
3. Save and execution will use new logic

---

## ✅ Deployment Complete!

Your Telegram to MagicLamp AI chatbot is now live and ready to serve users!

**Next Steps:**
- Share your bot username with users
- Monitor execution logs for errors
- Consider adding rate limiting on backend
- Set up alerts for failed executions

---

## 📊 Quick Reference

| Component | Value |
|-----------|-------|
| Workflow File | `telegram_to_magiclamp_workflow.json` |
| Telegram Credential | Bot token from @BotFather |
| API Credential | `Authorization: Bearer <jwt_token>` |
| Backend Endpoint | `/api/v1/brain/reason/ask` |
| Expected Response | `{ "response": { "text": "..." } }` |

**Support:** Check the N8N execution logs and MagicLamp backend logs for troubleshooting.
