"""Human voice module: the agent must NOT write like an AI.

`check.py` scores draft text for AI-ness. `post draft` and `engage comment`
run it automatically and warn on robotic text. Banned phrases live in
banned.json; per-platform registers live in profiles/.
"""
