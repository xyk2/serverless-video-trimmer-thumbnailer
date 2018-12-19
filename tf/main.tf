provider "google" {
	project = "${var.project_id}"
}

provider "archive" { }

resource "random_string" "file_suffix" {
  length = 5
  special = false
}

data "archive_file" "function_dist" {
  type        = "zip"
  source_dir  = "../source"
  output_path = "dist/app-${random_string.file_suffix.result}.zip"
}

resource "google_storage_bucket" "gcf-build-artifacts" {
  name     = "gcf-build-artifacts"
  location = "asia-northeast1"
  storage_class = "REGIONAL"
  force_destroy = true
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "app-${random_string.file_suffix.result}.zip"
  source = "dist/app-${random_string.file_suffix.result}.zip"
  bucket = "gcf-build-artifacts"

  depends_on = ["google_storage_bucket.gcf-build-artifacts"]
}


resource "google_cloudfunctions_function" "video-segmentation" {
  name                  = "video-segmentation"
  description           = "[Managed by Terraform] transcodes and generates thumbnails from HTTP triggers."
  available_memory_mb   = 2048
  source_archive_bucket = "${google_storage_bucket_object.function_zip.bucket}"
  source_archive_object = "${google_storage_bucket_object.function_zip.name}"
  entry_point           = "trim"
  runtime				= "python37"
  timeout				= 60
  trigger_http			= true
  region                = "asia-northeast1"
}


output "md5" {
  value = "${data.archive_file.function_dist.output_md5}"
}