# Estimated charges
MOST=$(aws --region us-east-1 cloudwatch get-metric-statistics  --namespace "AWS/Billing"  --metric-name "EstimatedCharges"  --dimension "Name=Currency,Value=USD"  --start-time $(date +"%Y-%m-%dT%H:%M:00" --date="-12 hours")  --end-time $(date +"%Y-%m-%dT%H:%M:00")  --statistic Maximum  --period 60  --output text | sort -r -k 3 | head -n 1 | cut -f 2 )

# Marketplace Charges
MARKET=$(aws --region us-east-1 cloudwatch get-metric-statistics  --namespace "AWS/Billing"  --metric-name "EstimatedCharges"  --dimensions Name=ServiceName,Value=AWSMarketplace Name=Currency,Value=USD   --start-time $(date +"%Y-%m-%dT%H:%M:00" --date="-12 hours")  --end-time $(date +"%Y-%m-%dT%H:%M:00")  --statistic Maximum  --period 60  --output text | sort -r -k 3 | head -n 1 | cut -f 2)

# Redshift
REDSHIFT=$(aws --region us-east-1 cloudwatch get-metric-statistics  --namespace "AWS/Billing"  --metric-name "EstimatedCharges"  --dimensions Name=ServiceName,Value=AmazonRedshift Name=Currency,Value=USD   --start-time $(date +"%Y-%m-%dT%H:%M:00" --date="-12 hours")  --end-time $(date +"%Y-%m-%dT%H:%M:00")  --statistic Maximum  --period 60  --output text | sort -r -k 3 | head -n 1 | cut -f 2)

BILL=$(echo "$MOST+$MARKET" | bc)

aws sns --region us-west-2 publish  --topic-arn arn:aws:sns:us-west-2:xxxxx:xxxxxx --subject "Current=\$$BILL (AWS Dev)" --message "Current bill past 12 hours"
