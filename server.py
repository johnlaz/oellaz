# OEL Command v12.0

**AI-powered sales operations command center — built for TRSAV and Odoo 19.**

OEL Command is a single-file Progressive Web App connecting your IMAP inbox, Odoo CRM, and Groq AI into one interface. Unified inbox management, AI-assisted project planning, smart quote building, vendor outreach, document library, and more — all in one place.

---

## Quick Start

**Requirements:** Python 3, Groq API key ([console.groq.com](https://console.groq.com)), Odoo 19 with API key.

```
Double-click start.bat
```

Starts both Python servers and opens the app in Chrome. Go to Settings on first launch — enter Odoo URL, database, username, API key, and Groq key.

---

## Servers

| File | Port | Purpose |
|------|------|---------|
| `imap_server.py` | 7843 | IMAP/SMTP, email fetch, lead capture, body parsing |
| `server.py` | 7842 | Odoo 19 XML-RPC CORS proxy |

---

## Feature Summary

- **Inbox** — Turbify/IMAP, Odoo, Gmail unified. AI reply drafts, log to Odoo, bounce detection.
- **Lead Capture** — Scan inbox for leads, AI extracts contact info, push to Odoo CRM. Forwarded email detection.
- **Activities** — Due today list, AI follow-up drafts, send via IMAP with auto-log.
- **Quotes** — Rental quote builder with Odoo catalog, template loader, push to sale.order.
- **Smart Builder** — Paste any request, AI extracts contact + equipment, fuzzy-matches catalog, pushes rental order.
- **Request Desk** — AI drafts TRSAV-style response to vague quote requests with clarifying questions.
- **Projects** — Odoo project/task browser, quick-add, task edit modal with AI rewrite, To Do list, AI Brainstorm chat.
- **Templates** — Reusable email templates with AI Composer.
- **Dormant Contacts** — Find inactive contacts, AI re-engagement drafts.
- **Bounce Manager** — Upload bounced email lists, match to Odoo contacts, tag as Bounced Email.
- **Vendor Outreach** — Find and email vendors, push to Odoo suppliers.
- **Document Library** — Upload W9s, COIs, contracts locally. Tag, filter, attach to Odoo contacts.
- **Dashboard** — CRM pipeline cards, accounting summary, AI daily briefing.

---

## Version History

| Version | Highlights |
|---------|-----------|
| **v12.0** | Customizable sidebar order — drag-free reorder via Settings modal |
| **v11.1** | Scroll fixed globally across all tabs and sub-panels |
| **v11.0** | Document Library, Bounce tagging (Bounced Email tag in Odoo), import/export includes docs |
| **v10.1** | Smart Builder tab (AI extract + catalog match + push to Odoo), Request Desk rename |
| **v10.0** | Projects tab, conversational AI brainstorm, task edit modal, Quote Desk |
| **v9.5**  | FWD email detection, contact override in lead modal, activity schedule fix |
| **v9.3**  | Templates section, Bounce Manager, Help guide, email body cleaner |

---

## Built By

Lazzaro · Powered by Groq AI + Odoo 19  
`OEL Command v12.0`
