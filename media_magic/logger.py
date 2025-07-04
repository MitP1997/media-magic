import logging

FORMAT_CONS = '%(asctime)s %(name)-12s %(levelname)8s\t%(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT_CONS)
logger = logging.getLogger('media_magic') 