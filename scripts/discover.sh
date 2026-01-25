#!/bin/bash
# Full WhatsApp lists generator
set -e

echo "Creating full WhatsApp lists..."
mkdir -p lists

# Get current date for both files
CURRENT_DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Full domain list (27 domains like original)
cat > lists/domains.txt << DOMAINS_EOF
# WhatsApp domains
whatsapp.com
www.whatsapp.com
web.whatsapp.com
api.whatsapp.com
chat.whatsapp.com
call.whatsapp.com
voice.whatsapp.com
status.whatsapp.com
updates.whatsapp.com
beta.whatsapp.com

# WhatsApp.net domains
s.whatsapp.net
static.whatsapp.net
mmg.whatsapp.net
mmi.whatsapp.net
mms.whatsapp.net
v.whatsapp.net

# Voice calls
voip.whatsapp.com

# Meta infrastructure
facebook.com
www.facebook.com
fb.com
www.fb.com
messenger.com
www.messenger.com
fbcdn.net
static.xx.fbcdn.net
scontent.xx.fbcdn.net

# Instagram (part of Meta)
instagram.com
www.instagram.com

# Generated: $CURRENT_DATE
DOMAINS_EOF

# Full CIDR list (20 ranges like original)
cat > lists/cidr.txt << CIDR_EOF
# Meta IP ranges
31.13.24.0/21
31.13.64.0/18
45.64.40.0/22
66.220.144.0/20
69.63.176.0/20
69.171.224.0/19
74.119.76.0/22
102.132.96.0/20
103.4.96.0/22
129.134.0.0/16
157.240.0.0/16
173.252.64.0/18
185.60.216.0/22
199.201.64.0/22
204.15.20.0/22

# Specific WhatsApp subnets
31.13.72.0/24
31.13.73.0/24
31.13.74.0/24
31.13.75.0/24
57.144.245.0/24

# Generated: $CURRENT_DATE
CIDR_EOF

echo "✅ Created full WhatsApp lists:"
echo "   Domains: $(wc -l < lists/domains.txt)"
echo "   CIDR: $(wc -l < lists/cidr.txt)"
echo "   Date: $CURRENT_DATE"
