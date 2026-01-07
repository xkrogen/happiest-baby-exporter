#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests>=2.32.0",
#   "click>=8.1.0",
# ]
# requires-python = ">=3.12"
# ///
"""
Export journal data from Happiest Baby API to CSV files.
"""

import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import requests


# API Configuration
API_BASE_URL = "https://api-us-east-1-prod.happiestbaby.com"
COGNITO_ENDPOINT = "https://cognito-idp.us-east-1.amazonaws.com/"
CLIENT_ID = "6kqofhc8hm394ielqdkvli0oea"

# API Endpoints
BABIES_ENDPOINT = "/us/me/v10/babies"
JOURNALS_ENDPOINT = "/cs/me/v11/babies/{baby_id}/journals/tracking"
PUMPING_ENDPOINT = "/cs/me/v11/pumping-journals/tracking"
SLEEP_ENDPOINT = "/ss/me/v11/babies/{baby_id}/sessions/daily"


def authenticate(email: str, password: str) -> str:
    """Authenticate with AWS Cognito and return IdToken."""
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    }

    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "AuthParameters": {
            "USERNAME": email,
            "PASSWORD": password,
        },
        "ClientId": CLIENT_ID,
    }

    try:
        response = requests.post(COGNITO_ENDPOINT, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if "AuthenticationResult" not in data:
            click.echo("Error: Authentication failed - no token in response", err=True)
            sys.exit(1)

        id_token = data["AuthenticationResult"]["IdToken"]
        return id_token

    except requests.exceptions.HTTPError as e:
        click.echo(f"Error: Authentication failed - {e}", err=True)
        try:
            error_data = e.response.json()
            if "__type" in error_data:
                click.echo(f"  {error_data['__type']}: {error_data.get('message', '')}", err=True)
        except:
            pass
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        click.echo(f"Error: Network error - {e}", err=True)
        sys.exit(1)


def fetch_babies(token: str) -> List[Dict[str, Any]]:
    """Fetch list of babies from API."""
    url = f"{API_BASE_URL}{BABIES_ENDPOINT}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        click.echo(f"Error: Failed to fetch babies - {e}", err=True)
        sys.exit(1)


def fetch_journals(
    baby_id: str,
    journal_type: str,
    from_date: datetime,
    to_date: datetime,
    token: str,
) -> List[Dict[str, Any]]:
    """Fetch journals of a specific type for a date range."""
    endpoint = JOURNALS_ENDPOINT.format(baby_id=baby_id)

    params = {
        "fromDateTime": from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toDateTime": to_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "journalType": journal_type,
    }

    headers = {
        "Authorization": f"Bearer {token}",
    }

    url = f"{API_BASE_URL}{endpoint}"
    click.echo(f"Fetching {journal_type} journals from {from_date.date()} to {to_date.date()}...")

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    click.echo(f"  Retrieved {len(data)} entries")
    return data


def fetch_pumping_journals(
    from_date: datetime,
    to_date: datetime,
    token: str,
) -> List[Dict[str, Any]]:
    """Fetch pumping journals for a date range."""

    params = {
        "fromDateTime": from_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "toDateTime": to_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }

    headers = {
        "Authorization": f"Bearer {token}",
    }

    url = f"{API_BASE_URL}{PUMPING_ENDPOINT}"
    click.echo(f"Fetching pumping journals from {from_date.date()} to {to_date.date()}...")

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    click.echo(f"  Retrieved {len(data)} entries")
    return data


def fetch_sleep_sessions(
    baby_id: str,
    from_date: datetime,
    to_date: datetime,
    token: str,
    timezone: str = "America/Los_Angeles",
) -> List[Dict[str, Any]]:
    """Fetch sleep sessions for a date range."""
    endpoint = SLEEP_ENDPOINT.format(baby_id=baby_id)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    url = f"{API_BASE_URL}{endpoint}"
    click.echo(f"Fetching sleep sessions from {from_date.date()} to {to_date.date()}...")

    all_sessions = []
    current_date = from_date.replace(hour=6, minute=0, second=0, microsecond=0)

    # The API fetches sessions per day, so iterate through each day
    while current_date.date() <= to_date.date():
        params = {
            "detailedLevels": "true",
            "levels": "true",
            "startTime": current_date.strftime("%Y-%m-%d %H:%M:%S.000"),
            "timezone": timezone,
        }

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        # The API returns a dict with 'levels' containing the actual session list
        if isinstance(data, dict) and 'levels' in data:
            sessions = data['levels']
        elif isinstance(data, list):
            sessions = data
        else:
            sessions = []

        all_sessions.extend(sessions)
        current_date += timedelta(days=1)

    click.echo(f"  Retrieved {len(all_sessions)} entries")
    return all_sessions


def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_", preserve_lists: bool = False) -> Dict[str, Any]:
    """Flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep, preserve_lists=preserve_lists).items())
        elif isinstance(v, list):
            if preserve_lists:
                # Keep lists as-is for later processing
                items.append((new_key, v))
            else:
                # Convert lists to JSON strings for CSV compatibility
                items.append((new_key, json.dumps(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def clean_journal_entry(
    entry: Dict[str, Any],
    journal_type: str,
    units: str,
    baby_id: Optional[str] = None,
    baby_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Clean and transform a journal entry according to export rules."""
    cleaned = {}

    # Add babyName for all journal types except pumping (if we have it)
    if journal_type != "pumping" and baby_name:
        cleaned["babyName"] = baby_name

    for key, value in entry.items():
        # Skip id, userId, and isActive fields
        if key in ("id", "userId", "isActive"):
            continue

        # Replace babyId with babyName (skip the babyId field entirely since we added babyName above)
        if key == "babyId":
            continue

        # Remove 'data_' prefix
        if key.startswith("data_"):
            key = key[5:]  # Remove 'data_' prefix

        # Handle units - keep only imperial or metric (or both if units == "both")
        if units == "imperial":
            # Skip metric fields
            if key.endswith("Metric") or key.endswith("_ml") or "metric" in key.lower():
                continue
        elif units == "metric":
            # Skip imperial fields
            if key.endswith("Imperial") or key.endswith("_oz") or "imperial" in key.lower():
                continue
        # If units == "both", keep all fields

        # Special handling for diaper types field
        if journal_type == "diaper" and key == "types" and isinstance(value, list):
            # Convert list to comma-separated string
            value = ",".join(value)
        elif isinstance(value, list):
            # For any other lists, convert to JSON string
            value = json.dumps(value)

        cleaned[key] = value

    return cleaned


def order_fields(fieldnames: List[str]) -> List[str]:
    """Order fields with babyName first, time fields next, and audit fields last."""
    baby_name_field = []
    time_fields = []
    audit_fields = []
    other_fields = []

    for field in fieldnames:
        if field == "babyName":
            baby_name_field.append(field)
        elif field in ("startTime", "endTime"):
            time_fields.append(field)
        elif field in ("createdAt", "updatedAt"):
            audit_fields.append(field)
        else:
            other_fields.append(field)

    # Order time fields: startTime first, then endTime
    if "startTime" in time_fields and "endTime" in time_fields:
        time_fields = ["startTime", "endTime"]
    elif "startTime" in time_fields:
        time_fields = ["startTime"]
    elif "endTime" in time_fields:
        time_fields = ["endTime"]

    other_fields.sort()
    audit_fields.sort()  # createdAt, updatedAt alphabetically

    return baby_name_field + time_fields + other_fields + audit_fields


def export_to_csv(
    journals: List[Dict[str, Any]],
    output_file: str,
    journal_type: str,
    units: str,
    baby_id: Optional[str] = None,
    baby_name: Optional[str] = None,
    encoding: str = "utf-8",
) -> None:
    """Export journal data to CSV file."""
    if not journals:
        click.echo(f"  No data to export to {output_file}")
        return

    # Flatten all dictionaries, preserving lists for diaper type
    preserve_lists = (journal_type == "diaper")
    flattened = [flatten_dict(journal, preserve_lists=preserve_lists) for journal in journals]

    # Clean entries
    cleaned = [clean_journal_entry(entry, journal_type, units, baby_id, baby_name) for entry in flattened]

    # Get all unique keys across all entries
    all_keys = set()
    for entry in cleaned:
        all_keys.update(entry.keys())

    # Order fieldnames
    fieldnames = order_fields(list(all_keys))

    with open(output_file, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned)

    click.echo(f"  Exported to {output_file}")


def consolidate_sleep_sessions(sleep_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Consolidate sleep entries by sessionId."""
    from collections import defaultdict
    from datetime import datetime as dt

    sessions = defaultdict(list)

    # Group by sessionId
    for entry in sleep_entries:
        session_id = entry.get("sessionId")
        if session_id:
            sessions[session_id].append(entry)

    consolidated = []

    for session_id, entries in sessions.items():
        # Find earliest start time
        start_times = []
        for entry in entries:
            start_time = entry.get("startTime")
            if start_time:
                try:
                    # Parse the time string
                    parsed_time = dt.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")
                    start_times.append((parsed_time, start_time))
                except:
                    start_times.append((dt.max, start_time))

        if not start_times:
            continue

        earliest_time = min(start_times)[1]

        # Sum durations
        total_duration = sum(
            entry.get("stateDuration", 0)
            for entry in entries
            if isinstance(entry.get("stateDuration"), (int, float))
        )

        # Get distinct types (sorted)
        types = sorted(set(
            entry.get("type")
            for entry in entries
            if entry.get("type")
        ))
        types_str = ",".join(types)

        # Create consolidated entry with fields from first entry
        consolidated_entry = entries[0].copy()
        consolidated_entry["startTime"] = earliest_time
        consolidated_entry["stateDuration"] = total_duration
        consolidated_entry["type"] = types_str

        consolidated.append(consolidated_entry)

    # Sort by start time
    consolidated.sort(key=lambda x: x.get("startTime", ""))

    return consolidated


def extract_baby_id_from_logs(log_file: str) -> str:
    """Extract baby_id from request logs."""
    log_path = Path(log_file)
    if not log_path.exists():
        click.echo(f"Error: Request log file '{log_file}' not found", err=True)
        sys.exit(1)

    with open(log_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("URL", "")
            if "/babies/" in url and "/journals/" in url:
                # Extract baby_id from URL
                parts = url.split("/babies/")[1].split("/")
                return parts[0]

    click.echo("Error: Could not find baby_id in request logs", err=True)
    sys.exit(1)


@click.command()
@click.option(
    "--email",
    envvar="HAPPIESTBABY_EMAIL",
    prompt=True,
    help="Email address (can use HAPPIESTBABY_EMAIL env var; interactive prompt if not provided)",
)
@click.option(
    "--password",
    envvar="HAPPIESTBABY_PASSWORD",
    prompt=True,
    hide_input=True,
    help="Password (can use HAPPIESTBABY_PASSWORD env var; interactive prompt if not provided)",
)
@click.option(
    "--baby-name",
    help="Baby name to fetch data for (if not provided, interactive selection will be provided, unless there is only a single baby)",
)
@click.option(
    "--lookback-days",
    type=int,
    default=14,
    help="Number of days to look back from today",
    show_default=True,
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=".",
    help="Directory to save CSV files",
    show_default=True,
)
@click.option(
    "--journal-type",
    help="Comma-separated list of journal types to export (breastfeeding,bottlefeeding,diaper,solidfood,pumping,sleep,weight,height,head; if not specified, exports all types)",
)
@click.option(
    "--units",
    type=click.Choice(["imperial", "metric", "both"], case_sensitive=False),
    default="imperial",
    help="Unit system to use for measurements (both keeps all columns)",
    show_default=True,
)
@click.option(
    "--timezone",
    default="America/Los_Angeles",
    help="Timezone for sleep session data",
    show_default=True,
)
@click.option(
    "--encoding",
    default="utf-8",
    help="Character encoding for CSV files (utf-8 recommended for emoji support)",
    show_default=True,
)
def main(
    email: str,
    password: str,
    baby_name: Optional[str],
    lookback_days: int,
    output_dir: Path,
    journal_type: Optional[str],
    units: str,
    timezone: str,
    encoding: str,
) -> None:
    """Export journal data from Happiest Baby API to CSV files.

    Each journal type will be exported to a separate CSV file named
    'journals_<type>.csv' in the output directory.
    """
    # Authenticate
    click.echo("Authenticating with Happiest Baby...")
    token = authenticate(email, password)
    click.echo("✓ Authentication successful")
    click.echo()

    # Determine journal types to export
    if journal_type:
        # Parse comma-separated list
        valid_types = ["breastfeeding", "bottlefeeding", "diaper", "solidfood", "pumping", "sleep", "weight", "height", "head"]
        journal_types = [t.strip().lower() for t in journal_type.split(",")]

        # Validate types
        invalid_types = [t for t in journal_types if t not in valid_types]
        if invalid_types:
            click.echo(f"Error: Invalid journal type(s): {', '.join(invalid_types)}", err=True)
            click.echo(f"Valid types: {', '.join(valid_types)}", err=True)
            sys.exit(1)
    else:
        journal_types = ["breastfeeding", "bottlefeeding", "diaper", "solidfood", "pumping", "sleep", "weight", "height", "head"]

    # Get baby_id only if needed (not needed for pumping journals only)
    needs_baby_id = any(jtype != "pumping" for jtype in journal_types)
    baby_id = None
    selected_baby_name = None

    if needs_baby_id:
        click.echo("Fetching babies from API...")
        babies = fetch_babies(token)

        if not babies:
            click.echo("Error: No babies found in your account", err=True)
            sys.exit(1)

        if baby_name is not None:
            # Find baby by name
            matching_babies = [b for b in babies if b.get("babyName", "").lower() == baby_name.lower()]

            if not matching_babies:
                click.echo(f"Error: No baby found with name '{baby_name}'", err=True)
                click.echo("Available babies:", err=True)
                for baby in babies:
                    click.echo(f"  - {baby.get('babyName', 'Unknown')}", err=True)
                sys.exit(1)

            baby_id = matching_babies[0]["_id"]
            selected_baby_name = matching_babies[0].get("babyName", "Unknown")
            click.echo(f"✓ Using baby: {selected_baby_name}")
        elif len(babies) == 1:
            baby_id = babies[0]["_id"]
            selected_baby_name = babies[0].get("babyName", "Unknown")
            click.echo(f"✓ Using baby: {selected_baby_name}")
        else:
            click.echo(f"Found {len(babies)} babies:")
            for i, baby in enumerate(babies, 1):
                name = baby.get("babyName", "Unknown")
                click.echo(f"  {i}. {name}")

            choice = click.prompt("Select baby number", type=int)
            if choice < 1 or choice > len(babies):
                click.echo("Error: Invalid selection", err=True)
                sys.exit(1)

            baby_id = babies[choice - 1]["_id"]
            selected_baby_name = babies[choice - 1].get("babyName", "Unknown")
            click.echo(f"✓ Selected baby: {selected_baby_name}")

    click.echo()

    # Set date range
    to_date = datetime.now(dt_timezone.utc)
    from_date = to_date - timedelta(days=lookback_days)

    click.echo(f"Fetching data from {from_date.date()} to {to_date.date()}")
    click.echo()

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export each journal type
    for jtype in journal_types:
        try:
            if jtype == "pumping":
                journals = fetch_pumping_journals(from_date, to_date, token)
            elif jtype == "sleep":
                journals = fetch_sleep_sessions(baby_id, from_date, to_date, token, timezone)
            else:
                journals = fetch_journals(baby_id, jtype, from_date, to_date, token)

            if jtype == "sleep":
                # Export detailed sleep data
                detailed_output = output_dir / "journals_sleep_detailed.csv"
                export_to_csv(journals, str(detailed_output), jtype, units, baby_id, selected_baby_name, encoding)

                # Export consolidated sleep data
                consolidated_output = output_dir / "journals_sleep.csv"
                consolidated = consolidate_sleep_sessions(journals)
                export_to_csv(consolidated, str(consolidated_output), jtype, units, baby_id, selected_baby_name, encoding)
            else:
                output_file = output_dir / f"journals_{jtype}.csv"
                export_to_csv(journals, str(output_file), jtype, units, baby_id, selected_baby_name, encoding)

            click.echo()
        except requests.exceptions.HTTPError as e:
            click.echo(f"  Error fetching {jtype}: {e}", err=True)
            click.echo()
        except Exception as e:
            click.echo(f"  Unexpected error for {jtype}: {e}", err=True)
            click.echo()

    click.echo("Export complete!")


if __name__ == "__main__":
    main()
