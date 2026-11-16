# Nathan Café Floral

Website and owner CRM for Nathan Café Floral — a café, floral studio and private
event venue in Ahuntsic, Montréal.

## What is here

| Path | What it is |
|---|---|
| `index.html` | The public website. Bilingual FR/EN, one self-contained file. |
| `crm/index.html` | The owner's CRM: pipeline board, quotes, knowledge base. |
| `api/lead.js` | Receives enquiries from the website; the CRM reads them back. |
| `api/schema.sql` | Run once in Supabase to create the `leads` table. |

## How an enquiry reaches the owner

The website's two forms (brunch and private events) build the same record:

```json
{ "v":1, "id":"…", "at":"…", "source":"website", "form":"eventForm",
  "lang":"en", "name":"", "email":"", "phone":"",
  "event_type":"", "event_date":"", "guests":0, "message":"" }
```

Where that record goes depends on `window.NCF_ENDPOINT` near the end of
`index.html`:

**Empty (today).** The forms tell the visitor plainly that nothing was sent.
They never show a confirmation that did not happen.

**A form-to-email service** (Web3Forms, Formspree). The enquiry is emailed to
the venue with an `NCF-LEAD…` token at the bottom. Paste that line into the
CRM's Inbox and it becomes a lead with every field filled in. No server needed.

**`/api/lead`** (this repo). Enquiries go straight into Postgres and the CRM
collects them on its own. Needs the environment variables below.

## Going from pasted to automatic

1. Create a Supabase project and run `api/schema.sql` in its SQL editor.
2. In Vercel → Settings → Environment Variables, add:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY` — server only, never in a page
   - `CRM_READ_TOKEN` — any long random string
   - `SITE_ORIGIN` — e.g. `https://nathancafefloral.com`
3. Redeploy.
4. In `index.html`, set `window.NCF_ENDPOINT = "https://<your-domain>/api/lead"`.
5. In the CRM's Inbox, paste the same URL and press **Check now**.

Until step 2 is done `/api/lead` answers `503` and names the variable it is
missing, instead of failing silently.

## Not built yet

WhatsApp, the AI concierge, staff sign-in and per-event guest pages all need
credentials and a backend that does not exist yet. The CRM's **Integrations**
page lists each one as *Not connected* and names the credential it needs. None
of them will ever show as connected until a real call has succeeded.

## History

This repository previously held the Café Zaytouna site. That work is preserved
on the `cafe-zaytouna-archive` branch.
