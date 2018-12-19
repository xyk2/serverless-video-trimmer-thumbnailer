# serverless video trimmer & thumbnailer

Trim or transcode video clips from long files on serverless platforms (Lambda and GCF). Used in a video pipeline to generate custom user-specified clips server-side. Especially quick for long files as trimming/transcoding is done with byte-range requests. Repeated requests are served from a storage-backed bucket on S3 or GCS.


### Usage
The general format of the URL is `https://FUNCTION_URL/{operation}/{parameters}/{source_filename}`. 

The operation is either a video `trim` or a `thumbnail`.

Allowed parameters are `fast`, `width`, `height`, `start` and `end`:
- `fast` (optional) does a straight codec copy (`-c copy` in ffmpeg), avoiding a slow transcoding step
- `width` and `height` (optional) specifies output width and height in pixels. For thumbnails, a percentage can be specified.
- `start` and `end` (optional) are the start and finish timestamps in seconds.

#### Example live URLs
Return a thumbnail 200px wide at 50 seconds: https://asia-northeast1-personal-projects-225512.cloudfunctions.net/video-segmentation/thumbnail/start:50,width:200/5_minute_timer.mp4

Return a thumbnail at 50% duration (original video size): https://asia-northeast1-personal-projects-225512.cloudfunctions.net/video-segmentation/thumbnail/start:50%/5_minute_timer.mp4

Return a video clip from 10.5 seconds to 20.5 seconds, compressed to 240p: https://asia-northeast1-personal-projects-225512.cloudfunctions.net/video-segmentation/trim/start:10.5,end:20.5,height:240/5_minute_timer.mp4

Return a video clip from 10.5 seconds to 20.5 seconds (original video size): https://asia-northeast1-personal-projects-225512.cloudfunctions.net/video-segmentation/trim/start:10.5,end:20.5,fast/5_minute_timer.mp4


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
- Improve cold start times
- Improve ffmpeg start up times with a barebones static build

### Technologies used
- python 3.7
- Google Cloud Datastore
- Google Cloud Storage
- Google Cloud Functions
- ffmpeg
- ffprobe
- Flask
- terraform

### Deployment
- From `gcloud` command line: `gcloud functions deploy serverless-ffmpeg-segmentation --runtime python37 --region=asia-northeast1 --trigger-http --entry-point=trim --memory=2048MB`
- Using terraform: run `terraform init` then `terraform apply` from the `terraform` folder. Will set up artifact bucket and automatically zip and create a function `video-segmentation`.


### Notes
I ran into issues with the static build of ffmpeg in that it errors with a segfault if doing a overlay filter with a seeked HTTP streaming input. I believe it is related to the timestamp being negative after seeking on a pseudo-streaming input, but more testing is needed. No issues with the build installed through apt.
