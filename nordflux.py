import argparse
import json
import logging
import math
import time
from datetime import date, timedelta
from typing import Optional

from influxdb import InfluxDBClient, SeriesHelper
from nordpool import elspot

DEFAULT_CONF_FILENAME = "nordflux.json"
AREAS = ["SE1", "SE2", "SE3", "SE4"]
CURRENCY = "SEK"


class NordpoolSeriesHelper(SeriesHelper):
    class Meta:
        series_name = "elspot"
        fields = ["cost"]
        tags = ["area", "currency"]


def nordflux(client, end_date: Optional[date] = None) -> None:

    spot = elspot.Prices(currency=CURRENCY)
    try:
        data = spot.hourly(areas=AREAS, end_date=end_date)
    except json.JSONDecodeError:
        logging.warning("No datapoints for %s", end_date)
        return

    has_datapoints = False

    for area in AREAS:
        for entry in data["areas"][area]["values"]:
            cost = entry["value"]
            if math.isinf(cost):
                continue
            NordpoolSeriesHelper(
                time=entry["start"].isoformat(),
                area=area,
                currency=CURRENCY,
                cost=cost,
            )
            has_datapoints = True

    if client is not None:
        if has_datapoints:
            NordpoolSeriesHelper.commit(client=client)
        else:
            logging.warning("No datapoints for %s", end_date)
    else:
        print(NordpoolSeriesHelper._json_body_())


def main() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="nordflux")
    parser.add_argument(
        "--conf",
        dest="conf_filename",
        default=DEFAULT_CONF_FILENAME,
        metavar="filename",
        help="configuration file",
        required=False,
    )
    parser.add_argument(
        "--begin",
        dest="begin_date",
        metavar="date",
        help="begin date",
        required=False,
    )
    parser.add_argument(
        "--end",
        dest="end_date",
        metavar="date",
        help="End date",
        required=False,
    )
    parser.add_argument(
        "--wait",
        dest="wait",
        metavar="seconds",
        help="Time to sleep between requests",
        type=int,
        default=0,
        required=False,
    )
    parser.add_argument("--test", dest="test", action="store_true", help="Test mode")
    parser.add_argument(
        "--debug", dest="debug", action="store_true", help="Print debug information"
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    with open(args.conf_filename) as config_file:
        config = json.load(config_file)

    client = (
        InfluxDBClient(
            host=config["hostname"],
            port=config.get("port", 8086),
            username=config["username"],
            password=config["password"],
            ssl=True,
            verify_ssl=True,
            database=config["database"],
        )
        if not args.test
        else None
    )

    begin_date = (
        date.fromisoformat(args.begin_date)
        if args.begin_date
        else date.today() + timedelta(days=1)
    )
    end_date = (
        date.fromisoformat(args.end_date)
        if args.end_date
        else date.today() + timedelta(days=1)
    )

    d = begin_date
    while d <= end_date:
        logging.debug("Processing %s", d)
        nordflux(client=client, end_date=d)
        d += timedelta(days=1)
        if d < end_date:
            time.sleep(args.wait)


if __name__ == "__main__":
    main()
