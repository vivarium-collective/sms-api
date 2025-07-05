### install crossplane

```bash
helm repo add crossplane-stable https://charts.crossplane.io/stable
helm repo update
```
```bash
helm install crossplane --namespace crossplane-system --create-namespace crossplane-stable/crossplane
```


### Create the IAM Policy and Role:

#### deploy cloud_formation.yaml using the AWS Console
- Go to the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home) and create a new stack using the `cloud_formation.yaml` file in this directory. Make sure to select "capabilities" and check "CAPABILITY_NAMED_IAM" to allow the creation of IAM roles.
- This will create an IAM policy and role that grants the necessary permissions for the vEcoli application to interact with AWS services.
- Once the stack is created, you can find the IAM role in the IAM console.
- You can also use the AWS CLI to create the stack, as shown below.
- This role can be assumed by the vEcoli application to access AWS resources.

#### or, deploy cloud_formation.yaml using CLI

```bash
aws cloudformation create-stack --stack-name vEcoli --template-body file://iam_config.yaml --capabilities CAPABILITY_NAMED_IAM
```
