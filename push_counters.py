import json
import os
import requests
import time
import socket
import sys

push_gateway = 'http://localhost:9091'
job_name = 'pushgateway'
instance_name = socket.gethostname()
iteration_interval = 1  # seconds

# Computed constants.
url = '{}/metrics/job/{}/instance/{}'.format(push_gateway, job_name, instance_name)
response_file = './counters.json'
rippled = 'rippled --conf rippled.cfg'

cmd = '{} server_info counters > {}'.format(rippled, response_file)
# Each of these paths leads to a dictionary from task type to object of
# counters (e.g. `started`, `finished`, `duration_us`).
# The value of each counter is a non-negative integer represented by a string
# (because its representation may be wider than 32 bits).
paths = [
    ['result', 'info', 'counters', 'rpc'],
    ['result', 'info', 'counters', 'job_queue'],
]

def get_counters():
    os.system(cmd)
    with open(response_file, 'r') as file:
        try:
            response = json.load(file)
        except Exception as cause:
            print('cannot parse JSON: {}'.format(cause), file=sys.stderr)
            return

    if not response or 'error' in response:
        print('error: {}'.format(response['error']), file=sys.stderr)
        return

    data = ''
    for path in paths:
        section = response
        for step in path:
            section = section[step]
        section_key = '_'.join(path)

        metric_prefix = path[-1]

        data += ''.join(
            '# TYPE {}_{} counter\n'.format(metric_prefix, counter_name)
            for counter_name in next(iter(section.values())).keys()
        )

        for task, counters in section.items():
            for counter, value in counters.items():
                data += '{}_{}{{task="{}"}} {}\n'.format(metric_prefix, counter, task, value)

    requests.post(url=url, data=data)
    print('pushed:\n{}'.format(data))


if __name__ == '__main__':
    while True:
        get_counters()
        time.sleep(iteration_interval)
