[![PyPI version](https://badge.fury.io/py/vinyldns-python.svg)](https://badge.fury.io/py/vinyldns-python)
[![Verify & Code-Coverage](https://github.com/vinyldns/vinyldns-python/actions/workflows/verify.yml/badge.svg)](https://github.com/vinyldns/vinyldns-python/actions/workflows/verify.yml)
[![codecov](https://codecov.io/gh/vinyldns/vinyldns-python/branch/master/graph/badge.svg)](https://codecov.io/gh/vinyldns/vinyldns-python)
![GitHub](https://img.shields.io/github/license/vinyldns/vinyldns-python)

# vinyldns-python

Production-ready Python client for [VinylDNS](https://www.vinyldns.io/)

Direct support requests and bug reports to [GitHub Issues](https://github.com/vinyldns/vinyldns-python/issues).

## Requirements

Python 3.11 or newer is required.

## Installation

Install from PyPI:

```bash
pip install vinyldns-python
```

To run, `pip install vinyldns-python` and then:

**Option 1: Explicit credentials**

```python
from vinyldns.client import VinylDNSClient

client = VinylDNSClient(
    "https://vinyldns.example.com",
    "my-access-key",
    "my-secret-key"
)

# Use the client
zones = client.list_zones()
```
**Option 2: Environment-based credentials**

First, set the required environment variables:
```bash
export VINYLDNS_API_URL="https://vinyldns.example.com"
export VINYLDNS_ACCESS_KEY_ID="my-access-key"
export VINYLDNS_SECRET_ACCESS_KEY="my-secret-key"
```

Then in your python code:
```python
from vinyldns.client import VinylDNSClient
client = VinylDNSClient.from_env()

# Use the client
zones = client.list_zones()
```

## Utilities

Several command-line utilities are available under scripts/ for common VinylDNS operations.
## Contributing

**Requirements**

* `python3.11 or newer`
* `pip`
* `virtualenv`
* `tox`
* `pre-commit`

## Setup
Create and activate a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```
Install the package in editable mode with development dependencies:

```bash
pip install -e .
pip install tox pre-commit
```

Install pre-commit hooks:

```bash
pre-commit install
```

## Usage Examples

You can reference the [VinylDNS API documentation](https://www.vinyldns.io/api/index.html) for more details on each endpoint.

**List Zones**
```python
from vinyldns.client import VinylDNSClient

client = VinylDNSClient.from_env()

# List all zones
zones = client.list_zones()
for zone in zones.zones:
    print(f"{zone.name} - {zone.id}")

# Filter zones by name
filtered_zones = client.list_zones(name_filter="example")
```

**Retrieve and list record sets**
```python
# Get a specific record set
record_set = client.get_record_set(zone_id="zone-123", rs_id="recordset-456")
print(f"{record_set.name} {record_set.type} {record_set.ttl}")

# List all record sets in a zone
record_sets = client.list_record_sets(zone_id="zone-123")
for rs in record_sets.record_sets:
    print(f"{rs.name} {rs.type}")

# Filter record sets by name
filtered_rs = client.list_record_sets(
    zone_id="zone-123",
    record_name_filter="www"
)

# Search record sets globally across all zones
search_results = client.search_record_sets(
    record_name_filter="api",
    record_type_filter=["A", "CNAME"]
)
```

**Create and update a record set**

The following examples modify DNS data:
```python
from vinyldns.record import RecordSet

# Create a new A record
new_record = RecordSet(
    zone_id="zone-123",
    name="app",
    type="A",
    ttl=300,
    records=[{"address": "192.0.2.10"}]
)
change = client.create_record_set(new_record)
print(f"Created record set with change ID: {change.id}")

# Update an existing record set
record_set = client.get_record_set(zone_id="zone-123", rs_id="recordset-456")
record_set.ttl = 600
record_set.records = [{"address": "192.0.2.20"}]
update_change = client.update_record_set(record_set)
print(f"Updated record set with change ID: {update_change.id}")

# Delete a record set
delete_change = client.delete_record_set(zone_id="zone-123", rs_id="recordset-456")
print(f"Deleted record set with change ID: {delete_change.id}")
```

**Work with Groups**

The following examples modify DNS data:
```python
from vinyldns.membership import Group, User

# Create a group
new_group = Group(
    name="engineering-team",
    email="engineering@example.com",
    description="Engineering team DNS access",
    members=[User(id="user-123")],
    admins=[User(id="user-123")]
)
created_group = client.create_group(new_group)
print(f"Created group: {created_group.id}")

# Get a group
group = client.get_group("group-456")
print(f"Group name: {group.name}")

# List my groups
my_groups = client.list_my_groups()
for group in my_groups.groups:
    print(f"{group.name} - {group.id}")

# List group members
members = client.list_members_group(group_id="group-456")
for member in members.members:
    print(f"Member: {member.user_name}")
```

**Create a Batch Change**

The following examples modify DNS data:
```python
from vinyldns.batch_change import BatchChangeRequest, AddRecord, DeleteRecordSet

# Create a batch change with multiple updates
batch_request = BatchChangeRequest(
    comments="Update DNS records for new deployment",
    changes=[
        AddRecord(
            input_name="app.example.com.",
            type="A",
            ttl=300,
            record={"address": "192.0.2.100"}
        ),
        AddRecord(
            input_name="api.example.com.",
            type="CNAME",
            ttl=300,
            record={"cname": "app.example.com."}
        ),
        DeleteRecordSet(
            input_name="old-app.example.com.",
            type="A"
        )
    ]
)

batch_change = client.create_batch_change(batch_request)
print(f"Batch change created: {batch_change.id}")
print(f"Status: {batch_change.status}")

# Get batch change status
batch_status = client.get_batch_change(batch_change.id)
print(f"Current status: {batch_status.status}")

# List batch change summaries
batch_summaries = client.list_batch_change_summaries()
for summary in batch_summaries.batch_changes:
    print(f"{summary.user_name} - {summary.created_timestamp} - {summary.status}")
```


## Running Unit Tests

Unit tests are developed using [pytest](https://docs.pytest.org/en/latest/).  We use
[Responses](https://github.com/getsentry/responses), which allows for simple mocking of HTTP endpoints.

Run static checks and unit tests:

```bash
tox -e check,py3
```

Verify Apache license headers are present:

```bash
pre-commit run apache-license-header-check --all-files
```

**Functional Tests**

The functional tests start a self-contained Docker-based VinylDNS environment, run tests against it, and tear it down:

From your virtualenv, run `tox -e func_test`

This workflow requires Docker to be installed and running.

**Running a full build**

When you are finished writing your code you will want to run everything including linters.  The
simplest way to do this is to run `tox -e check,py3`, which will run static checks and run unit tests.

If you see any failures / warnings, correct them until `tox` runs successfully.

If you do not have `tox` in your environment, `pip install tox` to add it.  For more information you can
read the [tox docs](https://tox.readthedocs.io/en/latest/index.html).


## Local Development

The repository includes a self-contained Docker environment for local testing and development. This is the same environment used by the functional tests.

**Starting the VinylDNS environment:**

```bash
bash ./docker/docker-up-vinyldns.sh
```

This starts VinylDNS API on `http://localhost:9000` along with MySQL and BIND9 dependencies.

**Connecting to the local environment:**
```python
local_client = VinylDNSClient("http://localhost:9000", "okAccessKey", "okSecretKey")
```

**Stopping the environment:**

```bash
./docker/remove-vinyl-containers.sh
```

**Running tests against the local environment:**

The functional tests automatically manage the Docker environment:

```bash
tox -e func_test
```

This will start the VinylDNS Docker environment, run all functional tests against it, and tear it down when complete.
