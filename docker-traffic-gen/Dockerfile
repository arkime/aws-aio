FROM --platform=linux/amd64 ubuntu:focal

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates

COPY ./run_traffic_gen.sh /run_traffic_gen.sh

CMD ["/run_traffic_gen.sh"]
