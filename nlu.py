import argparse
import asyncio
import datetime
import itertools
import json
import pprint
import sys

import aiohttp
import opuslib
import opuslib.api.constants
import pyaudio

from aiohttp.client_exceptions import WSServerHandshakeError
from yarl import URL


AUDIO_FORMAT = pyaudio.paInt16
FRAME_SIZE = 320
SAMPLE_SIZE = pyaudio.get_sample_size(AUDIO_FORMAT)  # in bytes

DEVICE_ID = 'MIX_WS_PYTHON_SAMPLE_APP'


class NCSTransaction:

    BEGIN_MESSAGE = 'query_begin'
    END_MESSAGE = 'query_end'
    ID_PROPERTY = 'transaction_id'

    def __init__(self, id_, session):
        self.id_ = id_
        self.session = session
        self.client = self.session.client

    @asyncio.coroutine
    def begin(self, **kwargs):
        """Send a 'query_begin' augmenting the payload with any additional kwargs,
        e.g. 'command', 'context_tag', 'language', etc.
        """
        payload = {
            'message': self.BEGIN_MESSAGE,
        }
        payload.update(kwargs)
        yield from self._send_json(payload)

    @asyncio.coroutine
    def send_parameter(self, name, type_, value):
        """Send a 'query_parameter' message.

        :param name: Corresponds to `parameter_name`
        :param type_: Corresponds to `parameter_type`
        :param value: The parameter itself. Should be a {key: value} dictionary
        """
        payload = {
            'message': 'query_parameter',
            'parameter_name': name,
            'parameter_type': type_,
        }
        payload.update(value)
        yield from self._send_json(payload)

    @asyncio.coroutine
    def end(self, wait=True, timeout=None):
        """Send a 'query_end' message and wait to receive an acknowledgement or
        disconnection message.

        :param wait: (bool) Wait for server-side confirmation before returning.
        :param timeout: (in seconds) How long you are willing to wait without
        receiving a payload.
        """
        yield from self._send_json({'message': self.END_MESSAGE})
        if wait:
            yield from self.wait_for_query_end(timeout)

    @asyncio.coroutine
    def _send_json(self, message):
        """Send a JSON payload using the original WS client.

        Injects the transaction ID in the payload, modifying the dictionary,
        so the transaction_id can be logged properly.
        """
        message.update({self.ID_PROPERTY: self.id_})
        return(yield from self.client.send_json(message))

    @asyncio.coroutine
    def wait_for_query_end(self, timeout=None):
        while True:
            message = yield from self.client.receive_json(timeout=timeout)
            if message['message'] in ('query_end', 'disconnect'):
                return message


class NCSAudioTransfer(NCSTransaction):
    """Transaction used to stream audio bytes.

    Behaves similarly to other NCS transactions, but with different parameter
    names and some minor behavior differences.
    """

    BEGIN_MESSAGE = 'audio'
    END_MESSAGE = 'audio_end'
    ID_PROPERTY = 'audio_id'

    @property
    def info(self):
        """Payload should be sent in the AUDIO_INFO.

        Expected format is:

            {"audio_id": 123}
        """
        return {self.ID_PROPERTY: self.id_}

    @asyncio.coroutine
    def send_bytes(self, bytes_, *args, **kwargs):
        yield from self.client.send_bytes(bytes_, *args, **kwargs)


class NCSSession:

    def __init__(self, client):
        self.id_ = None  # Assigned upon initial request
        self.client = client
        self._transaction_id_generator = itertools.count(start=1, step=1)
        self._audio_id_generator = itertools.count(start=1, step=1)

    @asyncio.coroutine
    def initiate(self, user_id, device_id, **kwargs):
        payload = {
            'message': 'connect',
            'device_id': device_id,
            'user_id': user_id,
        }
        payload.update(kwargs)
        yield from self.client.send_json(payload)
        message = yield from self.client.receive_json()
        if message.get('message') != 'connected':
            raise RuntimeError('Invalid session connection message')

        self.id_ = message['session_id']

    @asyncio.coroutine
    def begin_transaction(self, *args, **kwargs):
        transaction_id = self.get_new_transaction_id()
        transaction = NCSTransaction(transaction_id, session=self)
        yield from transaction.begin(*args, **kwargs)
        return transaction

    def get_new_transaction_id(self):
        return next(self._transaction_id_generator)

    def get_new_audio_id(self):
        return next(self._audio_id_generator)


class NCSWebSocketClient:
    """Client for Nuance Cloud Services (NCS) WebSocket API

    For more info on the protocol:
    https://developer.nuance.com/mix/documentation/websockets/

    This client only supports one session + transaction at a time.
    """

    def __init__(self, url, app_id, app_key):
        self.url = URL(url)
        self.app_id = app_id
        self.app_key = app_key
        self._http_session = None
        self._ws_client = None

    @asyncio.coroutine
    def connect(self):
        self._http_session = aiohttp.ClientSession()
        url = self.url.update_query(app_id=self.app_id, app_key=self.app_key,
                                    algorithm='key')
        try:
            self._ws_client = yield from self._http_session.ws_connect(url)
        except WSServerHandshakeError as ws_error:
            info = '%s %s\n' % (ws_error.code, ws_error.message)
            for (key, value) in ws_error.headers.items():
                info += '%s: %s\n' % (key, value)
            if ws_error.code == 401:
                raise RuntimeError('Authorization failure:\n%s' % info) from ws_error
            elif 500 <= ws_error.code < 600:
                raise RuntimeError('Server error:\n%s' %  info) from ws_error
            else:
                raise ws_error

    @asyncio.coroutine
    def init_session(self, user_id, device_id, **kwargs):
        session = NCSSession(client=self)
        yield from session.initiate(user_id, device_id, **kwargs)
        return session

    @asyncio.coroutine
    def receive_json(self, *args, **kwargs):
        message = yield from self._ws_client.receive_json(*args, **kwargs)
        self.log(message)
        return message

    @asyncio.coroutine
    def send_json(self, message, *args, **kwargs):
        self.log(message, sending=True)
        yield from self._ws_client.send_json(message, *args, **kwargs)

    @asyncio.coroutine
    def send_bytes(self, bytes_, *args, **kwargs):
        yield from self._ws_client.send_bytes(bytes_, *args, **kwargs)

    @asyncio.coroutine
    def close(self):
        if self._ws_client is not None and not self._ws_client.closed:
            yield from self._ws_client.close()
        if self._http_session is not None and not self._http_session.closed:
            self._http_session.close()

    @staticmethod
    def log(message, sending=False):
        print('>>>>' if sending else '<<<<')
        print(datetime.datetime.now())
        pprint.pprint(message)
        print()


@asyncio.coroutine
def understand_text(ncs_client, user_id, context_tag, text_to_understand, language='eng-USA'):
    request_info = {
        'dictionary': {
            'application_data': {
                'text_input': text_to_understand,
            },
        },
    }
    try:
        yield from ncs_client.connect()
        session = yield from ncs_client.init_session(user_id, DEVICE_ID)
        transaction = yield from session.begin_transaction(command='NDSP_APP_CMD',
                                                           language=language,
                                                           context_tag=context_tag)
        yield from transaction.send_parameter(name='REQUEST_INFO', type_='dictionary',
                                              value=request_info)
        yield from transaction.end()
    finally:
        yield from ncs_client.close()


@asyncio.coroutine
def understand_audio(ncs_client, loop, recorder, user_id, context_tag=None, language='eng-USA'):
    audio_type = "audio/opus;rate=%d" % recorder.rate

    # Useful terminology reference:
    # https://larsimmisch.github.io/pyalsaaudio/terminology.html
    bytes_per_frame = recorder.channels * SAMPLE_SIZE
    audio_packet_min_size = FRAME_SIZE * bytes_per_frame
    audio_packet_max_size = 4 * audio_packet_min_size

    try:
        yield from ncs_client.connect()
        session = yield from ncs_client.init_session(user_id, DEVICE_ID, codec=audio_type)
        transaction = yield from session.begin_transaction(command='NDSP_ASR_APP_CMD',
                                                           language=language,
                                                           context_tag=context_tag)

        audio_transfer = NCSAudioTransfer(id_=session.get_new_audio_id(), session=session)
        yield from transaction.send_parameter(name='AUDIO_INFO', type_='audio',
                                              value=audio_transfer.info)
        # We end the transaction here, but we will only have a 'query_end' response
        # back when the audio transfer and ASR/NLU are done.
        yield from transaction.end(wait=False)
        yield from audio_transfer.begin()

        key_event = asyncio.Event()

        def key_event_callback():
            sys.stdin.readline()
            key_event.set()
            recorder.stop()
            loop.remove_reader(sys.stdin)

        loop.add_reader(sys.stdin, key_event_callback)

        key_task = asyncio.ensure_future(key_event.wait())
        audio_task = asyncio.ensure_future(recorder.audio_queue.get())

        raw_audio = bytearray()
        mono_audio = bytearray()

        encoder = opuslib.Encoder(fs=recorder.rate, channels=1,
                                  application=opuslib.api.constants.APPLICATION_VOIP)

        recorder.start()
        print('Recording, press Enter to stop...')

        while not key_task.done():

            while len(raw_audio) > audio_packet_min_size:
                count = min(len(raw_audio), audio_packet_max_size)
                mono_audio += convert_to_mono(raw_audio, count, recorder.channels, SAMPLE_SIZE)
                raw_audio = raw_audio[count:]

            while len(mono_audio) > FRAME_SIZE * SAMPLE_SIZE:
                audio_to_encode = bytes(mono_audio[:FRAME_SIZE*SAMPLE_SIZE])
                audio_encoded = encoder.encode(audio_to_encode, FRAME_SIZE)
                yield from audio_transfer.send_bytes(audio_encoded)
                mono_audio = mono_audio[FRAME_SIZE*SAMPLE_SIZE:]

            yield from asyncio.wait((key_task, audio_task),
                                    return_when=asyncio.FIRST_COMPLETED,
                                    loop=loop)

            if audio_task.done():
                raw_audio += audio_task.result()
                audio_task = asyncio.ensure_future(recorder.audio_queue.get())

        audio_task.cancel()

        yield from audio_transfer.end(wait=False)
        yield from transaction.wait_for_query_end()
    finally:
        yield from ncs_client.close()


@asyncio.coroutine
def upload_concept_data_for_user(ncs_client, user_id, concept_id, concept_data):
    max_items_per_payload = 100
    command = 'NDSP_CONCEPT_UPLOAD_FULL_CMD'

    chunks = []

    for items_sublist in get_chunked_list(concept_data, chunk_size=max_items_per_payload):
        chunks.append({
            'type': 'sequence_chunk',
            'content_data': {
                'dictionary': {
                    'items': items_sublist,
                },
            },
        })

    if len(chunks) > 1:
        # Mark first and last chunk as such
        chunks[0]['type'] = 'sequence_start'
        chunks[-1]['type'] = 'sequence_end'
    else:
        chunks[0]['type'] = 'dictionary'

    try:
        yield from ncs_client.connect()
        session = yield from ncs_client.init_session(user_id, DEVICE_ID)
        transaction = yield from session.begin_transaction(command=command,
                                                           concept_id=concept_id)
        for chunk in chunks:
            yield from transaction.send_parameter(name='CONTENT_DATA',
                                                  type_=chunk['type'],
                                                  value=chunk['content_data'])
        yield from transaction.end()
    finally:
        yield from ncs_client.close()


@asyncio.coroutine
def wipe_concept_data_for_user(ncs_client, user_id):
    command = 'NDSP_DELETE_ALL_CONCEPTS_DATA_CMD'

    try:
        yield from ncs_client.connect()
        session = yield from ncs_client.init_session(user_id, DEVICE_ID)
        transaction = yield from session.begin_transaction(command=command)
        yield from transaction.end()
    finally:
        yield from ncs_client.close()


class Recorder:

    def __init__(self, device_index=None, rate=None, channels=None,
                 loop=None, auto_start=False):
        # Audio configuration
        self._audio = pyaudio.PyAudio()

        if device_index is None:
            device_index = self.pick_default_device_index()

        self._device_index = device_index

        if rate is None or channels is None:
            self.pick_default_parameters()
        else:
            self.rate = rate
            self.channels = channels

        self._stream = None

        # Event loop
        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop
        self.audio_queue = asyncio.Queue()
        self.auto_start = auto_start

    def start(self):
        self._stream.start_stream()

    def stop(self):
        self._stream.stop_stream()

    def __enter__(self):
        self._stream = self._audio.open(
            self.rate,
            self.channels,
            AUDIO_FORMAT,
            input=True,
            input_device_index=self._device_index,
            start=self.auto_start,
            stream_callback=self.callback)
        return self

    def __exit__(self, error_type, value, traceback):
        if self._stream is not None:
            if not self._stream.is_stopped():
                self._stream.stop_stream()
            self._stream.close()
        if self._audio is not None:
            self._audio.terminate()

    def callback(self, in_data, *_args):
        asyncio.run_coroutine_threadsafe(self.audio_queue.put(in_data), self._loop)
        return (None, pyaudio.paContinue)

    def pick_default_device_index(self):
        try:
            device_info = self._audio.get_default_input_device_info()
            return device_info['index']
        except IOError:
            raise RuntimeError('No Recording Devices Found')

    def pick_default_parameters(self):
        """ Pick compatible rates and channels in preferred order.

        16kHz is the preferred sampling rate, as it yields both good transfer
        speed and recognition results.

        Mono audio is also preferred, as stereo doubles the bandwidth,
        typically without any significant recognition improvement.
        """
        rates = [
            16000,
            24000,
            48000,
            12000,
            8000,
        ]
        channels = [1, 2]

        # Add device spefic information
        info = self._audio.get_device_info_by_index(self._device_index)
        rates.append(info['defaultSampleRate'])
        channels.append(info['maxInputChannels'])

        for (rate, channel) in itertools.product(rates, channels):
            if self._audio.is_format_supported(rate,
                                               input_device=self._device_index,
                                               input_channels=channel,
                                               input_format=pyaudio.paInt16):
                (self.rate, self.channels) = (rate, channel)
                break
        else:
            # If no (rate, channel) combination is found, raise an error
            error = "Couldn't find recording parameters for device %s" % self._device_index
            raise RuntimeError(error)


def get_chunked_list(list_, chunk_size):
    """Return sublists of `list_` with a max length of `chunk_size`"""
    for i in range(0, len(list_), chunk_size):
        yield list_[i:i + chunk_size]


def convert_to_mono(raw_audio, count, channels, sample_size):
    """Convert a subset of a raw audio buffer (up to `count` bytes)
    into single-channel (mono) audio.
    """
    mono_audio = bytearray()
    if channels == 1:
        mono_audio += raw_audio[:count]
    else:
        for i in range(0, count, channels * sample_size):
            mono_audio += raw_audio[i:i+sample_size]
    return mono_audio


def parse_args():
    parser = argparse.ArgumentParser(description='Mix.nlu sample application')

    # Check for credentials file
    parser.add_argument(
        '--config', '-c',
        dest='config',
        default='creds.json',
        help='JSON configuration file',
        type=argparse.FileType('r'),
    )
    parser.add_argument(
        '--user_id', '--user-id', '-u',
        dest='user_id',
        default='user1',
        help='User the transaction is being executed on behalf of',
    )

    # Add four subcommands: `audio`, `text` and `data_upload`, and `data_wipe`
    subparsers = parser.add_subparsers(dest='command', title='commands')
    subparsers.required = True

    # Audio NLU
    subparsers.add_parser(
        'audio',
        help='Execute NLU transaction from audio acquired from your microphone',
    )

    # Text NLU
    parser_text = subparsers.add_parser(
        'text',
        help='Execute NLU transaction using text',
    )
    parser_text.add_argument(
        'sentence',
        help='Sentence to understand (enclose in quotes)',
    )

    # Data Upload
    parser_data_upload = subparsers.add_parser(
        'data_upload',
        help='Upload user data for a dynamic list concept',
    )
    parser_data_upload.add_argument(
        'concept_id',
        help='Dynamic List concept to associate data with',
    )
    parser_data_upload.add_argument(
        nargs='?',
        dest='concept_data_file',
        default='dynamic_list.sample.json',
        help='Data to use for user specific ASR and NLU customization',
        type=argparse.FileType('r'),
    )

    # Data Wipe
    subparsers.add_parser(
        'data_wipe',
        help='Wipe user data for all dynamic list concepts',
    )

    return parser.parse_args()


def main():
    """
    For CLI usage:

        python nlu.py --help

    For audio + NLU:

        python nlu.py -u <user_id> audio
        # 1. Start recording when prompted;
        # 2. Press <enter> when done.

    For text + NLU:

        python nlu.py -u <user_id> text  'This is the sentence you want to test'

    For per-user data upload:

        python nlu.py -u <user_id> data_upload <concept_id> <concept_data_file.json>
        python nlu.py -u <user_id> data_wipe

    """
    args = parse_args()

    # Read the configuration file
    credentials = json.load(args.config, encoding='utf-8')

    loop = asyncio.get_event_loop()

    app_key = credentials['app_key']
    url = credentials['url']
    app_id = credentials['app_id']
    user_id = args.user_id

    ncs_client = NCSWebSocketClient(url, app_id, app_key)

    if args.command == 'text':
        loop.run_until_complete(understand_text(
            ncs_client,
            user_id,
            context_tag=credentials['context_tag'],
            text_to_understand=args.sentence,
            language=credentials['language']))

    elif args.command == 'audio':
        with Recorder(loop=loop) as recorder:
            loop.run_until_complete(understand_audio(
                ncs_client,
                loop,
                recorder,
                user_id,
                context_tag=credentials['context_tag'],
                language=credentials['language']))

    elif args.command == 'data_upload':
        concept_data = json.load(args.concept_data_file, encoding='utf-8')
        if not isinstance(concept_data, list):
            raise ValueError("Concept data must be a list of dicts with 'literal' and 'value'.")
        loop.run_until_complete(upload_concept_data_for_user(
            ncs_client,
            user_id,
            concept_id=args.concept_id,
            concept_data=concept_data))

    elif args.command == 'data_wipe':
        loop.run_until_complete(wipe_concept_data_for_user(
            ncs_client,
            user_id))


if __name__ == '__main__':
    main()
