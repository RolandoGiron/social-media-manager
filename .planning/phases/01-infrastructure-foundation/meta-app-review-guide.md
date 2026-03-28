# Meta App Review - Submission Guide for Clinic CRM

This guide walks through the entire process of creating a Facebook App, configuring it for social media publishing, and submitting it for Meta App Review. The review process takes 2-6 weeks, so submit as early as possible to avoid blocking social publishing features.

---

## Section 1: Prerequisites Checklist

Before starting, ensure the following are in place:

- [ ] Facebook Page for the clinic exists and is published
- [ ] Instagram account is converted to Business or Creator account
- [ ] Instagram account is linked to the Facebook Page (Settings > Accounts Center > Connected Accounts)
- [ ] A privacy policy URL is hosted and publicly accessible (can be a simple page on the clinic's website explaining data usage for social media scheduling)
- [ ] Domain for the app is registered (the VPS domain from `.env` DOMAIN)

## Section 2: Create Facebook App

1. Go to https://developers.facebook.com/apps/
2. Click "Create App"
3. Select app type: **Business**
4. App name: "[Clinic Name] Social Manager" (or similar)
5. App contact email: clinic admin email
6. Business portfolio: Select or create one for the clinic
7. After creation, note the **App ID** and **App Secret** -- store in `.env` as `META_APP_ID` and `META_APP_SECRET`

## Section 3: Configure App Settings

1. Go to App Dashboard > Settings > Basic
2. Set **Privacy Policy URL** to the clinic's privacy policy page
3. Set **App Domains** to your VPS domain
4. Set **Site URL** to `https://admin.DOMAIN` (the admin UI subdomain)
5. Save changes

## Section 4: Add Required Products

1. In the App Dashboard left sidebar, click "+ Add Product"
2. Add **Facebook Login for Business**
3. Add **Instagram Graph API** (from the products catalog)

## Section 5: Request Permissions for App Review

Request ONLY these permissions (minimal permissions reduce review friction):

| Permission | Purpose |
|---|---|
| `pages_manage_posts` | Required to publish posts to the clinic's Facebook Page |
| `pages_read_engagement` | Required to read post status and engagement metrics |
| `instagram_basic` | Required to read Instagram Business account info |
| `instagram_content_publish` | Required to publish posts to Instagram |

**Do NOT request** unnecessary permissions like `pages_manage_metadata`, `publish_video`, or `ads_management`. Extra permissions increase review scrutiny and delay approval.

For EACH permission, provide:

**Use case description:**
> Our clinic management platform allows the clinic administrator to schedule and publish promotional posts about dermatological treatments and services to the clinic's Facebook Page and Instagram Business account. The administrator writes the post content and schedules it through our internal admin panel. No user-generated content is published automatically.

**Steps to test:**
Include screenshots showing the admin UI post scheduling form (can be mockups initially).

**Video walkthrough:**
Record a 2-minute screen recording showing the flow from admin panel to published post (can simulate with mock data).

## Section 6: Submit for Review

1. Go to App Dashboard > App Review > Permissions and Features
2. Click "Request Advanced Access" for each permission listed above
3. Fill in the platform detail form with the use case descriptions above
4. Upload the video walkthrough
5. Submit the review request
6. Note: Review typically takes **2-6 weeks**. Check status at `https://developers.facebook.com/apps/[APP_ID]/review-status/`

## Section 7: While Waiting for Review

- The app can be used in **Development Mode** with test users (admin accounts added to the app as Testers in App Dashboard > Roles > Test Users)
- Continue building n8n social publishing workflows against the test user's pages
- If review is rejected, read the rejection reason carefully and resubmit with corrections
- **Fallback plan:** If review takes >4 weeks, integrate Buffer API (https://buffer.com/developers/api) as an intermediary -- Buffer already has Meta API approval

## Section 8: Post-Approval Steps

1. Switch app from "Development" to **"Live"** mode in App Dashboard
2. Generate a **long-lived Page Access Token** (valid 60 days, auto-refreshable)
3. Store the token in **n8n credentials manager** (NOT in workflow nodes)
4. Add `META_PAGE_ACCESS_TOKEN` to `.env` as backup reference
5. Set up a token refresh workflow in n8n that runs weekly to refresh the access token before expiry

---

*Guide created as part of Phase 01 (Infrastructure Foundation) to unblock Phase 06 (Social Media Publishing). Meta App Review is the longest lead-time external dependency in this project.*
