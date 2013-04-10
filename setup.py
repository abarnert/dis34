import sys

from setuptools import setup

extra_setup = {}
if sys.version_info < (3,):
    # TODO if possible
    sys.stderr.write('This backport is for Python 3.x only.\n')
    sys.exit(1)
else:
    # extra_setup['use_2to3'] = True
    pass

setup(
    name='dis34',
    version='0.1',
    description='Backport of new dis module from 3.4 to earlier 3.x.',
    long_description=(open('README.rst').read() + '\n\n' +
                      open('docs/dis34.rst').read() + '\n\n' +
                      open('docs/versions.rst').read()),
    py_modules=['dis34'],
    maintainer='Andrew Barnert',
    maintainer_email='abarnert@yahoo.com',
    license='PSF license',
    url='http://github.com/abarnert/dis34',
    test_suite='test.test_dis',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Python Software Foundation License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3'],
    keywords=['dis', 'disassembler'],
    **extra_setup
)
