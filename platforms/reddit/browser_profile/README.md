# browser_profile/ — a POINTER, not a profile

This directory holds **no browser profile data**. It is a pointer to the
identity's ONE shared persistent browser profile:

```
~/SocialAgent/identity/browser_profiles/<identity-id>/profile/
```

Per-platform workspaces each get their own workspace directory, but they
all share the same browser profile for one identity — the profile survives
VM restarts because it lives under the identity, not the platform.

`profile.json` carries the `identity_id`; resolve it with
`identity.store.read_platform_profile_pointer(home, platform)` or
`social-agent identity profile --identity <id>`.
