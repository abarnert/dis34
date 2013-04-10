# Hack to prevent stupid error on exit of `python setup.py test`. (See
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html.)
try:
    import multiprocessing
except ImportError:
    pass

import sys

from setuptools import setup

extra_setup = {}
if sys.version_info >= (3, 0):
    root_dir = 'dis34_3x'
else:
    root_dir = 'dis34_2x'

setup(
    name='dis34',
    version='0.2',
    description='Backport of new dis module from 3.4.',
    long_description=(open('README.rst').read() + '\n\n' +
                      open('docs/dis34.rst').read() + '\n\n' +
                      open('docs/versions.rst').read()),
    py_modules=['dis34'],
    package_dir={'': root_dir},
    maintainer='Andrew Barnert',
    maintainer_email='abarnert@yahoo.com',
    license='PSF license',
    url='http://github.com/abarnert/dis34',
    test_suite='test.test_dis',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Python Software Foundation License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3'],
    keywords=['dis', 'disassembler'],
    **extra_setup
)
