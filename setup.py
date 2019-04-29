"""
USAGE: 
   o install in develop mode: navigate to the folder containing this file,
                              and type 'python setup.py develop --user'.
                              (ommit '--user' if you want to install for 
                               all users)                           
"""
from setuptools import setup

setup(name='jpkfile',
      version='1.2',
      description='Package to handle reading of files recorded with JPK instruments.',
      url='',
      author='Ilyas Kuhlemann',
      author_email='ilyasp.ku@gmail.com',
      license='MIT',      
      entry_points={
          "console_scripts": [],
          "gui_scripts": []
      },
      install_requires=['numpy',
                        'python-dateutil'],
      packages=['jpkfile'],
      zip_safe=False)
