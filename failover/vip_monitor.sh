#!/bin/sh
# This script will monitor another HA node and take over a Virtual IP (VIP)
# if communication with the other node fails

# High Availability IP variables
# Other node's IP to ping and VIP to swap if other node goes down
HA_Node_IP=10.9.248.69
VIP=10.9.248.10

# Specify the EC2 region that this will be running in
REGION=us-west-2

# Run aws-apitools-common.sh to set up default environment variables and to
# leverage AWS security credentials provided by EC2 roles
# . /etc/profile.d/aws-apitools-common.sh

# Determine the instance and ENI IDs so we can reassign the VIP to the
# correct ENI. Requires EC2 describe-instances and assign-private-ip-address
# permissions. The following example EC2 roles policy will authorize these
# commands:
# {
# "Statement": [
# {
# "Action": [
# "ec2:AssignPrivateIpAddresses",
# "ec2:DescribeInstances"
# ],
# "Effect": "Allow",
# "Resource": "*"
# }
# ]
# }

INSTANCE_ID=`/usr/bin/curl --silent http://169.254.169.254/latest/meta-data/instance-id`

ENI_ID=$(\
  aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION | \
  jq -r \
  '.Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
)

echo `date` "-- Starting HA monitor"
while [ . ]; do
 #echo "ping -c 3 -W 1 $HA_Node_IP | grep time= | wc -l"
 pingresult=`ping -c 3 -W 1 $HA_Node_IP | grep time= | wc -l`
 if [ "$pingresult" -eq 0 ]; then
 echo `date` "-- HA heartbeat failed, taking over VIP"
 aws ec2 assign-private-ip-addresses --network-interface $ENI_ID --region $REGION --allow-reassignment --private-ip-addresses $VIP

 pingresult=$(ping -c 1 -W 1 $VIP | grep time= | wc -l)
 if [ $pingresult -eq 0 ]; then
 echo `date` "-- Restarting network"
 sudo ifdown eth0:0 > /dev/null 2>&1
 sudo ifup eth0:0 > /dev/null 2>&1
 fi
 sleep 60
 fi
 sleep 2
done
