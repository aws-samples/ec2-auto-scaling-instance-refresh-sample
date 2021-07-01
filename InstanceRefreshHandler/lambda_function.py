# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import boto3
from botocore.exceptions import ClientError
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# define boto3 clients
asg_client = boto3.client('autoscaling')


def get_ami_id_from_ib_notification(ib_notification):
    # Parse Image Builder notification and look up AMI for Lambda region
    for resource in ib_notification['outputResources']['amis']:
        if resource['region'] == os.environ['AWS_REGION']:
            return(resource['image'])
        else:
            return(None)


def set_asg_launch_template_version_latest(asg_name, lt_id):
    try:
        response = asg_client.update_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            LaunchTemplate={
                'LaunchTemplateId': lt_id,
                'Version': '$Latest'
            }
        )
        logging.info("Set launch template: {} version for asg: {} to $Latest".format(
            lt_id, asg_name))
        return response
    except ClientError as e:
        logging.error('Error setting launch template version to $Latest')
        raise e


def trigger_auto_scaling_instance_refresh(asg_name, strategy="Rolling",
                                          min_healthy_percentage=90, instance_warmup=300):

    try:
        response = asg_client.start_instance_refresh(
            AutoScalingGroupName=asg_name,
            Strategy=strategy,
            Preferences={
                'MinHealthyPercentage': min_healthy_percentage,
                'InstanceWarmup': instance_warmup
            })
        logging.info("Triggered Instance Refresh {} for Auto Scaling "
                     "group {}".format(response['InstanceRefreshId'], asg_name))

    except ClientError as e:
        logging.error("Unable to trigger Instance Refresh for "
                      "Auto Scaling group {}".format(asg_name))
        raise e


def lambda_handler(event, context):

    # Load SNS message body
    ib_notification = json.loads(event['Records'][0]['Sns']['Message'])
    logging.info(json.dumps(ib_notification, sort_keys=True, indent=4))
    asg_name = os.environ['AutoScalingGroupName']
    lt_id = os.environ['LaunchTemplateId']

    # Finish if Image build wasn't successful
    if ib_notification['state']['status'] != "AVAILABLE":
        logging.warning("No action taken. EC2 Image build failed.")
        return("No action taken. EC2 Image build failed.")

    # Get the AMI ID for current region from Image Builder notification
    ami_id = get_ami_id_from_ib_notification(ib_notification)
    if ami_id is None:
        logging.warning("There's no image created for region {}".format(
                        os.environ['AWS_REGION']))
        return("No AMI id created for region {}".format(
            os.environ['AWS_REGION']))

    # Change LT version to $Latest if not yet $Latest
    set_asg_launch_template_version_latest(asg_name, lt_id)

    # Trigger Auto Scaling group Instance Refresh
    trigger_auto_scaling_instance_refresh(asg_name)

    return("Success")
