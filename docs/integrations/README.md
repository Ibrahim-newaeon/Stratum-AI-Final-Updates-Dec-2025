# External Integrations

## Supported Platforms
- Google Ads API
- Meta Marketing API
- TikTok Ads API
- Snapchat Marketing API

## Adding New Integrations
1. Create service in `services/{platform}/`
2. Implement signal collector
3. Add health calculation logic
4. Register in integration registry
5. Document API requirements

## Authentication
All API credentials stored in environment variables.
Never commit credentials to repository.
