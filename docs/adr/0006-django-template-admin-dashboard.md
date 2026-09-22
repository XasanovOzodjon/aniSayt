# Django-template dashboard is the Admin panel on this stack

The public site is still Django templates and JWT, so the Admin panel ships as `/dashboard/` in that same UI. Django `/admin/` remains for low-level model work. ADR 0003’s Next.js `/admin-panel` still stands as the later operator UI; we did not rebuild the public site in Next.js just to host a dashboard.
