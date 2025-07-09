terraform {
  backend "s3" {
    bucket = "tf-state-123456789012"
    key    = "dev/addons/terraform.tfstate"
    region = "us-west-2"
    encrypt = true
  }
}
