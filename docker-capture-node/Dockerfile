FROM --platform=linux/amd64 ubuntu:focal

ENV DEBIAN_FRONTEND noninteractive

# Get required and quality-of-life utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget curl ca-certificates unzip less mandoc vim

# Install the AWS CLI so we can pull the OpenSearch Domain password from AWS Secrets Manager at runtime
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip

# Install/configure Arkime
RUN wget -O arkime.deb http://s3.amazonaws.com/files.molo.ch/builds/ubuntu-20.04/arkime_4.2.0-1_amd64.deb && \
    apt-get install -y ./arkime.deb && \
    rm -rf ./arkime.deb
COPY ./arkime_config.ini /opt/arkime/etc/config.ini

COPY ./run_capture_node.sh /run_capture_node.sh
CMD ["/run_capture_node.sh"]
