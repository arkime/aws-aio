#!/bin/bash
#
# Randomly pick an url to fetch and then a semi random pause up to 5s.
# Use http url so we capture both clear and usually encrypted version
# after a redirect.

set -e

URLS=(
  http://www.google.com
  http://www.youtube.com
  http://www.twitter.com
  http://www.wikipedia.org
  http://www.amazon.com
  http://www.instagram.com
  http://www.linkedin.com
  http://www.reddit.com
  http://www.whatsapp.com
  http://openai.com
  http://www.yahoo.com
  http://www.bing.com
  http://www.live.com
  http://www.microsoft.com
)

SLEEPS=(0 0.1 0.5 1 1.5 2 3 5)

# Curl some Alexa top 100 sites, wash, repeat
while :
do
    u=${URLS[$RANDOM % ${#URLS[@]}]}
    s=${SLEEPS[$RANDOM % ${#SLEEPS[@]}]}
    #echo $s - $u
    curl -L --output /dev/null $u
    sleep $s
done
