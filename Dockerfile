FROM golang:1.23 as builder

WORKDIR /    

# Clone the repository and build the stand-alone nitriding executable.
RUN git clone https://github.com/brave/nitriding-daemon.git
ARG TARGETARCH
RUN ARCH=${TARGETARCH} make -C nitriding-daemon/ nitriding

COPY start.sh  /bin/
COPY gmail_mcp /bin/mcp

RUN chown root:root /bin/mcp/server.py /bin/start.sh
RUN chmod 0755      /bin/mcp/server.py /bin/start.sh

FROM python:3.13-slim-bullseye
RUN apt-get update && apt-get install -y curl git procps && rm -rf /var/lib/apt/lists/*

# Copy all our files to the final image.
COPY --from=builder /nitriding-daemon/nitriding /bin/start.sh /bin/
COPY --from=builder /bin/mcp                    /bin/mcp

# Install PDM for Python package management
RUN pip install pdm

# Install Python dependencies
WORKDIR /bin/mcp
RUN pdm install --no-self --no-editable

CMD ["start.sh"]
