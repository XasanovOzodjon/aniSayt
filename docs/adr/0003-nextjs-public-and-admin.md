# Next.js for the public site and the admin panel

The public Animee UI and `/admin-panel` are Next.js talking to the existing Django API. Django admin is not the operator surface. We keep Django as the API and domain, not as the long-term HTML UI — templates already exist but cannot carry the motion, i18n, and dashboard the product needs.
