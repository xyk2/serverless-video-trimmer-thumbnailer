#!/usr/bin/env python
# encoding: utf-8

import ffmpeg
import time
import hashlib
import json
import urllib
import os
import sys
import logging
from google.cloud import datastore
from flask import Flask, abort, request, jsonify, send_file, make_response

logging.getLogger().setLevel(logging.INFO)

_allowed_params = ['start', 'end', 'height', 'width', 'fast'] # Allowed parameters in the URL request
SOURCE_BUCKET_NAME = 'LOL'
DESTINATION_BUCKET_NAME = 'LOL'
LOCAL_DESTINATION_PATH = './outputs'
FFMPEG_BINARY_PATH = './ffmpeg_static_builds/mac/ffmpeg'

if os.environ.get('GCP_PROJECT', None) is not None:
	FFMPEG_BINARY_PATH = './ffmpeg_static_builds/amd64/ffmpeg'
	LOCAL_DESTINATION_PATH = '/tmp'


def generate_hash(message):
	"Returns an MD5 hash given a message."
	hashmd5 = hashlib.md5(str(message).encode('utf-8')).hexdigest()
	return hashmd5

def request_signed_url(filename):
	"Request and return a protected signed URL from the source bucket."

	url = '{}/{}'.format('http://storage.googleapis.com/test_videos_mp4', urllib.parse.quote(filename))
	return url

def check_in_datastore(md5_hash):
	"Check if this unique query is repeated in the datastore."
	return md5_hash

def insert_to_datastore(md5_hash, location):
	"Add this unique query to the datastore."
	return (md5_hash, location)

def upload_to_storage_and_return_url(filename):
	"Upload the processed file to cloud storage and return the URL."
	return filename

def round_to_nearest_even(number):
	"Round a number to the next highest even number if odd."
	number = int(number)

	if number % 2 == 1: # Odd heights are not allowed in codec spec
		number += 1

	return number

def ffmpeg_output_args(**params):
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
	kwargs = dict()
	kwargs['multiple_requests'] = '1' # Reuse tcp connections

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

	## Create args for ffmpeg.input
	_input_kwargs = ffmpeg_input_args(**_params)

	## Generate hash
	_hash = generate_hash("{}:{}".format(json.dumps(_params, sort_keys=True), _source_file))

	job = ffmpeg.input(request_signed_url(_source_file), **_input_kwargs)
	#job = ffmpeg.filter(job, 'fps', fps=25, round='up')

	_output_kwargs = ffmpeg_output_args(**_params)

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

	response = make_response(send_file('{}/{}_{}.{}'.format(LOCAL_DESTINATION_PATH, _time, _hash, 'mp4' if _params['operation'] == 'trim' else 'jpg')))
	response.headers['X-Query-Hash'] = _hash
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







