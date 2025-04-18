prog := python-enclave
version := $(shell git describe --tag --dirty 2>/dev/null || echo v1.0.0)
image_tag := $(prog):$(version)
image_tar := $(prog)-$(version)-kaniko.tar
image_eif := $(image_tar:%.tar=%.eif)

ARCH ?= $(shell uname -m)
ifeq ($(ARCH),aarch64)
	override ARCH=arm64
endif
ifeq ($(ARCH),x86_64)
	override ARCH=amd64
endif

.PHONY: all
all: run-debug

.PHONY: image
image: clean $(image_tar)

$(image_tar): Dockerfile start.sh
	docker run \
		-v $(PWD):/workspace \
		gcr.io/kaniko-project/executor:v1.9.2 \
		--reproducible \
		--no-push \
		--tarPath $(image_tar) \
		--destination $(image_tag) \
		--build-arg TARGETPLATFORM=linux/$(ARCH) \
		--build-arg TARGETOS=linux \
		--build-arg TARGETARCH=$(ARCH) \
		--build-arg GITHUB_TOKEN=$(GITHUB_TOKEN) \
		--custom-platform linux/$(ARCH)

$(image_eif): $(image_tar)
	docker load -i $<
	nitro-cli build-enclave \
		--docker-uri $(image_tag) \
		--output-file $(image_eif)

.PHONY: run
run:
	# Terminate already-running enclave.
	nitro-cli terminate-enclave --all
	# Start our proxy and the enclave.
	./run-enclave.sh $(image_eif)

.PHONY: run-debug
run-debug: $(image_eif)  
	# Terminate already-running enclave.
	nitro-cli terminate-enclave --all
	# Start our proxy and the enclave.
	./run-enclave.sh $(image_eif) --debug
	
.PHONY: clean
clean:
	rm -f $(prog)*

.PHONY: run-proxy
run-proxy:
	./gvproxy.sh

.PHONY: stop
stop:
	nitro-cli terminate-enclave --all


