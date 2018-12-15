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

from flask import Flask, abort, request, jsonify, send_file

_allowed_params = ['s', 'f', 'q', 'w'] # Allowed parameters in the URL request
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

	url = '{}/{}'.format('https://storage.googleapis.com/test_videos_mp4', urllib.parse.quote(filename))
	return url

def check_in_memorystore(md5_hash):
	"Check if this query is repeated in the memorystore."
	return md5_hash

def insert_to_memorystore(md5_hash, location):
	"Add the query to the memorystore."
	return (md5_hash, location)

def upload_to_storage_and_return_url(filename):
	"Upload the processed file to cloud storage and return the path."
	return filename




def trim(request):
	request.path = request.path.strip('/')
	_source_params = request.path.split('/')[0]
	_source_file = request.path.split('/')[1]
	_time = int(time.time())
	_params = dict()
	_ffmpeg_input_args = dict()
	_hash = None

	# Extract parameters from URL field
	for param in _source_params.split(','):
		try:
			_key = param.split(':')[0]
			_value = param.split(':')[1]

			if _key in _allowed_params:
				_params[_key] = _value
			else: abort(400)
		except: abort(400)

	## Generate hash
	_hash = generate_hash("{}:{}".format(json.dumps(_params, sort_keys=True), _source_file))

	## Create args for ffmpeg.input()
	if 's' in _params and 'f' in _params:
		_ffmpeg_input_args['ss'] = float(_params['s'])
		_ffmpeg_input_args['t'] = float(_params['f']) - float(_params['s'])

	## FFprobe
	probe = ffmpeg.probe(request_signed_url(_source_file))
	video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
	width = int(video_stream['width'])
	height = int(video_stream['height'])

	## Run FFMPEG
	watermark = ffmpeg.input('watermark.png')

	job = ffmpeg.input(request_signed_url(_source_file), **_ffmpeg_input_args)
	#job = ffmpeg.filter(job, 'fps', fps=25, round='up')
	job = ffmpeg.drawbox(job, 50, 50, 120, 120, color='red', thickness=5)
	job = ffmpeg.overlay(job, watermark)
	job = ffmpeg.output(job, '{}/{}_{}.mp4'.format(LOCAL_DESTINATION_PATH, _time, _hash), **{'movflags': '+faststart'})


	try:
		out, err = ffmpeg.run(job, cmd=FFMPEG_BINARY_PATH, capture_stderr=True, capture_stdout=True)
		logging.info(out)
		logging.error(err)

	except ffmpeg.Error as e:
		logging.error(e.stderr.decode())
		print(e.stderr.decode(), file=sys.stderr)


	return send_file('{}/{}_{}.mp4'.format(LOCAL_DESTINATION_PATH, _time, _hash))

	#return jsonify({
	#	'params': _source_params,
	#	'js_params': _params,
	#	'ffmpeg_args': _ffmpeg_input_args,
	#	'ffmpeg_command': " ".join(ffmpeg.compile(job)),
	#	'source_file': _source_file,
	#	# Generate unique hash based on sorted parameters + source filename
	#	'hash': _hash,
	#	'video_stream': video_stream
	#})

# https://storage.googleapis.com/test_videos_mp4/%5B60fps%5D%205%20minutes%20timer%20with%20milliseconds-CW7-nFObkpw.mp4
# https://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4

# ffmpeg -y -ss 00:00:05.000 -i "https://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4" -t 00:00:05.000 -c:a copy -c:v copy output.mp4
# ffmpeg -y -ss 00:00:05.000 -i "http://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4" -t 00:00:05.000 -c:a copy -c:v copy output.mp4

# Return 302 directly if file hash already exists in storage
# Return 302 after finishing uploading and processing (to avoid Lambda and GCF response size limits)
# Combine clips
# Watermarking
# Signed UR generation for private source bucket (and for output as well)
# moov_atom
# configuration file format
# GCP Functions / AWS Lambda
# Include ffmpeg static build?

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

	app.run('127.0.0.1', 5000, debug=True)





"""
def my_function(request):
    return 'Hello World'

if __name__ == "__main__":
    from flask import Flask, request
    app = Flask(__name__)

    @app.route('/')
    def index():
        return my_function(request)

    app.run('127.0.0.1', 8000, debug=True)
"""










