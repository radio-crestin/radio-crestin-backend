#!/bin/bash

set -e

cat requirements.txt
echo ""

find . -name "requirements.txt" -print0 | xargs -0 -I {} sh -c 'cat {}; echo ""'
