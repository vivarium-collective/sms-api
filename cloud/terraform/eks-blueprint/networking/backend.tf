terraform {
  backend "s3" {
    bucket = "tf-state-123456789012"
    key    = "dev/networking/terraform.tfstate"
    region = "us-west-2"
    encrypt = true
  }
}
