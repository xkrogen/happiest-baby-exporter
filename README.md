# Happiest Baby Exporter

Export your journal data from the Happiest Baby API to CSV files.

This tool allows you to download and back up your baby's data from Happiest Baby (SNOO) in a structured CSV format for analysis, record-keeping, or migration to other tools.

## Features

- **Multiple journal types**: Exports breastfeeding, bottlefeeding, diaper, solid food, pumping, sleep, weight, height, and head circumference data
- **Flexible date ranges**: Specify how many days of data to export (default: 14 days)
- **Sleep tracking**: Provides both detailed and consolidated sleep session data
- **Unit selection**: Choose between imperial, metric, or both measurements
- **Easy authentication**: Uses your Happiest Baby email/password credentials
- **Multiple babies**: Automatically handles accounts with multiple babies

## Installation

### Install uv

This script uses [uv](https://github.com/astral-sh/uv), a fast Python package installer and runner.

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**With pip:**
```bash
pip install uv
```

For more installation options, see the [uv documentation](https://docs.astral.sh/uv/getting-started/installation/).

## Usage

### Option 1: Run directly from GitHub (no checkout required)

You can run the script directly from GitHub without cloning the repository:

```bash
uv run https://raw.githubusercontent.com/xkrogen/happiest-baby-exporter/refs/heads/main/happiest-baby-exporter.py
```

This will prompt you for your email and password interactively.

### Option 2: Clone and run locally

```bash
git clone https://github.com/xkrogen/happiest-baby-exporter.git
cd happiest-baby-exporter
./happiest-baby-exporter.py
```

Or with uv:

```bash
uv run happiest-baby-exporter.py
```

## Authentication

You can provide credentials in three ways:

1. **Interactive prompts** (most secure):
   ```bash
   ./happiest-baby-exporter.py
   ```

2. **Environment variables**:
   ```bash
   export HAPPIESTBABY_EMAIL="your-email@example.com"
   export HAPPIESTBABY_PASSWORD="your-password"
   ./happiest-baby-exporter.py
   ```

3. **Command-line options**:
   ```bash
   ./happiest-baby-exporter.py --email your-email@example.com --password your-password
   ```

## Command-Line Options

```
Options:
  --email TEXT               Email address (can use HAPPIESTBABY_EMAIL env var;
                             interactive prompt if not provided)
  --password TEXT            Password (can use HAPPIESTBABY_PASSWORD env var;
                             interactive prompt if not provided)
  --baby-name TEXT           Baby name to fetch data for (if not provided,
                             interactive selection will be provided, unless
                             there is only a single baby)
  --lookback-days INTEGER    Number of days to look back from today [default: 14]
  --output-dir DIRECTORY     Directory to save CSV files [default: .]
  --journal-type TEXT        Comma-separated list of journal types to export
                             (breastfeeding,bottlefeeding,diaper,solidfood,
                             pumping,sleep,weight,height,head; if not specified,
                             exports all types)
  --units [imperial|metric|both]
                             Unit system to use for measurements (both keeps
                             all columns) [default: imperial]
  --timezone TEXT            Timezone for sleep session data
                             [default: America/Los_Angeles]
  --encoding TEXT            Character encoding for CSV files (utf-8
                             recommended for emoji support) [default: utf-8]
  --help                     Show this message and exit.
```

## Examples

**Export all data for the last 30 days:**
```bash
./happiest-baby-exporter.py --lookback-days 30
```

**Export only sleep and diaper data:**
```bash
./happiest-baby-exporter.py --journal-type sleep,diaper
```

**Export with metric units:**
```bash
./happiest-baby-exporter.py --units metric
```

**Export with both imperial and metric units:**
```bash
./happiest-baby-exporter.py --units both
```

**Export growth tracking data (weight, height, head circumference):**
```bash
./happiest-baby-exporter.py --journal-type weight,height,head
```

**Export to a specific directory:**
```bash
./happiest-baby-exporter.py --output-dir ~/backup/baby-data
```

**Export for a specific baby (if you have multiple):**
```bash
./happiest-baby-exporter.py --baby-name SnoobyDoo
```

## Output Files

The script creates separate CSV files for each journal type:

- `journals_breastfeeding.csv` - Breastfeeding sessions
- `journals_bottlefeeding.csv` - Bottle feeding sessions
- `journals_diaper.csv` - Diaper changes
- `journals_solidfood.csv` - Solid food feedings
- `journals_pumping.csv` - Pumping sessions
- `journals_sleep.csv` - Consolidated sleep sessions (grouped by session ID)
- `journals_sleep_detailed.csv` - Detailed sleep data (all state changes)
- `journals_weight.csv` - Weight measurements
- `journals_height.csv` - Height/length measurements
- `journals_head.csv` - Head circumference measurements

## CSV Structure

All CSV files include:
- Baby name (except pumping journals)
- Start/end times where applicable
- Type-specific data (amounts, durations, etc.)
- Creation and update timestamps

Fields are ordered for easy reading: baby name first, followed by time fields, then data fields, and finally audit fields (createdAt, updatedAt).

## Privacy & Security

- Your credentials are only used to authenticate with the Happiest Baby API
- No data is sent to any third parties
- All data is saved locally to CSV files on your machine
- The script uses AWS Cognito for authentication (same as the official app)

## Requirements

- Python 3.12 or later
- Internet connection to access the Happiest Baby API

Dependencies are automatically managed by uv:
- `requests>=2.32.0` - HTTP library for API calls
- `click>=8.1.0` - Command-line interface framework

## License

MIT License - feel free to use and modify as needed.

## Disclaimer

This is an unofficial tool and is not affiliated with or endorsed by Happiest Baby, Inc. Use at your own risk.
