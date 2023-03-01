#!/bin/sh

set -e

# Curl some Alexa top 100 sites, wash, repeat
while :
do
	curl https://www.google.com
	curl https://www.youtube.com
	curl https://www.twitter.com
	curl https://www.wikipedia.org
	curl https://www.amazon.com
	curl https://www.instagram.com
	curl https://www.linkedin.com
	curl https://www.reddit.com
	curl https://www.whatsapp.com
	curl https://openai.com
	curl https://www.yahoo.com
	curl https://www.bing.com
	curl https://www.live.com
	curl https://www.microsoft.com
	sleep 10
done