"""
USAGE: 
   o install in develop mode: navigate to the folder containing this file,
                              and type 'python setup.py develop --user'.
                              (ommit '--user' if you want to install for 
                               all users)                           
"""
from setuptools import setup

with open("README.rst", 'r') as fh:
    long_description = fh.read()

setup(name='jpkfile',
      version='1.6',
      description='Package to handle reading of files recorded with JPK instruments.',
      long_description=long_description,
      long_description_content_type="text/x-rst",
      url='https://gitlab.gwdg.de/ikuhlem/jpkfile',
      author='Ilyas Kuhlemann',
      author_email='ilyasp.ku@gmail.com',
      license='MIT',
      entry_points={
          "console_scripts": [],
          "gui_scripts": []
      },
      install_requires=['numpy',
                        'python-dateutil', 'pytz'],
      packages=['jpkfile'],
      zip_safe=False)
