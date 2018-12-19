#!/usr/bin/env python
# encoding: utf-8

import ffmpeg
import datetime
import time
from hashlib import md5
from json import dumps
from urllib import parse
from os import environ
import logging
from google.cloud import datastore
from flask import Flask, abort, request, jsonify, send_file, make_response

_allowed_params = ['start', 'end', 'height', 'width', 'fast'] # Allowed parameters in the URL request
SOURCE_BUCKET_NAME = 'LOL'
DESTINATION_BUCKET_NAME = 'LOL'
LOCAL_DESTINATION_PATH = './outputs'
FFMPEG_BINARY_PATH = './ffmpeg_static_builds/mac/ffmpeg'
GCP_PROJECT_ID = environ.get('GCP_PROJECT', 'personal-projects-225512')

if environ.get('GCP_PROJECT', None) is not None:
	FFMPEG_BINARY_PATH = './ffmpeg_static_builds/amd64/ffmpeg' # bundled as part of repo
	LOCAL_DESTINATION_PATH = '/tmp' # only /tmp is write-accessible on GCF

client = datastore.Client(GCP_PROJECT_ID) # Set up datastore
logging.getLogger().setLevel(logging.INFO)

def generate_hash(message):
	"Returns an MD5 hash."

	return md5(str(message).encode('utf-8')).hexdigest()

def read_in_datastore(md5_hash):
	"Check if this key/value exists in the datastore."

	key = client.key('processed_videos', md5_hash)
	task = client.get(key)

	if task:
		return task.get('location')
	else:
		return None

def insert_to_datastore(md5_hash, location):
	"Add this key/value to the datastore."

	key = client.key('processed_videos', md5_hash)
	task = datastore.Entity(key)

	task.update({
	    'location': location,
	    'created_at': datetime.datetime.utcnow()
	})

	client.put(task)

	return

def request_signed_url(filename):
	"Request and return a protected signed URL from the source bucket."

	url = '{}/{}'.format('http://storage.googleapis.com/test_videos_japan', parse.quote(filename))
	return url

def upload_to_storage_and_return_url(filename):
	"Upload the processed file to cloud storage and return the public URL."
	return filename

def round_to_nearest_even(number):
	"Round a number to the next highest even number if odd."
	number = int(number)

	if number % 2 == 1: # Odd heights are not allowed in codec spec
		number += 1

	return number

def ffmpeg_output_args(**params):
	"Generate ffmpeg output arguments from parameters."

	kwargs = dict()
	kwargs['movflags'] = '+faststart' # moov atom in front
	kwargs['hide_banner'] = None # hide ffmpeg banner from logs
	kwargs['nostdin'] = None # disable interactive mode
	kwargs['loglevel'] = 'debug' # more detailed logs from ffmpeg

	if params['operation'] == 'thumbnail':
		kwargs['vframes'] = '1'

	if 'height' in params:
		# Set fixed heigh & scale width to closest even number
		kwargs['vf'] = "scale=-2:'min({},ih)'".format(round_to_nearest_even(params['height']))

	if 'width' in params:
		kwargs['vf'] = "scale='min({},iw)':-2".format(round_to_nearest_even(params['width']))

	if 'fast' in params and ('height' in params or 'width' in params):
		abort(400)

	if 'fast' in params:
		kwargs['c'] = 'copy'

	return kwargs

def ffmpeg_input_args(**params):
	"Generate input output arguments from parameters."

	kwargs = dict()
	kwargs['multiple_requests'] = '1' # Reuse tcp connections in pseudostream

	if params['operation'] == 'thumbnail' and 'start' in params and '%' in params['start']:
		## FFprobe (requires another complete moov atom handshake, slow)
		probe = ffmpeg.probe(request_signed_url(params['source_file']))
		video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
		params['start'] = (float(params['start'].strip('%')) / 100.1) * float(video_stream['duration'])
		params.pop('end', None)

	if 'start' in params:
		kwargs['ss'] = float(params['start'])

	if 'end' in params:
		kwargs['t'] = float(params['end']) - float(params['start'])

	return kwargs


def trim(request):
	if request.path == '/favicon.ico': abort(404) # Ignore browser requests for favicon

	request.path = request.path.strip('/').split('/')
	_source_params = request.path[1]
	_source_file = request.path[2]
	_time = int(time.time())
	_params = dict()
	_params['operation'] = request.path[0]
	_params['source_file'] = request.path[2]

	# Extract parameters from URL field
	for param in _source_params.split(','):
		try:
			_split = param.split(':')
			_key = _split[0]
			_value = _split[1] if len(_split) > 1 else None

			if _key in _allowed_params:
				_params[_key] = _value
			else: abort(400)
		except: abort(400)


	## Generate hash
	_hash = generate_hash("{}:{}".format(dumps(_params, sort_keys=True), _source_file))

	## Check for existing entry in datastore
	_entity = read_in_datastore(_hash)
	if _entity:
		# todo: 301/302/307 redirect
		print('Already found.')

	## Create args for ffmpeg.input
	_input_kwargs = ffmpeg_input_args(**_params)
	_output_kwargs = ffmpeg_output_args(**_params)

	job = ffmpeg.input(request_signed_url(_source_file), **_input_kwargs)
	job = ffmpeg.output(job, '{}/{}_{}.{}'.format(LOCAL_DESTINATION_PATH, _time, _hash, 'mp4' if _params['operation'] == 'trim' else 'jpg'), **_output_kwargs)


	try:
		out, err = ffmpeg.run(job, cmd=FFMPEG_BINARY_PATH, capture_stderr=True, capture_stdout=True)

		# read source metadata from out?
		#logging.info(out.decode('utf-8').replace('\n', ' '))
		#logging.error(err.decode('utf-8').replace('\n', ' '))

	except ffmpeg.Error as e:
		abort(500)
		logging.error(e.stderr.decode().replace('\n', ' '))
		logging.error(e.stderr)
		logging.error(e)




	_info = {
		'params': _source_params,
		'js_params': _params,
		'ffmpeg_input_args': _input_kwargs,
		'ffmpeg_output_args': _output_kwargs,
		'ffmpeg_command': " ".join(ffmpeg.compile(job)),
		'source_file': _source_file,
		'hash': _hash
	}

	logging.info(_info)

	# todo: wrap in try except
	response = make_response(send_file('{}/{}_{}.{}'.format(LOCAL_DESTINATION_PATH, _time, _hash, 'mp4' if _params['operation'] == 'trim' else 'jpg')))
	response.headers['X-Query-Hash'] = _hash

	insert_to_datastore(_hash, '{}/{}_{}.{}'.format(LOCAL_DESTINATION_PATH, _time, _hash, 'mp4' if _params['operation'] == 'trim' else 'jpg'))

	return response

	#return jsonify({
	#	'params': _source_params,
	#	'js_params': _params,
	#	'ffmpeg_input_args': _input_kwargs,
	#'ffmpeg_output_args': kwargs,
	#	'ffmpeg_command': " ".join(ffmpeg.compile(job)),
	#	'source_file': _source_file,
	#	'hash': _hash,
	#	#'video_stream': video_stream
	#})



# https://storage.googleapis.com/test_videos_mp4/%5B60fps%5D%205%20minutes%20timer%20with%20milliseconds-CW7-nFObkpw.mp4
# https://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4

# ffmpeg -y -ss 00:00:05.000 -i "https://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4" -t 00:00:05.000 -c:a copy -c:v copy output.mp4
# ffmpeg -y -ss 00:00:05.000 -i "http://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4" -t 00:00:05.000 -c:a copy -c:v copy output.mp4

# Return 302 directly if file hash already exists in storage
# Return 302 after finishing uploading and processing (to avoid Lambda and GCF response size limits)
# Combine clips
# Watermarking
# Signed URL generation for private source bucket (and for output as well)
# moov_atom
# configuration file format
# GCP Functions / AWS Lambda
# Include ffmpeg static build?
# -c copy if 1) mp4 2) only trim and 3) acceptable to have end freeze

# Things to test
#	moov-atom at the back source file
#	MOVs, AVIs, WAVs, FLVs
#	Benchmark processing times on various serverless configs
#	Benchmark ffmpeg invocation, download, transcode, upload times
#	Benchmark serverless vs container pricing per clip
#	Benchmark cross region load times (GCP Japan to GCS Taiwan)












if __name__=="__main__":
	app = Flask(__name__)

	@app.route('/', defaults={'path': ''})
	@app.route('/<path:path>')
	def index(path):
	    return trim(request)

	app.run('0.0.0.0', 5000, debug=True)







