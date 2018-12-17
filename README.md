# serverless-video-trimmer

Trim and transcode (if neeed) video clips from long files on vendor-neutral serverless platforms (Lambda and GCF). Used in a video pipeline to generate custom user-specified clips server-side. Repeated requests are served from a storage-backed service on S3 or GCS.

### Differences & advantages
The pseudo-streaming approach to the input file has several key advantages:
- Not limited by Lambda / GCF limitations on storage capacity, which for longer videos can be easy to hit
- Trimming LONG videos (>5GB) is much faster, as the entire original file does not need to be downloaded first, only the relevant section
- The video is being transcoded as it is being downloaded

But it also comes with disadvantages (some pretty big):
- Not all video formats support pseudo/progressive streaming
- Requires generation of signed URLs as it relies on HTTP byte range requests
- Transcoding can be slow, as even the largest Lambda/GCF configurations are very weak for video processing (max 2 vCPU)


### Static build of ffmpeg
I ran into issues with the static build of ffmpeg in that it errors with a segfault if doing a overlay filter with a seeked HTTP streaming input. I believe it is related to the timestamp being negative after seeking, but more testing is needed. No issues with the version installed through apt.


### Deployment
`gcloud functions deploy demo1 --runtime python37 --region=asia-northeast1 --trigger-http --entry-point=trim --memory=2048MB`
