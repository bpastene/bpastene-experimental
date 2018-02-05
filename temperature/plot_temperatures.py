"""
This script polls an attached USB temperature sensor, the specific product
being a SIENOC TEMPerHUM PC Laptop USB Sensor. Listed on Amazon at:
https://www.amazon.com/gp/product/B00HWP8U44
This script makes the GUI shipped with the device (and written in Chinese)
unnecessary.
Supported only on Windows. Requires pywinusb:
https://github.com/rene-aguirre/pywinusb
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
GRAPHED_SENSORS = set(['cpu_total_load', 'used_memory', 'gpu_core_temp'])


def parse_timestamp(timestamp):
  d = datetime.datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S')
  return d
  #epoch = datetime.datetime.utcfromtimestamp(0)
  #return int((d - epoch).total_seconds())


def get_header_positions(headers):
  """Returns dict with key = device name, value = row index."""
  i = 0
  position_mapping = {}
  for field in headers:
    if field:
      position_mapping[field] = i
    i += 1
  return position_mapping
      

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      'hw_temp_file', type=str,
      help='Path to hardware temperature report file.')
  parser.add_argument(
      '--ambient-temp-file', type=str,
      help='Optional path to ambient temperature report file.')
  args = parser.parse_args()
  
  timestamps = []
  data = collections.defaultdict(list)
  with open(args.hw_temp_file) as f:
    temp_reader = csv.reader(f)
    headers_device_names = temp_reader.next()
    headers_titles = temp_reader.next()
    position_mapping = get_header_positions(headers_device_names)
    for row in temp_reader:
      timestamps.append(parse_timestamp(row[0]))
      for field_name in GRAPHED_SENSORS:
        field_value = row[position_mapping[SENSOR_NAME_MAPPING[field_name]]]
        data[field_name].append(field_value)
    

  traces = []
  for sensor, values in data.iteritems():
    trace = plotly.graph_objs.Scatter(
        x = timestamps,
        y = values,
        name = sensor,
        line = {
            'color': 'rgb(%d, %d, %d)' % (
                int(random.random() * 255),
                int(random.random() * 255),
                int(random.random() * 255)
            ),
            'width': 4,
        }
    )
    traces.append(trace)
  
  layout = {
      'title': 'System Stats Over Time',
      'xaxis': {'title': 'Time'},
      'yaxis': {'title': 'Temperature (degrees C)'},
  }
  fig = {
      'data': traces,
      'layout': layout,
  }
  plotly.offline.plot(fig, filename='graphs.html')

  
if __name__ == '__main__':
  sys.exit(main())