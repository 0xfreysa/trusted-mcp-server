echo "📦 Setting up nitro instance"

# Amazon Linux 2023 uses dnf instead of amazon-linux-extras
echo "📦 Installing Nitro Enclave CLI"
sudo yum install -y aws-nitro-enclaves-cli aws-nitro-enclaves-cli-devel

# Create groups if they don't exist
echo "📦 Setting up user groups"
sudo groupadd -f ne
sudo groupadd -f docker

# Add user to groups
sudo usermod -aG ne ec2-user
sudo usermod -aG docker ec2-user

# Install Docker for AL2023
echo "📦 Installing Docker"
sudo yum install -y docker
sudo systemctl enable docker.service
sudo systemctl start docker.service

# Setup nitro enclaves service
echo "📦 Setting up Nitro Enclaves service"
sudo yum install -y aws-nitro-enclaves-cli-devel
sudo systemctl enable nitro-enclaves-allocator.service
sudo systemctl start nitro-enclaves-allocator.service

# Check if nitro-cli is in path, if not create symlink
if ! command -v nitro-cli &> /dev/null; then
    echo "📦 Setting up nitro-cli command"
    sudo ln -sf /usr/bin/nitro-cli-devel /usr/bin/nitro-cli
fi

# Verify nitro-cli installation
nitro-cli --version || echo "nitro-cli not available, may need to log out and back in"

echo "📦 Installing development tools"
sudo yum install -y make git

echo '📦 Installing Go'
GO_VERSION="1.23.8"  # Keep your original version
wget https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz
rm go${GO_VERSION}.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc

echo '📦 Verify Go version'
go version

echo '📦 Installing gvproxy'
git clone https://github.com/containers/gvisor-tap-vsock.git
cd gvisor-tap-vsock
make

echo "✅ Setup done, reboot with 'sudo reboot'"
