# serverless-video-trimmer

Trim or transcode video clips from long files on serverless platforms (Lambda and GCF). Used in a video pipeline to generate custom user-specified clips server-side. Especially quick for long files as trimming/transcoding is done with byte-range requests. Repeated requests are served from a storage-backed bucket on S3 or GCS.


### Usage


### Some insights and observations:
- GCF caches JPG outputs depending on the Cache-Control header, though it intermittently clears the cache regardless of the header duration
-


### Advantages & disadvantages
The pseudo-streaming/byte-range approach to the input file has several key advantages:
- Not limited by Lambda / GCF limitations on storage capacity, which for longer videos can be easy to hit
- Trimming LONG videos (>5GB) is much faster, as the entire original file does not need to be downloaded first, only the relevant section
- The video is being transcoded as it is being downloaded

Of course, serverless also comes with its own advantages:
- Massive scalability & concurrency
- No need to provision servers
- Reduced costs, because functions run only when requested

This approach also comes with disadvantages (some pretty big):
- The first uncached request will take some time before a response is generated
- Not all video formats support pseudo/progressive streaming
- Requires generation of signed URLs as it relies on HTTP byte range requests
- Transcoding can be slow, as even the largest GCF configurations are very weak for video processing (max 2 vCPU)
- GCF as of this time does not support caching with a CDN layer in front natively, so a regional GCS bucket is used instead as a asset store
- 301/302/307 replies for existing assets is another set of handshakes for the client, slightly increasing load times


### Possible improvements
- Switch from HTTP triggers to a pub/sub model
- Put behind Firebase Hosting and use it as a CDN



### Technologies used
- python 3.7
- Google Cloud Datastore
- Google Cloud Storage
- Google Cloud Functions
- ffmpeg
- ffprobe
- Flask

### Static build of ffmpeg
I ran into issues with the static build of ffmpeg in that it errors with a segfault if doing a overlay filter with a seeked HTTP streaming input. I believe it is related to the timestamp being negative after seeking on a pseudo-streaming input, but more testing is needed. No issues with the build installed through apt.


### Deployment
`gcloud functions deploy serverless-ffmpeg-segmentation --runtime python37 --region=asia-northeast1 --trigger-http --entry-point=trim --memory=2048MB`
