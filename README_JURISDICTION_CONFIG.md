# Jurisdiction Configuration

RecoveryOS can be configured to work with different jurisdictions and regulatory contexts. By default, it uses generic/neutral language, but can be configured for specific regions like BC, Canada or the United States.

## Configuration Options

### Option 1: Using Configuration File (Recommended)

Set the `JURISDICTION_CODE` environment variable to one of the predefined configurations:

```bash
# For BC, Canada specific configuration
JURISDICTION_CODE=BC_CA

# For United States specific configuration  
JURISDICTION_CODE=US

# For generic/neutral configuration (default)
JURISDICTION_CODE=GENERIC
```

Available configurations are defined in `config/jurisdictions.json`.

### Option 2: Environment Variable Override

You can override specific settings using environment variables:

```bash
JURISDICTION_NAME="Your Region"
JURISDICTION_AGENCIES="Your Health Agency, NIDA, WHO"
JURISDICTION_COMPLIANCE="your compliance requirements"
CRISIS_LINE="your crisis line number"
EMERGENCY_NUMBER="your emergency number"
JURISDICTION_OPTIONS="Local | National | Global | Other"
```

## Adding New Jurisdictions

To add a new jurisdiction, edit `config/jurisdictions.json`:

```json
{
  "YOUR_CODE": {
    "display_name": "Your Region Name",
    "regulatory_agencies": [
      "Your Health Agency",
      "Other Relevant Agencies"
    ],
    "crisis_line": "your-crisis-number",
    "emergency_number": "your-emergency-number", 
    "compliance_rules": [
      "your compliance requirement 1",
      "your compliance requirement 2"
    ],
    "jurisdiction_options": ["Local", "National", "Global", "Other"]
  }
}
```

Then set `JURISDICTION_CODE=YOUR_CODE` in your environment.

## What Gets Configured

The jurisdiction configuration affects:

- **System Identity**: How the AI agents identify their operational context
- **Regulatory Agencies**: Which health agencies are prioritized in research
- **Compliance Rules**: What regulatory requirements are emphasized
- **Crisis Information**: Emergency contact numbers and crisis lines
- **Research Context**: Geographic scope for evidence evaluation

## Backward Compatibility

The system maintains full backward compatibility. If no jurisdiction is configured, it defaults to generic/neutral language that works globally.
