#!/bin/bash
lftp -e "mirror --parallel=40 --verbose --reverse ./out /test-isr-radio-crestin-com;quit;" test-isr-radio-crestin-com@storage.bunnycdn.com
