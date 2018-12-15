#!/usr/bin/env python
# encoding: utf-8

import ffmpeg
import time
import hashlib
import json
from flask import Flask, abort, request, jsonify


ts = int(time.time())
_allowed_params = ['s', 'f', 'q', 'w'] #
SOURCE_BUCKET_NAME = 'LOL'

app = Flask(__name__)

@app.route('/<params>/<source_file>', methods=['GET'])
def trim(params, source_file):
	_params = dict()

	# Extract parameters from URL field
	for param in params.split(','):
		try:
			_key = param.split(':')[0]
			_value = param.split(':')[1]

			if _key in _allowed_params:
				_params[_key] = _value
			else: abort(400)
		except: abort(400)


	return jsonify({
		'params': params,
		'js_params': _params,
		'source_file': source_file,
		# Generate unique hash based on sorted parameters + source filename
		'hash': generate_hash("{}:{}".format(json.dumps(_params, sort_keys=True), source_file))
	})

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

def generate_hash(message):
	"Returns an MD5 hash given a message."
	hashmd5 = hashlib.md5(str(message).encode('utf-8')).hexdigest()
	return hashmd5

def request_signed_url(filename):
	"Request and return a protected signed URL from the source bucket."
	return filename

def check_in_memorystore(md5_hash):
	"Check if this query is repeated in the memorystore."
	return md5_hash

def insert_to_memorystore(md5_hash, location):
	"Add the query to the memorystore."
	return (md5_hash, location)

def upload_to_storage_and_return_url(filename):
	"Upload the processed file to cloud storage and return the path."
	return filename

















if __name__=="__main__":
	import sys, pprint

	source_file = 'source_examples/5_minute_timer_DV_NTSC_24p.mov'

	if(len(sys.argv) >= 2):
		source_file = sys.argv[1]

	stream = ffmpeg.input(source_file, ss=10, t=5)
	#stream = ffmpeg.filter(stream, 'fps', fps=25, round='up')
	stream = ffmpeg.output(stream, 'outputs/{}.mp4'.format(ts))
	ffmpeg.run(stream)
	#lol = ffmpeg.compile(stream)

	#print(lol)






























