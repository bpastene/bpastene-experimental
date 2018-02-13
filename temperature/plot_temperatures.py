"""
This script graphs system metrics recorded with OpenHardwareMonitor. The
graphs are rendered via the plotly py lib. The sensors mapped here correlate
with a Win8 machine with the following specs:
- gpu: Nvdia GTX 980
- cpu: Intel i7 4790
- mobo: Intel Z97-G45

It can optionally read a report file containing ambient temperature and
humidity levels as recorded by the get_usb_temp.py script in the same dir.

See OpenHardwareMonitor project:
http://openhardwaremonitor.org/
See plotly project:
https://plot.ly/python/
"""
import argparse
import collections
import csv
import datetime
import random
import sys

import plotly
import plotly.graph_objs as go


SENSOR_NAME_MAPPING = {
    'cpu_1_temp': '/intelcpu/0/temperature/0',
    'cpu_2_temp': '/intelcpu/0/temperature/1',
    'cpu_3_temp': '/intelcpu/0/temperature/2',
    'cpu_4_temp': '/intelcpu/0/temperature/3',
    'cpu_package_temp': '/intelcpu/0/temperature/4',
    'cpu_total_load': '/intelcpu/0/load/0',
    'cpu_1_load': '/intelcpu/0/load/1',
    'cpu_2_load': '/intelcpu/0/load/2',
    'cpu_3_load': '/intelcpu/0/load/3',
    'cpu_4_load': '/intelcpu/0/load/4',
    'gpu_core_temp': '/nvidiagpu/0/temperature/0',
    'gpu_fan': '/nvidiagpu/0/fan/0',
    'used_memory': '/ram/data/0',
}
AMBIENT_TEMP_NAME = 'ambient_temp'
AMBIENT_HUMIDITY_NAME = 'ambient_humidity'
CPU_AVG_TEMP_NAME = 'cpu_avg_temp'
AVAILABLE_SENSORS = SENSOR_NAME_MAPPING.keys() + [
    AMBIENT_TEMP_NAME, AMBIENT_HUMIDITY_NAME, CPU_AVG_TEMP_NAME]
OPTIMAL_COLORS = [
    (57, 106, 177),
    (218, 124, 48),
    (62, 150, 81),
    (204, 37, 41),
    (83, 81, 84),
    (107, 76, 154),
    (146, 36, 40),
    (148, 139, 61),
]


def parse_timestamp(timestamp):
  return datetime.datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S')


def get_header_positions(headers):
  """Returns dict with key = device name, value = row index."""
  i = 0
  position_mapping = {}
  for field in headers:
    if field:
      position_mapping[field] = i
    i += 1
  return position_mapping


def get_avg_cpu_temp(position_mapping, row):
  cpu1 = float(row[position_mapping[SENSOR_NAME_MAPPING['cpu_1_temp']]])
  cpu2 = float(row[position_mapping[SENSOR_NAME_MAPPING['cpu_2_temp']]])
  cpu3 = float(row[position_mapping[SENSOR_NAME_MAPPING['cpu_3_temp']]])
  cpu4 = float(row[position_mapping[SENSOR_NAME_MAPPING['cpu_4_temp']]])
  return (cpu1 + cpu2 + cpu3 + cpu4) / 4.0


def get_color():
  color_ind = 0
  while color_ind < len(OPTIMAL_COLORS):
    yield OPTIMAL_COLORS[color_ind]
    color_ind += 1
  yield (
      int(random.random() * 255),
      int(random.random() * 255),
      int(random.random() * 255),
  )


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--ambient-temp-file', type=str,
      help='Optional path to ambient temperature report file.')
  parser.add_argument(
      'hw_temp_files', type=str, nargs='+',
      help='Path to hardware temperature report file.')
  parser.add_argument(
      '--graphed-sensors', '-s', type=str, action='append',
      help='List of sensors to graph. Available options are: %s.' % (
          ', '.join(AVAILABLE_SENSORS)))
  args = parser.parse_args()


  ambient_timestamps = []
  ambient_data = collections.defaultdict(list)
  hw_timestamps = []
  hw_data = collections.defaultdict(list)

  if args.ambient_temp_file:
    with open(args.ambient_temp_file) as f:
      ambient_temp_reader = csv.reader(f)
      for row in ambient_temp_reader:
        timestamp = datetime.datetime.fromtimestamp(int(row[0]))
        temp_reading = float(row[1])
        humidity_reading = float(row[2])
        ambient_timestamps.append(timestamp)
        if AMBIENT_TEMP_NAME in args.graphed_sensors:
          ambient_data[AMBIENT_TEMP_NAME].append(temp_reading)
        if AMBIENT_HUMIDITY_NAME in args.graphed_sensors:
          ambient_data[AMBIENT_HUMIDITY_NAME].append(humidity_reading)


  for hw_temp_file in args.hw_temp_files:
    with open(hw_temp_file) as f:
      temp_reader = csv.reader(f)
      headers_device_names = temp_reader.next()
      headers_titles = temp_reader.next()
      position_mapping = get_header_positions(headers_device_names)
      for row in temp_reader:
        hw_timestamps.append(parse_timestamp(row[0]))
        for field_name in args.graphed_sensors:
          if field_name not in SENSOR_NAME_MAPPING:
            continue
          field_value = row[position_mapping[SENSOR_NAME_MAPPING[field_name]]]
          hw_data[field_name].append(field_value)
        if CPU_AVG_TEMP_NAME in args.graphed_sensors:
          hw_data[CPU_AVG_TEMP_NAME].append(
              get_avg_cpu_temp(position_mapping, row))


  traces = []

  color_gen = get_color()
  for reading_type, values in ambient_data.iteritems():
    trace = plotly.graph_objs.Scatter(
        x = ambient_timestamps,
        y = values,
        name = reading_type,
        line = {
            'color': 'rgb(%d, %d, %d)' % next(color_gen),
            'width': 4,
        }
    )
    traces.append(trace)

  for sensor, values in hw_data.iteritems():
    trace = plotly.graph_objs.Scatter(
        x = hw_timestamps,
        y = values,
        name = sensor,
        line = {
            'color': 'rgb(%d, %d, %d)' % next(color_gen),
            'width': 4,
        }
    )
    traces.append(trace)

  layout = {
      'title': 'System Stats Over Time',
      'xaxis': {'title': 'Time'},
      'yaxis': {
          'range': [0, 100],
          'title': 'Arbitrary Units (Maybe Celcius? Maybe Percent? '
                   'Who can say...?)',
      },
  }
  fig = {
      'data': traces,
      'layout': layout,
  }
  plotly.offline.plot(fig, filename='graphs.html')


if __name__ == '__main__':
  sys.exit(main())