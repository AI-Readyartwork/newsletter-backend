# Active Campaign Newsletter Integration

Push newsletters directly to Active Campaign as email campaigns.

## Prerequisites

1. Active Campaign account with API access
2. At least one subscriber list in Active Campaign

## Setup

### 1. Get Your API Credentials

1. Log into your Active Campaign account
2. Navigate to **Settings → Developer**
3. Copy your:
   - **API URL** (e.g., `https://youraccountname.api-us1.com`)
   - **API Key** (long string of characters)

### 2. Configure Environment Variables

Add these to your `.env` file in the backend directory:

```env
ACTIVECAMPAIGN_URL=https://youraccountname.api-us1.com
ACTIVECAMPAIGN_API_KEY=your-api-key-here
```

### 3. Restart the Backend

```bash
cd backend
python main.py
```

---

## Usage

### Pushing a Newsletter to Active Campaign

1. Create/edit your newsletter in the editor
2. Navigate to the **Final Preview** page
3. Click the **"Push to Active Campaign"** button
4. Select a subscriber list from the dropdown
5. Optionally edit the campaign name and subject
6. Click **"Push Campaign"**

The newsletter will be created as a campaign in Active Campaign and sent immediately to the selected list.

---

## ActiveCampaign API v3 - Detailed Endpoints

### Base URL & Authentication

```
Base URL: https://{your-account}.api-us1.com/api/3/
Header: Api-Token: {your-api-key}
```

All requests require the `Api-Token` header for authentication.

---

### Step 1: Get All Lists

Fetches all subscriber lists from your Active Campaign account.

**Endpoint:** `GET /api/3/lists`

**Request:**
```bash
curl -X GET "https://youraccountname.api-us1.com/api/3/lists" \
  -H "Api-Token: your-api-key"
```

**Response:**
```json
{
  "lists": [
    {
      "id": "1",
      "name": "Newsletter Subscribers",
      "stringid": "newsletter-subscribers",
      "cdate": "2024-01-15T10:30:00-05:00",
      "subscriber_count": 2345
    },
    {
      "id": "2",
      "name": "Test List",
      "stringid": "test-list",
      "cdate": "2024-02-01T08:00:00-05:00",
      "subscriber_count": 5
    }
  ],
  "meta": {
    "total": "2"
  }
}
```

**Query Parameters (optional):**
| Parameter | Description |
|-----------|-------------|
| `limit` | Number of lists to return (default: 20) |
| `offset` | Starting position for pagination |

---

### Step 2: Create a Message (Email Content)

Creates the email message with your HTML newsletter content.

**Endpoint:** `POST /api/3/messages`

**Request:**
```bash
curl -X POST "https://youraccountname.api-us1.com/api/3/messages" \
  -H "Api-Token: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "fromname": "Ready Artwork",
      "fromemail": "newsletter@readyartwork.com",
      "reply2": "newsletter@readyartwork.com",
      "subject": "Your Weekly Newsletter",
      "html": "<html><body>Your newsletter HTML here</body></html>",
      "text": "Plain text version of newsletter"
    }
  }'
```

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `fromname` | string | Sender display name |
| `fromemail` | string | Sender email address |
| `reply2` | string | Reply-to email address |
| `subject` | string | Email subject line |
| `html` | string | HTML content of the email |

**Optional Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Plain text version (fallback) |
| `preheader_text` | string | Preview text in inbox |

**Response:**
```json
{
  "message": {
    "id": "123",
    "subject": "Your Weekly Newsletter",
    "fromname": "Ready Artwork",
    "fromemail": "newsletter@readyartwork.com",
    "cdate": "2026-01-13T10:30:00-05:00"
  }
}
```

---

### Step 3: Create a Campaign

Creates a campaign in draft status linked to a specific list.

**Endpoint:** `POST /api/3/campaigns`

**Request:**
```bash
curl -X POST "https://youraccountname.api-us1.com/api/3/campaigns" \
  -H "Api-Token: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign": {
      "type": "single",
      "name": "January 2026 Newsletter",
      "sdate": null,
      "status": 0,
      "public": 1,
      "tracklinks": "all",
      "trackopens": 1,
      "lists": [
        {
          "list": "1"
        }
      ]
    }
  }'
```

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Campaign type: `"single"` for one-time |
| `name` | string | Internal campaign name |
| `lists` | array | Array of list objects with `list` ID |

**Optional Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `sdate` | datetime | Scheduled send date (null = immediate) |
| `status` | integer | Campaign status (see table below) |
| `public` | integer | 1 = show in archive, 0 = hide |
| `tracklinks` | string | `"all"`, `"mime"`, or `"none"` |
| `trackopens` | integer | 1 = track opens, 0 = don't track |

**Status Values:**
| Status | Meaning |
|--------|---------|
| 0 | Draft |
| 1 | Scheduled |
| 2 | Sending |
| 3 | Paused |
| 4 | Stopped |
| 5 | Completed / Send Now |

**Response:**
```json
{
  "campaign": {
    "id": "456",
    "name": "January 2026 Newsletter",
    "type": "single",
    "status": "0",
    "cdate": "2026-01-13T10:35:00-05:00"
  }
}
```

---

### Step 4: Link Message to Campaign

Associates the email message content with the campaign.

**Endpoint:** `POST /api/3/campaignMessages`

**Request:**
```bash
curl -X POST "https://youraccountname.api-us1.com/api/3/campaignMessages" \
  -H "Api-Token: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "campaignMessage": {
      "campaign": "456",
      "message": "123"
    }
  }'
```

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `campaign` | string | Campaign ID from Step 3 |
| `message` | string | Message ID from Step 2 |

**Response:**
```json
{
  "campaignMessage": {
    "id": "789",
    "campaign": "456",
    "message": "123"
  }
}
```

---

### Step 5: Send Campaign

Updates the campaign status to trigger immediate sending.

**Endpoint:** `PUT /api/3/campaigns/{campaignId}`

**Request:**
```bash
curl -X PUT "https://youraccountname.api-us1.com/api/3/campaigns/456" \
  -H "Api-Token: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign": {
      "status": 5
    }
  }'
```

**Response:**
```json
{
  "campaign": {
    "id": "456",
    "name": "January 2026 Newsletter",
    "type": "single",
    "status": "5"
  }
}
```

> **Note:** Setting `status: 5` triggers immediate sending to all subscribers on the linked list.

---

## Complete Implementation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Backend Implementation Flow                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. GET  /api/3/lists              → Fetch available lists      │
│     ↓                                                            │
│  2. POST /api/3/messages           → Create email with HTML     │
│     ↓                               (returns message_id)        │
│  3. POST /api/3/campaigns          → Create campaign draft      │
│     ↓                               (returns campaign_id)       │
│  4. POST /api/3/campaignMessages   → Link message to campaign   │
│     ↓                                                            │
│  5. PUT  /api/3/campaigns/{id}     → Set status=5 to send       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Your Backend API Endpoints

### GET `/activecampaign/lists`

Fetches all subscriber lists from your Active Campaign account.

**Response:**
```json
{
  "lists": [
    { "id": "1", "name": "Newsletter Subscribers" },
    { "id": "2", "name": "Test List" }
  ]
}
```

### POST `/activecampaign/push`

Creates and sends a campaign to a specific list.

**Request Body:**
```json
{
  "listId": "1",
  "campaignName": "January 2026 Newsletter",
  "subject": "Your Weekly Marketing Update",
  "htmlContent": "<html>...</html>",
  "senderName": "Ready Artwork",
  "senderEmail": "newsletter@readyartwork.com"
}
```

**Response:**
```json
{
  "success": true,
  "campaignId": "149",
  "message": "Campaign created and sent successfully"
}
```

---

## Error Handling

### Common Error Responses

| HTTP Code | Error | Solution |
|-----------|-------|----------|
| 401 | Unauthorized | Check API Key is valid |
| 403 | Forbidden | Check account permissions |
| 404 | Not Found | Verify list/campaign ID exists |
| 422 | Validation Error | Check required fields |
| 429 | Rate Limited | Reduce request frequency |

**Example Error Response:**
```json
{
  "message": "403 Forbidden",
  "errors": [
    {
      "title": "Forbidden",
      "detail": "You do not have permission to perform this action"
    }
  ]
}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Lists not loading | Check API URL and Key in `.env` |
| 401 Unauthorized | API Key is invalid or expired |
| Campaign not sending | Verify list has active subscribers |
| HTML not rendering | Ensure HTML is valid email-compatible markup |
| Message not linked | Ensure campaignMessages step completes before sending |

---

## Testing Recommendations

1. Create a **test list** with only your email address
2. Push to the test list first before sending to production lists
3. Verify formatting in the received email
4. Check Active Campaign dashboard to confirm campaign was created

---

## Rate Limits

ActiveCampaign API has the following limits:

- **5 requests per second** per account
- Implement exponential backoff for 429 responses
- Cache list data to reduce API calls
