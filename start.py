#!/usr/bin/env python2.7
# -*- coding: utf-8 -*
"""Startup script."""
import sys
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

logging.basicConfig(
    format='%(created).3f %(levelname).1s %(threadName)s'
           ' %(lineno)5d %(name)-35s'
           '>> %(message)s',
    datefmt='%y.%j %H:%M:%S',
    level=logging.DEBUG,
)

log.debug(f'Starting with args: {sys.argv}')

if __name__ == '__main__':
    from medusa.__main__ import main
    main()
