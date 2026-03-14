# Claude Code Project Guidelines

## Lessons & Preferences

### Before making big changes to a Home Assistant integration:
Always do an "investigation before big change" — document the current state of:
1. All devices and entities currently registered in HA (entity IDs, unique IDs, device names)
2. All automations, scripts, and dashboard cards that reference those entities
3. Any services registered by the integration and where they're used
4. The user should capture this from their live HA instance (Developer Tools > States, grep config files) since the repo only contains the integration code, not the HA instance config

This ensures everything can be restored to the same state after re-adding the integration, especially if entity IDs change.
