#!/bin/bash

set -euo pipefail
# VolumeMount type was read only, GAM app was trying to adjust file name but was unsuccesful
# Mounting secrets to /credentials than copying them to /opt/gam/src/ solved the issue
cp /credentials/* /root/.gam/

exec $@
