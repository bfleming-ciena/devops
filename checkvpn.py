'''
@origin author Bommarito Consulting, LLC; http://bommaritollc.com/
@date 20131029
This script monitors and logs to CSV the status of all tunnels for all VPNs for a single EC2 region.

Modified by
@author Brian Fleming

Added SNS notification if no tunnels are up.
Added more detailed information regarding the resources.
'''

# Imports
import boto
import boto.ec2
import boto.vpc
import boto.sns
import csv
import datetime
import fabric.colors
import sys
import argparse
import os

# Set your AWS creds if you aren't using a dotfile or some other boto auth method
ec2_region = 'us-west-2'

# CSV output file
csv_file_name = "vpn_status.csv"
TUNNEL_UP = {}
IGNORE_VPN = {'vyatta': 1}


def report_tunnel_down(tunnel, vpn_name):
    '''
    Report and possibly take corrective action.
    '''
    msg = fabric.colors.red("{}: Tunnel {} is down since {}\n"
                            .format(vpn_name, tunnel.outside_ip_address, tunnel.last_status_change))

    sys.stderr.write(msg)


def test_tunnel_status(tunnel, vpn_name):
    '''
    Run a test on tunnel status.
    For now, this just trusts the AWS API status and does not perform network-level test.
    '''
    if vpn_name not in TUNNEL_UP:
        TUNNEL_UP[vpn_name] = 0

    # Check by status string
    if tunnel.status == 'DOWN':
        report_tunnel_down(tunnel, vpn_name)
        return False
    else:
        sys.stderr.write("{}: Tunnel {} is UP {}\n".format(vpn_name, tunnel.outside_ip_address,
                         tunnel.last_status_change))
        TUNNEL_UP[vpn_name] = TUNNEL_UP[vpn_name] + 1
        return True


def test_vpc_status():
    '''
    Output VPC tunnel statuses.
    '''
    # Create EC2 connection
    ec2_conn = boto.vpc.connect_to_region(ec2_region)
    # aws_access_key_id= aws_access_key_id,
    # aws_secret_access_key=aws_secret_access_key)
    cgws = {c.id: dict(name=c.tags['Name'], ip=c.ip_address) for c in ec2_conn.get_all_customer_gateways()}
    status_results = []
    # Setup the CSV file writer
    with open(csv_file_name, 'a') as csv_file:
        csv_writer = csv.writer(csv_file)
        # Iterate over all VPC connections
        for vpn_connection in ec2_conn.get_all_vpn_connections():
            # Handle connection and its tunnels
            for tunnel in vpn_connection.tunnels:
                # import ipdb
                # ipdb.set_trace()
                # Test the tunnel and output
                tunnel_name = cgws[vpn_connection.customer_gateway_id]['name']
                if tunnel_name not in IGNORE_VPN:
                    status = test_tunnel_status(tunnel, tunnel_name)
                row = [tunnel_name, cgws[vpn_connection.customer_gateway_id]['ip'],
                       datetime.datetime.now(), vpn_connection.id, tunnel.outside_ip_address, status,
                       tunnel.status_message, tunnel.last_status_change]
                csv_writer.writerow(row)
                msg = "Tunnel [ {3} ] {0} is {1} since {2}\n".format(tunnel.outside_ip_address, tunnel.status,
                                                                     tunnel.last_status_change,
                                                                     cgws[vpn_connection.customer_gateway_id])
                status_results.append(msg)
        return status_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check status of VPN connections.')
    parser.add_argument('-s', '--sns', type=str, help='Send diff report to this arn::sns topic. \
Assumes us-west-2 region.')

    args = parser.parse_args()
    test_vpc_status()

    UNHEALTHY_THRESH = 1
    if args.sns:
        sns = boto.sns.connect_to_region('us-west-2')

        for v in TUNNEL_UP:
            msg = ""
            if TUNNEL_UP[v] < 1:
                if not os.path.exists(str(v)):
                    file = open(str(v), "w")
                    unhealthy = 1
                    file.write(str(unhealthy))
                    file.close()
                else:
                    file = open(str(v), "r+")
                    unhealthy = int(file.read()) + 1
                    file.seek(0)
                    file.write(str(unhealthy))
                    file.close()

                if unhealthy >= UNHEALTHY_THRESH:
                    msg = msg + "{} is down. Unhealthy {} >= {}".format(v, unhealthy, UNHEALTHY_THRESH)
                    if v not in IGNORE_VPN:
                        if unhealthy == UNHEALTHY_THRESH or unhealthy % 10 == 0:
                            print "ALERT: Tunnel is down. SNS sent to {}".format(args.sns)
                            sns.publish(args.sns, message=msg, subject="AWS ALERT! VPN [{}] is Down! {} >= {}".format(v, unhealthy, UNHEALTHY_THRESH))
            else:
                if(os.path.exists(v)):
                    file = open(str(v), "r")
                    unhealthy = int(file.read())
                    file.close()
                    if unhealthy < UNHEALTHY_THRESH:
                        os.remove(v)
                    else:
                        msg = msg + "{} is back up.".format(v)
                        print "ALERT: Tunnel is back up. SNS sent to {}".format(args.sns)
                        sns.publish(args.sns, message=msg, subject="AWS VPN STATUS: VPN [{}] is back up.".format(v))
                        os.remove(v)
