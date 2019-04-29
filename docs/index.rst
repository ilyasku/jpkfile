.. jpkfile documentation master file, created by
   sphinx-quickstart on Mon Aug 29 11:43:50 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to jpkfile's documentation!
===================================

jpkfile is a module for reading of data archives recorded with `JPK Instruments <http://www.jpk.com/>`_. It is a very early stage of the project, so expect to encounter some problems. This project is licensed under MIT License, and everyone is invited to contribute. If you encounter any problems, feel free to notify me via email, open a new issue on github or fix it and send a pull request!  

To see how to use this module, I recommend to take a look at the files in the `examples` folder. The source code is documented on :doc:`this page <source>`. I also refer to :doc:`a page <structure>` several times where I describe the structure of JPK archives.

Install
=======

Currently jpkfile has only one relevant python file *jpkfile.py*, which makes "installing" straight-forward: you simply need to add the folder in which the .py file lies to your python path.  
One way to do so is to add a *.pth* file containing the path to the folder as text to your user's *site-packages* folder:

* On my Ubuntu 14.04 machine, the site-packages folder is at `/home/user-name/.local/lib/python2.7/site-packages`
* If yours isn't there, you can figure it out by starting python in the command line and typing

    >>> import site
    >>> site.USER_SITE

* Open a new file in a text editor, enter the path to the folder containing the jpkfile module.
* Save the file into the site-packages folder.  

That's it. You should now be able to import jpkfile anywhere on your system. I recommend you start with the files in the `examples` folder to see how to use the jpkfile module.


Contents
========

.. toctree::
   :titlesonly:
   :maxdepth: 1

   Documentation of source code <source> 
   Structure of JPK archives <structure> 


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

License
=======

The MIT License (MIT)
Copyright (c) 2016 Ilyas Kuhlemann (ilyasp.ku@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
