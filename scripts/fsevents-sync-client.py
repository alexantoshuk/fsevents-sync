#!/usr/bin/python3
# -*- coding: utf-8 -*-

import watchdog
import logging
from watchdog.observers import Observer
from pathlib import Path
import asyncio
import json
import os
import time
from threading import Timer


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class ClientProtocol(asyncio.Protocol):
    def __init__(self, message, on_con_lost, logger=None):
        self.message = message
        self.on_con_lost = on_con_lost
        self.logger = logger or logging.root

    def connection_made(self, transport):
        transport.write(self.message.encode())
        self.logger.debug('Data sent: {!r}'.format(self.message))

    def data_received(self, data):
        self.logger.debug('Data received: {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        self.logger.debug('The server closed the connection')
        self.on_con_lost.set_result(True)


class Client:
    def __init__(self, host, port, logger=None):
        self.logger = logger or logging.root
        self.host = host
        self.port = port

    def send(self, message):
        async def _send():
            # Get a reference to the event loop as we plan to use
            # low-level APIs.
            loop = asyncio.get_running_loop()

            on_con_lost = loop.create_future()
            # message = dict(path="Hello World!", item="FILE", mode="CREATE")
            json_msg = json.dumps(message)
            transport, protocol = await loop.create_connection(lambda: ClientProtocol(json_msg, on_con_lost, self.logger), self.host, self.port)

            # Wait until the protocol signals that the connection
            # is lost and close the transport.
            try:
                await on_con_lost
            finally:
                transport.close()

        asyncio.run(_send())


def ignore(name):
    basename = os.path.basename(name)
    return basename.startswith('.#') or basename.endswith('.__tmp__')


class EventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, watch_dir, client, logger=None):
        super().__init__()
        self.client = client
        self.watch_dir = watch_dir
        self.logger = logger or logging.root
        self.ts = time.time()
        self.movedir = None
        self.timer = RepeatedTimer(1.0, EventHandler._timer_callback, self)

    def _timer_callback(self):
        d = time.time() - self.ts
        if d < 0.5:
            return
        self.end_dirmove()

    def begin_dirmove(self, event):
        if event.is_directory and not self.movedir:
            self.movedir = event
            self.timer.start()
            return True

        if self.movedir and event.src_path.startswith(self.movedir.src_path) and event.dest_path.startswith(self.movedir.dest_path):
            return True

    def end_dirmove(self):
        if not self.movedir:
            return

        self.timer.stop()

        event = self.movedir

        self.logger.info('Move dir %s to "%s"',
                         event.src_path, event.dest_path)

        msg = dict(event='move', item='dir',
                   src=event.src_path, dst=event.dest_path)
        self.movedir = None
        self.client.send(msg)
        return True

    def on_any_event(self, event):
        self.ts = time.time()

    def on_moved(self, event):
        if self.begin_dirmove(event):
            return

        self.end_dirmove()

        self.logger.info('')

        what = 'dir' if event.is_directory else 'file'

        self.logger.info('Move %s %s to "%s"', what, event.src_path,
                         event.dest_path)

        msg = dict(event='move', item=what,
                   src=event.src_path, dst=event.dest_path)
        self.client.send(msg)

    def on_created(self, event):
        self.end_dirmove()
        if ignore(event.src_path):
            return

        what = 'dir' if event.is_directory else 'file'

        self.logger.info('Create %s "%s"', what, event.src_path)

        msg = dict(event='create', item=what, src=event.src_path)
        self.client.send(msg)

    def on_deleted(self, event):
        self.end_dirmove()
        if ignore(event.src_path):
            return

        what = 'dir' if event.is_directory else 'file'
        self.logger.info('Delete %s "%s"', what, event.src_path)

        msg = dict(event='delete', item=what, src=event.src_path)
        self.client.send(msg)

    def on_closed(self, event):
        self.end_dirmove()
        if ignore(event.src_path):
            return

        what = 'dir' if event.is_directory else 'file'

        self.logger.info('Close %s "%s"', what, event.src_path)

        msg = dict(event='close', item=what, src=event.src_path)
        self.client.send(msg)

    def on_modified(self, event):
        if event.is_directory:
            return

        self.end_dirmove()
        if ignore(event.src_path):
            return

        what = 'dir' if event.is_directory else 'file'

        self.logger.info('Modify %s "%s"', what, event.src_path)

        msg = dict(event='modify', item=what, src=event.src_path)
        self.client.send(msg)


def main():
    conf_template = """
    {
        "watch_dir": "/path_to/watch_dir_name",        
        "log_level": "INFO",
        "host": "127.0.0.1",
        "port": 8888
    }

    """

    conf_path = Path.home().joinpath(".fsevents-sync-client.json")
    watch_dir = None
    log_level = 'DEBUG'
    host = "127.0.0.1"
    port = 8888

    logging.basicConfig(
        level=logging.INFO, format='%(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if not conf_path.is_file():
        conf_path = Path(__file__).parent.joinpath(
            ".fsevents-sync-client.json")

    if not conf_path.is_file():
        msg = "Config '{0}' is not exists. Config template:\n" + conf_template
        msg = msg.format(conf_path)
        logging.error(msg)
        raise Exception(msg)

    with open(conf_path, 'r') as conf_file:
        try:
            conf_dict = json.load(conf_file)
            watch_dir = Path(conf_dict.get('watch_dir', watch_dir))
            log_level = conf_dict.get("log_level", log_level)
            host = conf_dict.get("host", host)
            port = conf_dict.get("port", port)
        except:
            pass

    logging.root.setLevel(log_level)

    if (not watch_dir):
        msg = "Config '{0}' has invalid data. Config template:\n" + \
            conf_template
        msg = msg.format(conf_path)
        logging.error(msg)
        raise Exception(msg)

    if not watch_dir.is_dir():
        msg = "Local dir '%s' is not exists" % watch_dir
        logging.error(msg)
        raise Exception(msg)

    client = Client(host, port)
    event_handler = EventHandler(watch_dir, client)

    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
