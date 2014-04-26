import sys

from setuptools import setup, find_packages


setup(
    name='grymt',
    version='1.2',
    description='Preps a set of HTML files for deployment',
    long_description=open('README.md').read(),
    author='Peter Bengtsson',
    author_email='mail@peterbe.com',
    license='MPL2',
    py_modules=['grymt'],
    entry_points={
        'console_scripts': ['grymt = grymt:main']
    },
    url='https://github.com/peterbe/grymt',
    include_package_data=True,
    install_requires=['cssmin', 'jsmin'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration'
        ],
    keywords=['grymt', 'deploy', 'deployment', 'minification',
              'concatenation']
)
