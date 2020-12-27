import argparse
import json
import logging
import math

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


def nordflux(client) -> None:

    spot = elspot.Prices(currency=CURRENCY)
    data = spot.hourly(areas=AREAS)
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
        print(NordpoolSeriesHelper._json_body_())


def main() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="wapi2nsconf")
    parser.add_argument(
        "--conf",
        dest="conf_filename",
        default=DEFAULT_CONF_FILENAME,
        metavar="filename",
        help="configuration file",
        required=False,
    )
    parser.add_argument("--test", dest="test", action="store_true", help="Test mode")
    parser.add_argument(
        "--debug", dest="debug", action="store_true", help="Print debug information"
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    with open(args.conf_filename, "rt") as config_file:
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

    nordflux(client=client)


if __name__ == "__main__":
    main()
