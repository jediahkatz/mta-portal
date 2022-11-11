# Write your code here :-)
import board
import digitalio
import time

import time
import microcontroller
from board import NEOPIXEL
import displayio

import adafruit_display_text.label
from adafruit_display_shapes.circle import Circle
from adafruit_datetime import datetime
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.matrix import Matrix
from adafruit_matrixportal.network import Network

LINE_TO_TIME_MAP = {
    "F": "?",
    "G": "?",
    "4": "?",
    "A": "?",
}

STOP_TO_LINE_MAP = {
    "fc33": ["G", "F"],
    "923c": ["A"],
    "4e75": ["4"],
}

STATUS_COLORS = {
    "OFF": 0x000000,
    "ERROR": 0x440000,
    "ON": 0x444444,
}

DATA_LOCATION = ["data"]
UPDATE_DELAY = 15
SYNC_TIME_DELAY = 20
MINIMUM_MINUTES_DISPLAY = 2
MAX_MINUTES_DISPLAY = 19
BACKGROUND_IMAGE = "background.bmp"
ERROR_RESET_THRESHOLD = 3


def get_arrival_in_minutes_from_now(now, date_str):
    train_date = datetime.fromisoformat(date_str).replace(
        tzinfo=None
    )  # Remove tzinfo to be able to diff dates
    return round((train_date - now).total_seconds() / 60.0)


def get_arrival_times(stop_id):
    data_url = "https://api.wheresthefuckingtrain.com/by-id/%s" % (stop_id,)
    stop_trains = network.fetch_data(data_url, json_path=(DATA_LOCATION,))

    northbound_trains = stop_trains[0]["N"]

    for line_name in STOP_TO_LINE_MAP[stop_id]:

        # Filter trains
        trains_in_line = [
            t["time"] for t in northbound_trains if t["route"] == line_name
        ]

        def map_train_to_time(time):
            time = get_arrival_in_minutes_from_now(datetime.now(), time)
            # Don't tell us about trains that are 0 or 1 minutes away
            if time < MINIMUM_MINUTES_DISPLAY:
                return None
            if time > MAX_MINUTES_DISPLAY:
                return None
            return time

        trains = list(
            filter(lambda x: x is not None, map(map_train_to_time, trains_in_line))
        )

        if len(trains) > 1:
            # Train time is less than 10 mins
            if trains[0] < 10:
                LINE_TO_TIME_MAP[line_name] = "%s,%s" % (trains[0], trains[1])
            # Diff between trains is less than 10 mins
            elif trains[1] - trains[0] < 10:
                LINE_TO_TIME_MAP[line_name] = "%s+%s" % (
                    trains[0],
                    trains[1] - trains[0],
                )
            else:
                LINE_TO_TIME_MAP[line_name] = "%s" % (trains[0])
        elif len(trains) == 1:
            LINE_TO_TIME_MAP[line_name] = "%s" % (trains[0])
        else:
            LINE_TO_TIME_MAP[line_name] = "-"


def update_text():
    for key, value in LINE_TO_TIME_MAP.items():
        LINE_TO_TEXT_MAP[key].text = value
    display.show(group)


def update_status(status):
    print("status", status)
    if status == "SLEEP":
        status_indicators[0].fill = STATUS_COLORS["ON"]
        status_indicators[1].fill = STATUS_COLORS["OFF"]
        status_indicators[2].fill = STATUS_COLORS["OFF"]
    elif status == "ERROR":
        status_indicators[0].fill = STATUS_COLORS["ERROR"]
        status_indicators[1].fill = STATUS_COLORS["ERROR"]
        status_indicators[2].fill = STATUS_COLORS["OFF"]
    elif status == "HTTP":
        status_indicators[0].fill = STATUS_COLORS["OFF"]
        status_indicators[1].fill = STATUS_COLORS["OFF"]
        status_indicators[2].fill = STATUS_COLORS["ON"]
    elif status == "DISPLAY":
        status_indicators[0].fill = STATUS_COLORS["OFF"]
        status_indicators[1].fill = STATUS_COLORS["ON"]
        status_indicators[2].fill = STATUS_COLORS["OFF"]
    elif status == "TIME":
        status_indicators[0].fill = STATUS_COLORS["ON"]
        status_indicators[1].fill = STATUS_COLORS["ON"]
        status_indicators[2].fill = STATUS_COLORS["OFF"]
        
    display.show(group)

    if status != "ERROR":
        time.sleep(0.5)
        for s in status_indicators:
            s.fill = STATUS_COLORS["OFF"]
        display.show(group)


# --- Display setup ---
matrix = Matrix()
display = matrix.display
network = Network(status_neopixel=NEOPIXEL, debug=False)

# --- Drawing setup ---

bitmap = displayio.OnDiskBitmap(open(BACKGROUND_IMAGE, "rb"))
colors = [0x444444]  # [dim white, gold]

y_offset = 8
x_offset = 16

font = bitmap_font.load_font("fonts/atari-small.bdf")

LINE_TO_TEXT_MAP = {
    "F": adafruit_display_text.label.Label(
        font, color=colors[0], x=x_offset, y=y_offset, text=""
    ),
    "G": adafruit_display_text.label.Label(
        font, color=colors[0], x=x_offset, y=(16 + y_offset), text=""
    ),
    "4": adafruit_display_text.label.Label(
        font, color=colors[0], x=(32 + x_offset), y=(y_offset), text=""
    ),
    "A": adafruit_display_text.label.Label(
        font, color=colors[0], x=(32 + x_offset), y=(16 + y_offset), text=""
    ),
}

text_lines = [
    # Background Image
    displayio.TileGrid(
        bitmap, pixel_shader=getattr(bitmap, "pixel_shader", displayio.ColorConverter())
    ),
] + list(LINE_TO_TEXT_MAP.values())

group = displayio.Group()
for x in text_lines:
    group.append(x)

status_indicators = [
    Circle(63, 31, 0, fill=STATUS_COLORS["OFF"]),
    Circle(62, 31, 0, fill=STATUS_COLORS["OFF"]),
    Circle(61, 31, 0, fill=STATUS_COLORS["OFF"]),
]

for si in status_indicators:
    group.append(si)
display.show(group)

error_counter = 0
last_time_sync = None
while True:
    try:
        update_text()
        
        if (
            last_time_sync is None
            or time.monotonic() > last_time_sync + SYNC_TIME_DELAY
        ):
            # Sync clock to minimize time drift
            update_status("TIME")
            network.get_local_time()
            last_time_sync = time.monotonic()
        for station_id in STOP_TO_LINE_MAP.keys():
            update_status("HTTP")
            get_arrival_times(station_id)
            update_status("DISPLAY")
            update_text()
    except (ValueError, RuntimeError) as e:
        update_status("ERROR")
        print("Some error occured, retrying! -", e)
        error_counter = error_counter + 1
        if error_counter > ERROR_RESET_THRESHOLD:
            microcontroller.reset()
    update_status("SLEEP")
    time.sleep(UPDATE_DELAY)
