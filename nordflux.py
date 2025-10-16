import argparse
import asyncio
import datetime
import json
import logging
import time

import aiohttp
from influxdb import InfluxDBClient, SeriesHelper
from pynordpool import Currency, NordPoolClient

DEFAULT_CONF_FILENAME = "nordflux.json"
AREAS = ["SE1", "SE2", "SE3", "SE4"]

CURRENCY = Currency.SEK


class NordpoolSeriesHelper(SeriesHelper):
    class Meta:
        series_name = "elspot"
        fields = ["cost"]
        tags = ["area", "currency"]


async def nordflux(
    nordpool_client: NordPoolClient,
    influx_client: InfluxDBClient | None,
    start_date: datetime.date,
) -> None:
    """Fetch data from Nordpool and submit to InfluxDB"""

    delivery_period_datetime = datetime.datetime.combine(
        start_date,
        datetime.time(hour=0),
        tzinfo=datetime.UTC,
    )

    try:
        delivery_period_data = await nordpool_client.async_get_delivery_period(
            delivery_period_datetime, CURRENCY, AREAS
        )
    except json.JSONDecodeError:
        logging.warning("No datapoints for %s", delivery_period_datetime)
        return

    has_datapoints = False

    for entry in delivery_period_data.entries:
        for area in AREAS:
            NordpoolSeriesHelper(
                time=entry.start,
                area=area,
                currency=str(CURRENCY),
                cost=entry.entry[area],
            )
            has_datapoints = True

    if influx_client is not None:
        if has_datapoints:
            NordpoolSeriesHelper.commit(client=influx_client)
        else:
            logging.warning("No datapoints for %s", start_date)
    else:
        print(NordpoolSeriesHelper._json_body_())


async def async_main() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="Nordpool to InfluxDB exporter")
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

    influx_client = (
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
        datetime.date.fromisoformat(args.begin_date)
        if args.begin_date
        else datetime.date.today() + datetime.timedelta(days=1)
    )

    end_date = (
        datetime.date.fromisoformat(args.end_date)
        if args.end_date
        else datetime.date.today() + datetime.timedelta(days=1)
    )

    async with aiohttp.ClientSession() as session:
        nordpool_client = NordPoolClient(session)

        d = begin_date
        while d <= end_date:
            logging.debug("Processing %s", d)
            await nordflux(
                nordpool_client=nordpool_client,
                influx_client=influx_client,
                start_date=d,
            )
            d += datetime.timedelta(days=1)
            if d < end_date:
                time.sleep(args.wait)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
