import paho.mqtt.client as mqtt
from channels import ChannelMgr
from pprint import pprint
import time
from json import dumps, loads
from conf import load_config
import requests
import sys

def send_to_elk(client, userdata, msg):
    mid = msg.mid
    payload = loads(msg.payload.decode("utf-8"))
    timestamp = msg.timestamp
    url = msg.topic
    nodule_id = url.split('/')[-2]
    payload['nodule_id'] = nodule_id
    payload['ts'] = timestamp
    # r = requests.post("http://10.0.88.108:9200/logs/test", data=dumps(payload))
    # sys.stdout.write(r.text)
    sys.stdout.write("ELK:\t{}, {}".format(url, payload))
    return

def send_to_db(client, userdata, msg):
    mid = msg.mid
    payload = loads(msg.payload.decode("utf-8"))
    timestamp = msg.timestamp
    url = msg.topic
    # sys.stdout.write("DB:\t", url, payload)
    topic, node_name = url.split('/')
    # sys.stdout.write(node_name, topic)
    if topic == 'presence':
        sys.stdout.write("{}.presence = {}".format(node_name, payload.get('presence')))
    elif topic == 'report':
        sys.stdout.write("{} = {}".format(node_name, payload))
    return


def send_to_file(client, userdata, msg):
    mid = msg.mid
    payload = loads(msg.payload.decode("utf-8"))
    timestamp = msg.timestamp
    url = msg.topic
    time = payload['timestamp'].split('.')[0]
    values = loads(payload['value'].replace("'", '"'))
    # temp = values['temp']
    log_line = '{}, {}\n'.format(time, values)
    with open('logfile.txt', 'a') as logfile:
        logfile.write(log_line)
    return

def add_timestamp(payload):
    ts = str(datetime.now())
    payload['rec_ts'] = ts
    return payload

router = {
    'elk': send_to_elk,
    'db': send_to_db,
    'file': send_to_file,
}

routes = {
    'presence': ['elk', 'db'],
    'sensors': ['elk'],#, 'file'],
    'logs': ['elk'],
    'errors': ['elk'],
    'report': ['elk', 'db'],
}

def msg_cb(client, userdata, msg):
    topic = msg.topic.split("/")[0]
    for route in routes.get(topic):
        # try:
        r_func = router.get(route)
        r_func(client, userdata, msg)
        # except:
        #     sys.stdout.write("Topic {} not recognized".format(topic))
        #     pass

config = load_config()
name = 'bridge'
channel = ChannelMgr(name)
elk_port = 9300
elk_host = 'dmip'
client = mqtt.Client(client_id=name)

def presence_msg(connected=True):
    return dumps({'presence': 'Connected' if connected else 'Disconnected', 'node': name})

client.will_set(channel.presence(), presence_msg(False), 0, False)
client.connect(config['MQTT_URL'], config['MQTT_PORT'], config['MQTT_KEEPALIVE'])

for topic in config['topics']:
    channel_name = topic + '/#'
    client.message_callback_add(channel_name, msg_cb)
    client.subscribe(channel_name)  # Add, modify, remove, trigger, etc

client.loop_start()
client.publish(channel.presence(), presence_msg(True))

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()
        break
exit(0)
