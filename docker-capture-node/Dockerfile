FROM --platform=linux/amd64 ubuntu:focal

ENV DEBIAN_FRONTEND noninteractive

# Get required and quality-of-life utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget curl ca-certificates unzip less mandoc man-db vim libmagic1 iproute2 dnsutils net-tools tcpdump jq

# Install the AWS CLI so we can pull passwords from AWS Secrets Manager at runtime
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip

# Install/configure Arkime.
RUN wget -O arkime.deb https://github.com/arkime/arkime/releases/download/v5.0.1/arkime_5.0.1-1.ubuntu2004_amd64.deb && \
    apt-get install -y ./arkime.deb && \
    rm -rf ./arkime.deb

# Download the rir & oui files
RUN /opt/arkime/bin/arkime_update_geo.sh

COPY ./bootstrap_config.sh /bootstrap_config.sh
COPY ./run_capture_node.sh /run_capture_node.sh
CMD ["/run_capture_node.sh"]
