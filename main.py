import ffmpeg
import time
import hashlib

ts = int(time.time())
print(ts)

# https://storage.googleapis.com/test_videos_mp4/%5B60fps%5D%205%20minutes%20timer%20with%20milliseconds-CW7-nFObkpw.mp4
# https://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4

# ffmpeg -y -ss 00:00:05.000 -i "https://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4" -t 00:00:05.000 -c:a copy -c:v copy output.mp4
# ffmpeg -y -ss 00:00:05.000 -i "http://storage.googleapis.com/test_videos_mp4/bigbuckbunny.mp4" -t 00:00:05.000 -c:a copy -c:v copy output.mp4


# Return 302 directly if file hash already exists in storage
# Return 302 after finishing uploading and processing
# Combine clips
# Watermarking
# Signed UR generation for private source bucket
# moov_atom
# configuration file format
# GCP Functions / AWS Lambda
# Include ffmpeg static build?


# Things to test
#	moov-atom at the back source file
#	MOVs, AVIs, WAVs, FLVs
#	Benchmark processing times
#	Benchmark ffmpeg invocation, download, transcode, upload times
#	Benchmark cross region load times (GCP Japan to GCS Taiwan)


hashmd5 = hashlib.md5("whatever your string is".encode('utf-8')).hexdigest()
print(hashmd5)



stream = ffmpeg.input('source_examples/5_minute_timer_DV_NTSC_24p.mov', ss=10, t=15)
#stream = ffmpeg.filter(stream, 'fps', fps=25, round='up')
stream = ffmpeg.output(stream, 'outputs/{}.mp4'.format(ts))
ffmpeg.run(stream)
#lol = ffmpeg.compile(stream)

#print(lol)