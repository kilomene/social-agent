"""Comment moderation: lexicon-based classifiers + auto-hide rules (stdlib only).

Scope rule (hard): social-agent only ever moderates the user's OWN comment
sections — creators may moderate their own posts. It never touches anyone
else's content. Hiding is an approval-gated acting operation (like engage):
proposals are created, and nothing is hidden without explicit approval or a
pre-approved auto-hide rule from policy.yaml.

Labels: ok | question | praise | spam | toxic
Priority: toxic > spam > question > praise > ok (a comment is classified by
its most severe signal).
"""
