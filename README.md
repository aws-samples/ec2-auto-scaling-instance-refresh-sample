# Sample EC2 Auto Scaling groups Instance Refresh solution

## Introduction
Instance Refresh is an EC2 Auto Scaling feature that enables automatic deployments of instances in Auto Scaling groups in order to release new application versions or make infrastructure updates. You can trigger an Instance Refresh using the EC2 Auto Scaling  Management Console, or use the new `StartInstanceRefresh` API via the AWS CLI or any AWS SDK. All you need to do is specify the percentage of healthy instances to keep in the group while ASG terminates and launches instances, and the warm-up time which is the time period that ASG waits between groups of instances that it will refresh via Instance Refresh. If your ASG is using Health Checks, then ASG will also wait for the instances in the group to be healthy before it continues to the next group of instances.

You can use this functionality in a wide variety of solutions and workflows. This repository contains a sample solution that uses EC2 Image Builder to build a golden AMI and notify an SNS topic. Amazon SNS triggers an AWS Lambda function that updates the Launch Template of an EC2 Auto Scaling group you configure with the new AMI version that's been created and starts an Instance Refresh. If your Auto Scaling group is configured with `LaunchTemplateVersion = $Latest`, your instance fleet will be refreshed and new instances will use the new AMI.

![Architecture](/images/architecture-diagram.png)

## Deploying the solution

This solution deploys the following components:
* An Amazon VPC with three public subnets 
* A sample EC2 Image Builder pipeline that builds an AMI from the latest Amazon Linux 2 image, updating the system, installing Docker CE and rebooting
* An Amazon SNS Topic that receives notifications from the EC2 Image Builder pipeline
* A sample EC2 Auto Scaling group with two instances using the latest Amazon Linux 2 AMI
* An AWS Lambda function subscribed to the SNS topic that creates a new Launch Template version with the new created AMI and triggers an Instance Refresh of the above Auto Scaling group.
* An IAM role to grant the AWS Lambda function permissions to invoke the Auto Scaling and EC2 APIs 
* An IAM role for EC2 Image Builder instances

### Requirements

**Note:** For easiest deployment you can create a [Cloud9 environment](https://docs.aws.amazon.com/cloud9/latest/user-guide/create-environment.html), it already has the below requirements installed.

* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) 
* [Python 3 installed](https://www.python.org/downloads/)
* [Docker installed](https://www.docker.com/community-edition)
* [SAM CLI installed](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

### Deployment Steps

Once you've installed the requirements listed above, open a terminal session as you'll need to run through a few commands to deploy the solution.

First, we need an `S3 bucket` where we can upload the Lambda function packaged as ZIP before we deploy anything - If you don't have a S3 bucket to store code artifacts then, this is a good time to create one:

```bash
aws s3 mb s3://BUCKET_NAME
```
Next, clone the ec2-auto scaling-instance-refresh-sample repository to your local workstation or to your Cloud9 environment.

```
git clone https://github.com/aws-samples/ec2-auto-scaling-instance-refresh-sample.git
```

Next, change directories to the root directory for this example solution.

```
cd ec2-auto-scaling-instance-refresh-sample
```

Next, run the following command to build the Lambda function:

```bash
sam build --use-container
```

Next, run the following command to package the Lambda function to S3:

```bash
sam package \
    --output-template-file packaged.yaml \
    --s3-bucket REPLACE_THIS_WITH_YOUR_S3_BUCKET_NAME
```

Next, the following command will create a Cloudformation Stack and deploy your SAM resources.

```bash
sam deploy \
    --template-file packaged.yaml \
    --stack-name ec2-auto-scaling-instance-refresh-sample \
    --capabilities CAPABILITY_IAM 
```

By default we use t3.micro instances for both the EC2 Image Builder instance and the sample Auto Scaling group instance type. If you want to use a different instance type, you can include parameter overrides on the `sam deploy` command.

```bash
sam deploy \
    --template-file packaged.yaml \
    --stack-name ec2-auto-scaling-instance-refresh-sample \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
    BuildInstanceType=REPLACE_THIS_WITH_THE_INSTANCE_TYPE_YOU_WANT \
    SampleAutoScalingGroupInstanceType=REPLACE_THIS_WITH_THE_INSTANCE_TYPE_YOU_WANT  
```

You will find all the resources created on the [AWS CloudFormation console](https://console.aws.amazon.com/cloudformation/home?#/stacks/).

![CloudFormation console](/images/sam-cfn-console.png)

## Testing the solution

Trigger the EC2 Image Builder Pipeline.
1. [Go to the EC2 Image Builder console](https://console.aws.amazon.com/imagebuilder/home?#viewPipeline)
2. Click on the `SampleAmazon2WithDockerPipeline` pipeline
3. Click on the `Actions` button on the top-right side of the console, and select `Run pipeline`
4. Wait until the pipeline finishes (it will take ~20 minutes to complete). You can refresh the `Output image` section clicking the circle arrow button on the right side of the console.
    ![Image Builder console](/images/image-builder-console.png)
5. (Optional) If you want to get notified when Image Builder finishes, you can [subscribe your e-mail to the SNS topic](https://docs.aws.amazon.com/sns/latest/dg/sns-getting-started.html#step-send-message)
6. Click on the image version that's been created to see the AMI id that's been created.

Once the new image is built, you can check your Auto Scaling group and watch the instance refresh action.
1. Go to the [EC2 Auto Scaling console](https://console.aws.amazon.com/ec2autoscaling/home#/details)
2. Select the Auto Scaling group named `ec2-image-builder-instance-refresh-sample-SampleAuto ScalingGroup-*`. Then go to the `Instance Refresh` tab and you will see the instance refresh in progress.
3. You can also see the instance refresh events on the Activity tab.
    ![Auto Scaling activity](/images/asg-instance-refresh-activity-history.png)
4. You can also check on the EC2 Instances console and see how instances are shut down and new instances are launched.
    ![Instance Refresh](/images/ec2-instance-refresh.png)
5. Once it finishes, check the Auto Scaling group instances AMI on the EC2 Instances console (filter by Tag Name value `EC2 Image Builder Sample`). Select an instance and on the `Launch Configuration` tab you will find the AMI id. 

Feel free to also inspect the AWS Lambda function and the logs on the [CloudWatch logs console](https://console.aws.amazon.com/cloudwatch/home?#logsV2:log-groups).

## Clean up
Once you're done, you can delete the solution going to the [AWS CloudFormation console](https://console.aws.amazon.com/cloudformation/home#/stacks) and deleting the `ec2-image-builder-instance-refresh-sample`. Don't forget to delete the following artifacts too:
* Delete the AMI id that's been created by Image Builder.
* Delete the [CloudWatch log group](https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups) for the Lambda function. You'll identify it with the name `/aws/lambda/ec2-auto-scaling-instance-r-InstanceRefreshHandler*`. You can find the AMI id above on the logs. 
* Consider deleting the Amazon S3 bucket used to store the packaged Lambda artifact if you created it in purpose to deploy this solution

## Cost of the solution

The cost of the solution is covered completely by the free tier if your account is less than 12 months old (and you don't already exceed free tier limits like the 750 t3.micro hours monthly). Otherwise, the cost of testing the solution is less than $0.25 if running for an hour. Costs break-down below: 
* By default, this solution uses t3.micro instances, which cost $0.0104 / hour each in us-east-1. You can find all regions pricing [here](https://aws.amazon.com/ec2/pricing/on-demand/). t3.micro is eligible for [AWS Free tier](https://aws.amazon.com/free/?all-free-tier.sort-by=item.additionalFields.SortRank&all-free-tier.sort-order=asc)
* There is no extra charge for EC2 Image Builder, you only pay for the underlying EC2 resources. By default, this solution uses t3.micro instances to build AMIs.
* There are no charges for SNS Lambda notifications. If you subscribe your e-mail to the SNS topic, the first 1,000 notifications are free. More details [here](https://aws.amazon.com/sns/pricing/)
* AWS Lambda first 1 Million requests per month are covered by the [AWS Free tier](https://aws.amazon.com/free/?all-free-tier.sort-by=item.additionalFields.SortRank&all-free-tier.sort-order=asc).
* Cloudwatch Logs usage is covered by the free tier if you use less than 5GB of data. More info [here](https://aws.amazon.com/cloudwatch/pricing/). 

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

