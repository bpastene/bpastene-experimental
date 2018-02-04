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
import math
import msvcrt
import os
from pywinusb import hid
import sys
import time
import traceback


DEVICE_VENDOR_ID = 16701  # 413d in hex
DEVICE_PRODUCT_ID = 8455  # 2107 in hex
DEVICE_IN_OUT_USAGE = 4278190081L
DEVICE_FEATURE_USAGE = 786432


def parse_data(raw_data):
  assert len(raw_data) == 9, 'raw data in unknown format'
  assert all(isinstance(d, int) for d in raw_data), (
      'raw data in unknown format')
  temp_most_significant_byte = raw_data[3]
  temp_least_significant_byte = raw_data[4]
  humidity_most_significant_byte = raw_data[5]
  humidity_least_significant_byte = raw_data[6]
  # Note that this probably won't work with negative temperatures. The
  # supported range is -40 to 80 C on the device, but this script will only
  # work for >0 C.
  temp = (
      (temp_most_significant_byte * math.pow(2, 8)) +
      temp_least_significant_byte)
  humidity = (
      (humidity_most_significant_byte * math.pow(2, 8)) +
      humidity_least_significant_byte)
  return temp / 100.0, humidity / 100.0


def find_usb_temp_sensor():
  all_devices = hid.find_all_hid_devices()
  for d in all_devices:
    if d.vendor_id == DEVICE_VENDOR_ID and d.product_id == DEVICE_PRODUCT_ID:
      return d


def initialize_device(out_report):
  # These packets, sent in this order, initializes the device for reporting.
  # http://i0.kym-cdn.com/entries/icons/original/000/008/342/ihave.jpg
  packets = [
      [0x01, 0x86, 0xFF, 0x01, 0x00, 0x00, 0x00, 0x00],
      [0x01, 0x87, 0xEE, 0x00, 0x00, 0x00, 0x00, 0x00],
      [0x01, 0x82, 0x77, 0x01, 0x00, 0x00, 0x00, 0x00],
  ]
  for packet in packets:
    out_report[DEVICE_IN_OUT_USAGE] = packet
    out_report.send()
    time.sleep(1)


def get_temperature(out_report):
  request_packet = [0x01, 0x80, 0x33, 0x01, 0x00, 0x00, 0x00, 0x00]
  out_report[DEVICE_IN_OUT_USAGE] = request_packet
  out_report.send()


def poll_temperature(temp_sensor_device, poll_interval, report_file):
  def _record_data(data):
    temp, humidity = parse_data(data)
    if report_file:
      with open(report_file, 'a') as f:
        f.write('%d,%f,%f\n' % (int(time.time()), temp, humidity))
    else:
      print 'temp: %.2f, humidity: %.2f' % (temp, humidity)

  # input report: data from device to app
  # output report: data from app to device
  # feature report: data that can be read or written
  out_report = None
  for report in temp_sensor_device.find_output_reports():
    if DEVICE_IN_OUT_USAGE in report:
      out_report = report
      break

  if not out_report:
    print 'Unable to find output report for usb device.'
    return 1

  print 'Initializing device...'
  initialize_device(out_report)
  temp_sensor_device.set_raw_data_handler(_record_data)
  print 'Intialized! Polling for temperature...'
  while True:
    get_temperature(out_report)
    time.sleep(poll_interval)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--poll-interval', type=int, default=60,
      help='How frequently to poll temperature.')
  parser.add_argument(
      '--report-file', type=str,
      help='Optional path to file to record temperature to.')
  parser.add_argument(
      '--clear-file', action='store_true',
      help='If set, clears report file before recording.')
  args = parser.parse_args()

  if args.clear_file and args.report_file and os.path.exists(args.report_file):
    os.remove(args.report_file)

  temp_sensor_device = find_usb_temp_sensor()
  if not temp_sensor_device:
    print 'Unable to find usb device.'
    return 1

  try:
    temp_sensor_device.open()
    poll_temperature(temp_sensor_device, args.poll_interval, args.report_file)
  finally:
    temp_sensor_device.close()


if __name__ == '__main__':
  sys.exit(main())