# serverless-video-trimmer

Trim and transcode (if neeed) video clips from long files on vendor-neutral serverless platforms (Lambda and GCF). Used in a video pipeline to generate custom user-specified clips server-side. Repeated requests are served from a storage-backed service on S3 or GCS.


### Deployment
`gcloud functions deploy demo1 --runtime python37 --region=asia-northeast1 --trigger-http --entry-point=trim --memory=2048MB`