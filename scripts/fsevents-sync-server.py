import asyncio
import json
import logging
from pathlib import Path


def touch(path):
    path.touch()
    if path.is_file():
        with open(path, 'a'):
            pass
    return path


class FSEvent:
    def __init__(self, logger=None):
        self.logger = logger or logging.root
        self.tempdir = Path("/mnt/data/tmp")

    def move(self, item, src, dst):
        if item == 'file':
            try:
                self.logger.debug('Try to touch {0}'.format(dst))
                touch(dst)
                self.logger.debug(
                    'Try to touch {0} then delete it'.format(src))
                touch(src).unlink()
                self.logger.info(
                    'Move {0} "{1}" to "{2}"'.format(item, src, dst))
            except Exception as e:
                self.logger.error(
                    'Can\'n generate event: move {0} "{1}" to "{2}"'.format(item, src, dst))
                self.logger.error('{0}'.format(e))

        elif item == 'dir':
            try:
                tmp = dst.with_suffix('.__tmp__')
                self.logger.debug(
                    'Try to rename {0} to {1} and vice versa'.format(dst, tmp))
                dst.rename(tmp).rename(dst)

                self.logger.debug(
                    'Try to make dir {0} then remove it'.format(src))
                src.mkdir().rmdir()

                self.logger.info(
                    'Move {0} "{1}" to "{2}"'.format(item, src, dst))

            except Exception as e:
                self.logger.error(
                    'Can\'n generate event: move {0} "{1}" to "{2}"'.format(item, src, dst))
                self.logger.error('{0}'.format(e))

    def create(self, item, src):
        if item == 'file':
            self.logger.debug('Try to touch {0}'.format(src))
            touch(src)

            self.logger.info(
                'Create {0} "{1}"'.format(item, src))

        elif item == 'dir':
            try:
                dst = src.with_suffix('.__tmp__')
                self.logger.debug(
                    'Try to rename {0} to {1} and vice versa'.format(src, dst))
                src.rename(dst).rename(src)

                self.logger.info(
                    'Create {0} "{1}"'.format(item, src))
            except Exception as e:
                self.logger.error(
                    'Can\'n generate event: create {0} "{1}"'.format(item, src))
                self.logger.error('{0}'.format(e))

    def delete(self, item, src):
        if item == 'file':
            try:
                self.logger.debug(
                    'Try to touch {0} then remove it'.format(src))
                touch(src).unlink()
                self.logger.info(
                    'Delete {0} "{1}"'.format(item, src))
            except Exception as e:
                self.logger.error(
                    'Can\'n generate event: delete {0} "{1}"'.format(item, src))
                self.logger.error('{0}'.format(e))
        elif item == 'dir':
            try:
                self.logger.debug(
                    'Try to make dir {0} then remove it'.format(src))
                src.mkdir().rmdir()
                self.logger.info(
                    'Delete {0} "{1}"'.format(item, src))
            except Exception as e:
                self.logger.error(
                    'Can\'n generate event: delete {0} "{1}"'.format(item, src))
                self.logger.error('{0}'.format(e))

    def modify(self, item, src):
        if item != 'file':
            return
        self.logger.debug('Try to touch {0}'.format(src))
        src.touch()
        self.logger.info('Modify {0} "{1}"'.format(item, src))

    def close(self, item, src):
        self.logger.debug('Try to touch {0}'.format(src))
        touch(src)
        self.logger.info('Close {0} "{1}"'.format(item, src))

    def generate(self, data):
        event = data['event']
        item = data['item']
        src = Path(data['src'])

        if event == 'move':
            self.move(item, src, Path(data['dst']))
        elif event == 'create':
            self.create(item, src)
        elif event == 'delete':
            self.delete(item, src)
        elif event == 'close':
            self.close(item, src)
        elif event == 'modify':
            self.modify(item, src)


class ServerProtocol(asyncio.Protocol):
    def __init__(self, fsevent, logger=None):
        self.fsevent = fsevent
        self.logger = logger or logging.root

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        self.logger.debug('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        message = json.loads(data.decode())
        self.logger.debug('Data received: {!r}'.format(message))

        self.fsevent.generate(message)

        # self.logger.debug('Send message: {!r}'.format(message))
        # self.transport.write(data)

        self.logger.debug('Close the client socket')
        self.transport.close()


async def serve(fsevent, host, port):
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()

    server = await loop.create_server(
        lambda: ServerProtocol(fsevent),
        host, port)

    async with server:
        await server.serve_forever()


def main():
    conf_template = """
    {
        "log_level": "INFO",
        "host": "127.0.0.1",
        "port": 8888
    }

    """
    conf_path = Path.home().joinpath(".fsevents-sync-server.json")
    log_level = 'DEBUG'
    host = "127.0.0.1"
    port = 8888

    logging.basicConfig(
        level=logging.INFO, format='%(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if not conf_path.is_file():
        conf_path = Path(__file__).parent.joinpath(
            ".fsevents-sync-server.json")
    if not conf_path.is_file():
        msg = "Config '{0}' is not exists. Config template:\n" + conf_template
        msg = msg.format(conf_path)
        logging.error(msg)
        raise Exception(msg)

    with open(conf_path, 'r') as conf_file:
        try:
            conf_dict = json.load(conf_file)
            log_level = conf_dict.get("log_level", log_level)
            host = conf_dict.get("host", host)
            port = conf_dict.get("port", port)
        except:
            pass

    logging.root.setLevel(log_level)

    fsevent = FSEvent()
    asyncio.run(serve(fsevent, host, port))


if __name__ == "__main__":
    main()
