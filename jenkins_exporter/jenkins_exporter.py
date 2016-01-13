#!/usr/bin/python

import json
import re
import sys
import time
try:
  import urllib2
except:
  # Python 3
  import urllib.request as urllib2

from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY


class JenkinsCollector(object):
  def __init__(self, target):
    self._target = target.rstrip("/")

  def collect(self):
    # The build statuses we want to export about. 
    statuses = ["lastBuild", "lastCompletedBuild", "lastFailedBuild",
        "lastStableBuild", "lastSuccessfulBuild", "lastUnstableBuild",
        "lastUnsuccessfulBuild"]

    # The metrics we want to export.
    metrics = {}
    for s in statuses:
      snake_case = re.sub('([A-Z])', '_\\1', s).lower()
      metrics[s] = {
          'number':
              GaugeMetricFamily('jenkins_job_{0}'.format(snake_case),
                  'Jenkins build number for {0}'.format(s), labels=["jobname"]),
          'duration':
              GaugeMetricFamily('jenkins_job_{0}_duration_seconds'.format(snake_case),
                  'Jenkins build duration in seconds for {0}'.format(s), labels=["jobname"]),
          'timestamp':
              GaugeMetricFamily('jenkins_job_{0}_timestamp_seconds'.format(snake_case),
                  'Jenkins build timestamp in unixtime for {0}'.format(s), labels=["jobname"]),
          }

    # Request exactly the information we need from Jenkins
    result = json.loads(urllib2.urlopen(
        "{0}/api/json?tree=jobs[name,{1}]".format(
              self._target, ",".join([s + "[number,timestamp,duration]" for s in statuses])))
        .read().decode("utf-8"))

    for job in result['jobs']:
      name = job['name']
      for s in statuses:
        # If there's a null result, we want to export zeros.
        status = job[s] or {}
        metrics[s]['number'].add_metric([name], status.get('number', 0))
        metrics[s]['duration'].add_metric([name], status.get('duration', 0) / 1000.0)
        metrics[s]['timestamp'].add_metric([name], status.get('timestamp', 0) / 1000.0)

    for s in statuses:
      for m in metrics[s].values():
        yield m


if __name__ == "__main__":
  if len(sys.argv) < 2:
    sys.stderr.write("Usage: jenkins_exporter.py http://jenkins:8080\n")
    sys.exit(1)
  REGISTRY.register(JenkinsCollector(sys.argv[1]))
  start_http_server(9118)
  while True: time.sleep(1)
