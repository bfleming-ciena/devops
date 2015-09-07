#!/bin/bash

# The VIP hard-coded in this script must match the vip_monitor VIP.
#
# Just run this script without any arguments and this server will take over the VIP
# and become the primary server.
#

###### ###### ###### ###### ###### ###### ###### ######
# Description:
#
# attaches an IP of your choice to the primary NIC
# an instance you specify
#
# Setup:
#
# You need, at a minimum, the following permissions:
# {
#  "Statement": [
#    {
#      "Action": [
#        "ec2:AssignPrivateIpAddresses",
#        "ec2:DescribeInstances"
#      ],
#      "Effect": "Allow",
#      "Resource": "*"
#    }
#  ]
# }
#
# Usage:
#
# ./assign_private_ip.sh ip_address instance_id
#
# Example:
# ./assign_private_ip.sh '10.0.3.15' 'i-100ffabd'
#
###### ###### ###### ###### ###### ###### ###### ######


# http://www.davidpashley.com/articles/writing-robust-shell-scripts/
set -o errexit
set -o nounset

VIP=10.9.248.10
IP=$VIP
INSTANCE_ID=`curl http://169.254.169.254/latest/meta-data/instance-id`

ENI=$(\
  aws ec2 describe-instances \
  --region us-west-2 --instance-ids $INSTANCE_ID | \
  jq -r \
  '.Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
)

echo "Adding IP $IP to ENI $ENI"

aws ec2 assign-private-ip-addresses \
  --network-interface-id $ENI \
  --private-ip-addresses $IP \
  --allow-reassignment \
  --region us-west-2

sudo ifdown eth0:0
sudo ifup eth0:0
