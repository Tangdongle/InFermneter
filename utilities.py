from datetime import datetime, timedelta, timezone

TS_STR_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
# Strip the last characters from isoformat string to get rid of the pesky timezone
TS_STR_REPLACE_TZ_OFFSET = -6


def update_timestamp_file(fname):
    print("Updating timestamp file with new timestamp")
    with open(fname, "w") as ts:
        timestamp = datetime.now(timezone.utc).isoformat()
        ts.write(timestamp)


def get_last_timestamp(fname, **kwargs):
    last_run = datetime.now(timezone.utc) - timedelta(**kwargs)
    try:
        with open(fname, "r") as ts:
            last_run = datetime.strptime(ts.read()[:TS_STR_REPLACE_TZ_OFFSET], TS_STR_FORMAT)
            last_run = last_run.replace(tzinfo=timezone.utc)
    except FileNotFoundError:
        pass

    return last_run
