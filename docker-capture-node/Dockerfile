FROM --platform=linux/amd64 ubuntu:focal

ENV DEBIAN_FRONTEND noninteractive

# Get required and quality-of-life utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget curl ca-certificates unzip less mandoc man-db vim libmagic1 iproute2 dnsutils net-tools tcpdump

# Install the AWS CLI so we can pull passwords from AWS Secrets Manager at runtime
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip

# Install/configure Arkime.  WARNING - this uses the development tip and therefore version floats
RUN wget -O arkime.deb https://s3.amazonaws.com/files.molo.ch/arkime-main_ubuntu20_amd64.deb && \
    apt-get install -y ./arkime.deb && \
    rm -rf ./arkime.deb
COPY ./arkime_config.ini /opt/arkime/etc/config.ini

COPY ./run_capture_node.sh /run_capture_node.sh
CMD ["/run_capture_node.sh"]
