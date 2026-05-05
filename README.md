# OEL Command v12.0

**AI-powered sales operations command center — built for TRSAV and Odoo 19.**

OEL Command is a single-file Progressive Web App that connects your IMAP inbox, Odoo CRM, and Groq AI into one dark-luxury interface. From unified inbox management to vendor outreach, AI-assisted project planning to bounced email handling — every tool you need to move deals forward, all in one place.

---

## What It Does

### ✉ Unified Inbox
Pull Turbify/IMAP, Odoo, and Gmail into one view. Click any email row to expand the body inline — HTML noise, invisible tracking characters, and base64 image data are automatically stripped so you see clean text. Reply, AI-draft, log to Odoo, schedule an activity, or trash from each row.

**Bounce detection:** Delivery failure emails auto-detect the undeliverable address and pre-fill the Odoo contact search in the log note modal. Log the bounce to the correct contact in two clicks.

### ⚡ Activities
Scans Odoo activities due today. AI drafts a personalized follow-up email per contact using deal context and last chatter note. Review in the Send tab — compose via Quick Compose, log as a note, or send via IMAP with auto-log. Follow-up Tracker shows leads missing a scheduled activity.

### 📊 Dashboard & Reports
Eight CRM stat cards + four accounting cards. Click any for drill-down. AI Daily Briefing with Over Achiever mode. Quick reports: Aged AR, Top Customers (YTD), Overdue Notices — all print-ready with Save as PDF.

### 📝 Quote Desk
Paste any vague quote request and AI extracts contact info then drafts a TRSAV-style response with clarifying questions: event dates, venue, indoor/outdoor, audience size, AV needs, setup timing, budget. Custom prompt editor saves your own instructions without touching code. Push contact + opportunity to Odoo, schedule activity, or log draft to contact chatter.

### 🗂 Projects & Tasks
Four sub-tabs — all connected to Odoo's project module:

**Projects** — card grid of all Odoo projects. Click to view tasks or create new projects.

**Tasks** — filter by project, assignee, stage. Quick-add bar at the top. Full edit modal: name, description, stage, priority, assignee, deadline, chatter note, delete. Checkbox moves task to Done stage in Odoo (never deleted, always retrievable). AI Rewrite generates 3 alternative task name options.

**To Do** — personal tasks (localStorage-first), push any to Odoo. Sync imports existing personal Odoo tasks.

**✦ AI Brainstorm** — conversational AI planning. AI asks clarifying questions before generating tasks — holds a real conversation rather than immediately dumping a list. Tasks auto-appear in the Task Summary panel. Save last response as staged tasks, To Do items, or a new Odoo project with all tasks created inside it.

### 💤 Dormant Contacts
Finds contacts and opportunities with no recent activity. Filter by days inactive, type, rep, or tag. Search by name, company, or Odoo internal reference number. AI re-engagement drafts, send via IMAP, bulk schedule activities.

### 🏭 Vendor Outreach
Find Vendors opens YellowPages/Yelp/Google/ThomasNet pre-filled. Paste results → AI extracts contacts. Push to Odoo as suppliers. Blast quote request emails to all vendors.

### 📥 Lead Capture
Scans IMAP for inbound leads matching your specs. Forwarded emails auto-detected — AI extracts the real customer from the forwarded body. Contact override lets you link to an existing Odoo contact. One click creates CRM lead + partner + note + activity.

### 📭 Bounce Manager
Upload .txt or .csv of undeliverable emails. Fuzzy-matches against Odoo contacts. Per card: log bounce note, clear activities, reschedule follow-up. Bulk log to all matched contacts.

### 📋 Templates
Standalone sidebar section. Editor with variable insertion. AI Composer generates name, keywords, and body from a description (plain-text calls — no JSON errors). Templates populate every composer. Build from inbox email wizard creates templates from real conversations.

---

## How It Works

Single-file HTML/CSS/JS PWA. Two lightweight Python servers:

| Server | Port | Purpose |
|--------|------|---------|
| `imap_server.py` | 7843 | IMAP/SMTP, email body parsing, bounce detection |
| `server.py` | 7842 | Odoo 19 XML-RPC CORS proxy |

All Odoo data stays between your browser and your instance. AI calls go directly to Groq with your own key. No cloud storage, no analytics.

---

## Quick Start

**Requirements:** Python 3, Groq API key ([console.groq.com](https://console.groq.com)), Odoo 19 with API key enabled.

```
Double-click start.bat
```

Starts both servers and opens the app in Chrome. First-time: go to Settings, enter Odoo URL/database/username/API key and Groq key. Export credentials for backup.

---

## File Structure

```
OEL Command/
├── index.html            — The entire app (single file)
├── imap_server.py        — IMAP/SMTP server (port 7843)
├── server.py             — Odoo CORS proxy (port 7842)
├── manifest.json         — PWA manifest (v10.0.0)
├── sw.js                 — Service worker (cache: oel-v10.0)
├── start.bat             — Windows launcher
├── credentials.json      — Empty credentials template
└── icons/                — SVG + PNG icons (192, 512, maskable)
```

---

## Version History

| Version | Highlights |
|---------|-----------|
| **v10.0** | Projects tab (Projects/Tasks/To Do/AI Brainstorm), conversational AI, task edit modal with AI Rewrite, Done stage (not delete), Quote Desk TRSAV prompt with custom editor |
| v9.5 | Quote Desk, FWD email detection, contact override in lead modal, schedule activity fix |
| v9.3 | Templates standalone section, Bounce Manager, Help guide, email body cleaner |
| v9.2 | Bounce Manager, Help sidebar, template system with AI Composer |
| v9.1 | Contact search in log note modal, bounce address extraction |
| v9.0 | Activity draft→compose→log, vendor paste-extract, inbox body preview |
| v8.x | IMAP trash, inbox action bar, notes cleanup |
| v7.x | Dormant contacts, vendor outreach, accounting dashboard, remote support |

---

## Built By

Lazzaro · Powered by Groq AI + Odoo 19  
`OEL Command v10.0`
