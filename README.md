# Trusted GMail MCP Server

This is a gmail [MCP](https://modelcontextprotocol.io/introduction) server running inside a secure [AWS Nitro](https://aws.amazon.com/ec2/nitro/) enclave instance. It was originally forked from the [Claude Post](https://github.com/ZilongXue/claude-post) MCP server. Most MCP servers are run locally via the `stdio` transport; we followed [this guide](https://www.ragie.ai/blog/building-a-server-sent-events-sse-mcp-server-with-fastapi) to implement a remote MCP server using `sse` transport.

## Connect to the MCP Server

To use this MCP server, you will need an [app-specific password](https://myaccount.google.com/apppasswords).


Then simply add the following block to your client's `mcp.json` file.
```json
    "gmail_mcp": {
      "url": "http://https://gmail.mcp.freysa.ai/sse/sse/?ADDR=<your.email@gmail.com>&ASP=<your app-specific password>"
    }
```

Note that you might have to restart your client.

## Security Notice

This implementation is a proof of concept. Passing app-specific passwords in URLs is not a secure pattern because:
- URLs can be logged by proxies, browsers and servers
- URLs may appear in browser history
- URLs can be leaked via the Referer header to third-party sites

Unfortunately, current MCP clients have limitations on how they connect to servers. At the moment of release, MCP specification does not define a standard authentication mechanism for SSE servers. This means we can't use more secure patterns like bearer tokens or other authorization headers that would normally be preferred.

For additional security, consider:
1. Using a dedicated app-specific password just for this purpose
2. Accessing this over a secure VPN or private network
3. Running your own instance with the provided instructions

## Concept

AWS Nitro Enclaves provide isolated compute environments that enhance security through hardware-based attestation. When code runs in a Nitro Enclave, the platform generates cryptographic measurements of the code's identity and state. These measurements serve as a verifiable guarantee that the code has not been modified and is executing exactly as intended, protecting against tampering or unauthorized modifications. For more information, see this [blog post](https://blog.trailofbits.com/2024/02/16/a-few-notes-on-aws-nitro-enclaves-images-and-attestation/).

We use [Nitriding](https://github.com/brave/nitriding-daemon) to quickly deploy code in an AWS Nitro TEE.

## Verify the code attestation

To verify that the intended codebase is the one running in our TEE, you must reproduce running it in an AWS Nitro enclave yourself. Instructions to do so are below. Once you have it running, you can verify it using this repository as follows.

1. First build the code.

```sh
cd verifier

pnpm install && pnpm run build
```

2. Then run the verifier locally.
```
cd mcp/react-ts-webpack

pnpm i && pnpm run dev
```

3. Then open `http://localhost:8080/` in your browser. You will be prompted to add two fields

  (a) the PCR2 hash, which is a hash of the codebase

  (b) the Code attestation, which is signed by AWS

4. Click the "Verify Attestation" button

## Run your own instance in a TEE

You can reproduce running this server in a TEE as follows.

1. Use the AWS EC2 console to select a sufficiently large instance and be sure to enable Nitro.

2. Make sure that the ports needed by your application are open by checking the security group, in "security" tab of the instance in the ec2 console.

3. Clone this repo to your ec2 instance.

4. Run the setup script to download all necessary dependencies.
```bash
sudo /setup.sh
```

5. Allocate more memory for the enclave if necessary.
```bash
sudo nano /etc/nitro_enclaves/allocator.yaml

sudo systemctl restart nitro-enclaves-allocator.service
```

6. Run the enclave.
```bash
make
```

7. Run in production mode.
```bash
make run
```

## Use your MCP server

To actually use the MCP server, you will also need to run the gvproxy, as follows.

```bash
screen
./gvproxy.sh
```

Then you can `curl` the healthcheck endpoint to confirm that the MCP server is running in the enclave.

```bash
curl http://127.0.0.1:7047/
```
