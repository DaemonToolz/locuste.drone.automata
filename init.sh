#!/bin/bash

source ~/code/parrot-groundsdk/products/olympe/linux/env/shell
export LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1
python main.py