# Edge: Nginx TLS, Redis, TURN

Public traffic terminates on Nginx with Let’s Encrypt. `/static/` is files from `collectstatic`; `/media/` (Range/HLS) and `/ws/` proxy to Daphne so Django can rewrite S3 playlists and keep Watch Party sync. `REDIS_URL` is required for more than one Daphne worker. Camera/mic across NATs needs `TURN_URL` plus username/credential (coturn in docker-compose); STUN alone is not enough. Mail credentials live in `.env`, never in settings.
