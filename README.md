# jpkfile

jpkfile is a module for reading of data archives recorded with [JPK Instruments](http://www.jpk.com/).  
I am sorry for the lack of comments and documentation. This project is in a very early stage. Instead, you can have a look at the file in the `examples` folder.

# Install

Currently jpkfile has only one relevant python file *jpkfile.py*, which makes "installing" straight-forward: you simply need to add the folder in which the .py file lies to your python path.  
One way to do so is to add a *.pth* file containing the path to the folder as text to your user's *site-packages* folder:
* On my Ubuntu 14.04 machine, the site-packages folder is at `/home/user-name/.local/lib/python2.7/site-packages`
* If yours isn't there, you can figure it out by starting python in the command line and typing 
```
>>> import site
>>> site.USER_SITE
```
* Open a new file in a text editor, enter the path to the folder containing the jpkfile module.
* Save the file into the site-packages folder.  
That's it. You should now be able to import jpkfile anywhere on your system.

# First Steps

You can have a look at the `read_data_from_jpk_archive.py` file, or, if you have jupyter/ipython notebook installed, at the `read_data_from_jpk_archive.ipynb` file in the examples folder. Those examples show you first steps how to use the jpkfile module.

# License 

The MIT License (MIT)
Copyright (c) 2016 Ilyas Kuhlemann (ilyasp.ku@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.