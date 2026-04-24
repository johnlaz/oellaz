# OEL Command

**Your AI-powered sales operations command center — built for Odoo 19.**

OEL Command is a single-file Progressive Web App that sits alongside your Odoo CRM and turns your daily sales workflow into a streamlined, AI-assisted operation. From unified inbox management to vendor outreach, activity drafting to bounce handling — everything you need to move deals forward, all in one dark-luxury interface.

---

## What It Does

### ✉ Unified Inbox
Pull your Turbify/IMAP, Odoo, and Gmail messages into one view. Click any email to expand the body inline. Reply, AI-draft, log to Odoo, schedule an activity, or move to trash — all without leaving the app. Bounce-back emails are automatically detected and the undeliverable address is surfaced so you can log the failure to the correct contact instantly.

### ⚡ Activities
Connects to your Odoo CRM and scans activities due today. AI drafts a personalized follow-up email for each one using deal context and last chatter note. Review in the Send tab — compose via Quick Compose, log the draft as an Odoo note, or send directly via IMAP. The Follow-up Tracker shows which pushed leads are missing a scheduled activity.

### 📊 Dashboard & Reports
Eight CRM stat cards — Pipeline Value, Open Opportunities, Won This Month, Due Today, Odoo Inbox, Stalled Deals, Closing This Month, Lost This Month. Click any card for a drill-down. Daily AI Briefing summarizes your pipeline, wins, due activities, and stale deals — with Over Achiever mode that scans flagged emails for action items. Email the briefing to yourself with one click.

Accounting cards pull directly from Odoo: Open AR, Overdue, Revenue MTD, Collected MTD. Quick reports — Aged AR, Top Customers, Overdue Notices — open print-ready in a new tab.

### 📋 Templates
Dedicated template management section. Build templates manually with a rich editor and clickable variable insertion (`{{customer_name}}`, `{{subject}}`, `{{date}}`, and more). Or use the **AI Composer** — describe what you need, pick a tone, and AI writes the name, keywords, and body as three separate plain-text calls (no JSON parsing, no errors). Templates are available in every composer across the app and included in credential export/import.

### 💤 Dormant Contacts
Finds open opportunities and contacts with no scheduled activity and no recent movement. Filter by stage, rep, minimum revenue, or exclude a tag. AI drafts warm re-engagement emails. Send via IMAP with auto-log to Odoo, or bulk-schedule a follow-up activity on all selected contacts at once.

### 🏭 Vendor Outreach
Find subcontractors and vendors, send quote requests, track responses. Search your Odoo purchase/vendors by location and equipment type. The **Find Vendors** button opens YellowPages, Yelp, Google, and ThomasNet pre-filled with your search — paste results back in and AI extracts structured contact data. Pending vendors appear in a gold-bordered section. Push individually or all at once to Odoo as `res.partner` with `supplier_rank=1`. Blast quote request emails to all selected vendors.

### 📥 Lead Capture
Scans your IMAP inbox for inbound leads matching your configured specs. AI extracts contact name, phone, email, and notes. One click pushes a `crm.lead`, creates the `res.partner`, logs a chatter note, and schedules a follow-up activity in Odoo.

### 📭 Bounce Manager
Upload a `.txt` or `.csv` of undeliverable email addresses (or paste them directly). The app fuzzy-matches each against Odoo contacts — exact email first, then local-part matching. For each match: log a bounce note to the Odoo chatter, clear all scheduled activities, or reschedule a "verify contact info" activity. Bulk log notes on all matched contacts at once.

### 💬 Discuss
Check your Odoo inbox directly from the app. Log notes and schedule activities on any lead or contact.

### 🔧 Remote Support
One-click launchers for Quick Assist, Windows RDP, AnyDesk, and TeamViewer. Pre-written session invite emailer — pick the tool, enter your ID, and a professional connection guide opens in Quick Compose ready to send to your client.

### 📄 Documents
Upload PDFs and annotate them — text labels, signatures, highlights. Multi-page print-to-PDF. Save and reload signature.

---

## How It Works

OEL Command is a **single-file HTML/CSS/JavaScript PWA**. No frameworks, no build tools, no cloud dependency. Everything runs locally on your machine.

Two lightweight Python servers handle the heavy lifting:

| Server | Port | Purpose |
|--------|------|---------|
| `imap_server.py` | 7843 | IMAP/SMTP — fetch email, send email, lead capture, body parsing |
| `server.py` | 7842 | Odoo XML-RPC CORS proxy — all Odoo API calls |

All Odoo data stays between your browser and your Odoo instance. No third-party cloud. AI calls go directly to Groq's API using your own key.

---

## Quick Start

### Requirements
- Windows 10/11 (or any OS with Python 3.8+)
- Python 3 (`python.org`)
- Groq API key (free — `console.groq.com`)
- Odoo 19 instance with API key enabled

### Launch
```
Double-click start.bat
```
This starts both Python servers, registers auto-launch on Windows startup, and opens the app in Chrome.

Or start servers manually:
```
python imap_server.py   # port 7843
python server.py        # port 7842
```

### First-time setup
1. Open **Settings** (bottom of sidebar)
2. Enter your Odoo URL, database, username, and API key
3. Enter your Groq API key
4. Configure IMAP credentials in **Lead Capture** settings
5. Click **Export credentials** to save a backup JSON

---

## Feature Reference

### AI
- Powered by **Groq** (`llama-3.3-70b-versatile` by default, switchable)
- Used in: activity email drafting, inbox reply drafting, daily briefing, template AI Composer, lead extraction from email, vendor contact extraction, AI note cleanup, dormant contact re-engagement emails
- All prompts are grounded — AI only summarizes content you provide, never invents facts

### Email
- Send via IMAP/SMTP directly from the app
- All sent emails auto-log to Odoo chatter
- Bounce detection: `<email@domain>` addresses preserved through HTML stripping
- Quick Compose available from every section of the app

### Odoo Integration
- Odoo 19 XML-RPC API (all calls use correct `[[id]]` double-bracket syntax)
- Creates and updates: `crm.lead`, `res.partner`, `mail.activity`, `sale.order`, `account.move`
- Reads: pipeline, activities, accounting invoices, inbox messages, contacts, vendors
- All write operations surface errors — nothing fails silently

### Data & Privacy
- **All data is local** — credentials in `localStorage`, no cloud storage
- Export/import credentials as JSON (includes templates, specs, contacts, notes)
- Service worker caches the app shell for offline access
- No analytics, no ads, no telemetry

---

## File Structure

```
OEL Command/
├── index.html          — The entire app (HTML + CSS + JS, single file)
├── imap_server.py      — IMAP/SMTP server (port 7843)
├── server.py           — Odoo CORS proxy (port 7842)
├── manifest.json       — PWA manifest
├── sw.js               — Service worker (cache key: oel-v9.3)
├── start.bat           — Windows launcher
├── credentials.json    — Default empty credentials template
└── icons/
    ├── icon.svg
    ├── icon-192.png
    ├── icon-512.png
    ├── icon-maskable-192.png
    └── icon-maskable-512.png
```

---

## Version History

| Version | Highlights |
|---------|-----------|
| v9.3 | Templates as standalone sidebar section, AI Composer (3-call plain text), bounce manager, help guide, Follow-up Tracker fixed |
| v9.2 | Bounce Manager with fuzzy Odoo matching, Help sidebar section, template system rebuilt |
| v9.1 | Contact search override in log note modal, bounce email extraction from IMAP body (strip_html fix), Follow-up Tracker fixed |
| v9.0 | Activity draft→compose→log flow, vendor paste-extract with push-to-Odoo, inbox body preview, email preview modal |
| v8.0 | Inbox panel action bar, IMAP trash endpoint, notes cleanup modal, templates tab load fix |
| v7.x | Dormant contacts, vendor outreach, document center, accounting dashboard, remote support, bulk schedule |

---

## Built By

Lazzaro · Powered by Groq AI + Odoo 19  
`OEL Command v9.3`
