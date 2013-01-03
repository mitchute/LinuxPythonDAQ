This python program will sample data from a BB electronics data acquisition module 232 SDA12

Currently set up to be used on a unix machine where the port is mounted at /dev/TTYUSB0 although this is to be generalized for cross-platform capability soon

To run without sudo, need to add your user to the dialout group like:
	
	usermod -a -G dialout MY_USER_NAME   (as root, or with sudo, of course)

...and then log out/log in or reboot for the changes to take effect

Running on Windows (I haven't tested this process yet, just guessing):
	
- Option 1:
	Install a python interpreter: http://www.python.org/download/
	Install pygtk: http://www.pygtk.org/downloads.html
- Option 2:
	Install the Enthought python distribution which contains python, numpy, matplotlib, et al.

Running on Debian Linux:
- Install: 
	sudo apt-get install python python-matplotlib python-numpy

